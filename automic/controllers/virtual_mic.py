"""模式C: 把人声送进虚拟声卡 (VB-Cable)。

关麦时输出静音, 开麦时输出实时音频; 开麦瞬间先补上 preroll 预滚缓冲, 避免切掉第一个字。
游戏里把麦克风输入设备选成 "CABLE Output" 即可。
"""

from __future__ import annotations

import collections
import queue

import numpy as np
import sounddevice as sd

from ..audio_capture import find_output_device
from ..config import FRAME_MS, FRAME_SIZE, SAMPLE_RATE
from .base import MicController


class VirtualMicController(MicController):
    def __init__(self, device_name: str, preroll_ms: int):
        self._device_name = device_name
        preroll_frames = max(0, round(preroll_ms / FRAME_MS))
        self._preroll: collections.deque[np.ndarray] = collections.deque(
            maxlen=preroll_frames
        )
        # 输出队列: feed() 投递, 输出流回调消费; 限长防积压
        self._out_q: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)
        self._stream: sd.OutputStream | None = None
        self._is_open = False
        self._silence = np.zeros(FRAME_SIZE, dtype=np.float32)

    def start(self) -> None:
        device = find_output_device(self._device_name)
        if device is None:
            raise RuntimeError(
                f"找不到虚拟声卡输出设备 '{self._device_name}'。"
                "请先安装 VB-Audio Virtual Cable (https://vb-audio.com/Cable/) 并重启电脑。"
            )
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            device=device,
            channels=1,
            dtype="float32",
            callback=self._out_callback,
        )
        self._stream.start()

    def _out_callback(self, outdata, frames, time_info, status):  # noqa: ANN001
        try:
            frame = self._out_q.get_nowait()
        except queue.Empty:
            frame = self._silence
        outdata[:, 0] = frame

    def _enqueue(self, frame: np.ndarray) -> None:
        try:
            self._out_q.put_nowait(frame)
        except queue.Full:
            # 积压则丢最旧一帧, 保持低延迟
            try:
                self._out_q.get_nowait()
                self._out_q.put_nowait(frame)
            except queue.Empty:
                pass

    def set_open(self, is_open: bool) -> None:
        if is_open and not self._is_open:
            # 刚开麦: 先把预滚缓冲补进去
            for f in list(self._preroll):
                self._enqueue(f)
        self._is_open = is_open

    def feed(self, frame: np.ndarray) -> None:
        # 始终维护预滚缓冲 (即使没开麦)
        self._preroll.append(frame.copy())
        if self._is_open:
            self._enqueue(frame.copy())
        else:
            self._enqueue(self._silence)

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
