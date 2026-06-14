"""人声检测: Silero VAD (onnx, 不依赖 torch) + 开/关麦状态机。

状态机要点 (这就是"键盘鼠标不误触发"的关键):
- 必须连续检出人声 >= min_speech_ms 才开麦  -> 单次敲键/点鼠标的短脉冲被过滤掉
- 停止说话后保持 hangover_ms 再关麦         -> 一句话中间的停顿不会被切碎
- 再叠加 Silero 本身对"人声 vs 瞬态噪声"的判别能力
"""

from __future__ import annotations

import glob
import os
import sys
from typing import Callable

import numpy as np
import onnxruntime as ort

from .config import FRAME_MS, SAMPLE_RATE


def _find_model() -> str:
    """定位 Silero VAD 的 onnx 模型文件。"""
    candidates: list[str] = []
    # 打包后: PyInstaller 把模型解包到临时目录
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidates += [
            os.path.join(base, "silero_vad", "data", "silero_vad.onnx"),
            os.path.join(base, "silero_vad.onnx"),
        ]
    # 开发环境: 从已安装的 silero_vad 包里取
    data_dirs: list[str] = []
    try:
        import silero_vad  # type: ignore

        pkg_dir = os.path.dirname(silero_vad.__file__)
        data_dirs.append(os.path.join(pkg_dir, "data"))
        candidates += [
            os.path.join(pkg_dir, "data", "silero_vad.onnx"),
            os.path.join(pkg_dir, "data", "silero_vad_16k_op15.onnx"),
        ]
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        data_dirs.append(os.path.join(base, "silero_vad", "data"))

    for path in candidates:
        if os.path.exists(path):
            return path
    # 兜底: 扫描 data 目录里任意 .onnx
    for d in data_dirs:
        hits = sorted(glob.glob(os.path.join(d, "*.onnx")))
        if hits:
            return hits[0]
    raise FileNotFoundError(
        "找不到 Silero VAD onnx 模型, 请确认已 pip install silero-vad"
    )


class SileroVAD:
    """对单帧 (512 样本, 16kHz, float32) 输出人声概率 0~1。"""

    def __init__(self, model_path: str | None = None):
        path = model_path or _find_model()
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self._sess = ort.InferenceSession(
            path, sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._sr = np.array(SAMPLE_RATE, dtype=np.int64)
        self.reset()

    # 16kHz 时模型需要前置 64 样本的上下文 (官方 OnnxWrapper 行为), 必须维护
    _CONTEXT = 64

    def reset(self) -> None:
        # Silero v5/v6 的循环状态: shape (2, batch, 128)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, self._CONTEXT), dtype=np.float32)

    def __call__(self, frame: np.ndarray) -> float:
        x = frame.reshape(1, -1).astype(np.float32)
        # 关键: 把上一帧尾部 64 样本的上下文拼到当前 512 样本前面 (-> 576 样本), 否则识别不出人声
        x = np.concatenate([self._context, x], axis=1).astype(np.float32)
        self._context = x[:, -self._CONTEXT:]
        # 用 run(None, ...) 取全部输出, 不依赖输出节点命名
        out, self._state = self._sess.run(
            None, {"input": x, "state": self._state, "sr": self._sr}
        )
        return float(out[0][0])


class VADStateMachine:
    """把逐帧人声概率转成稳定的开/关麦事件。"""

    def __init__(
        self,
        threshold: float,
        min_speech_ms: int,
        hangover_ms: int,
        on_speech_start: Callable[[], None],
        on_speech_end: Callable[[], None],
    ):
        self._threshold = threshold
        self._min_speech_frames = max(1, round(min_speech_ms / FRAME_MS))
        self._hangover_frames = max(1, round(hangover_ms / FRAME_MS))
        self._on_start = on_speech_start
        self._on_end = on_speech_end

        self.is_open = False
        self._speech_run = 0   # 连续人声帧计数
        self._silence_run = 0  # 开麦后连续静音帧计数

    def reset(self) -> None:
        self.is_open = False
        self._speech_run = 0
        self._silence_run = 0

    def process(self, prob: float) -> None:
        is_speech = prob >= self._threshold
        if not self.is_open:
            if is_speech:
                self._speech_run += 1
                if self._speech_run >= self._min_speech_frames:
                    self.is_open = True
                    self._silence_run = 0
                    self._on_start()
            else:
                self._speech_run = 0
        else:
            if is_speech:
                self._silence_run = 0
            else:
                self._silence_run += 1
                if self._silence_run >= self._hangover_frames:
                    self.is_open = False
                    self._speech_run = 0
                    self._on_end()
