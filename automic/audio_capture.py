"""麦克风采集: sounddevice 16kHz 单声道输入流, 按 512 样本帧回调。"""

from __future__ import annotations

from typing import Callable

import numpy as np
import sounddevice as sd

from .config import FRAME_SIZE, SAMPLE_RATE

FrameCallback = Callable[[np.ndarray], None]


def find_input_device(name: str | None) -> int | None:
    """按名称(子串, 大小写不敏感)找输入设备索引; 留空返回 None (用系统默认)。"""
    if not name:
        return None
    name = name.lower()
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0 and name in dev["name"].lower():
            return idx
    return None


def resolve_input_device(name: str | None, exclude_substr: str = "") -> int | None:
    """确定要采集的麦克风索引。

    传了具体名字就用它; 否则取当前系统默认录音设备 —— 但**绝不**选中要排除的设备
    (比如 CABLE Output 虚拟麦), 避免自动路由把默认设备改成虚拟麦后自己采自己造成死循环。
    """
    if name:
        return find_input_device(name)

    excl = exclude_substr.lower()
    # 优先用当前默认录音设备 (前提是它不是被排除的虚拟麦)
    try:
        default = sd.query_devices(kind="input")
        dname = default["name"]
        if not excl or excl not in dname.lower():
            return find_input_device(dname)
    except Exception:
        pass
    # 兜底: 第一个不是被排除项的输入设备
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            if excl and excl in dev["name"].lower():
                continue
            return idx
    return None


def find_output_device(name: str | None) -> int | None:
    """按名称找输出设备索引 (模式C 写入虚拟声卡用)。"""
    if not name:
        return None
    name = name.lower()
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_output_channels", 0) > 0 and name in dev["name"].lower():
            return idx
    return None


def list_devices() -> str:
    """返回可读的设备列表 (供 --list-devices 和排错)。"""
    lines = []
    for idx, dev in enumerate(sd.query_devices()):
        kind = []
        if dev.get("max_input_channels", 0) > 0:
            kind.append("输入")
        if dev.get("max_output_channels", 0) > 0:
            kind.append("输出")
        lines.append(f"[{idx}] {dev['name']}  ({'/'.join(kind) or '无'})")
    return "\n".join(lines)


class AudioCapture:
    """打开麦克风输入流, 把每帧 (float32, [-1,1], 512样本) 交给回调。"""

    def __init__(self, device: int | None, on_frame: FrameCallback):
        self._device = device
        self._on_frame = on_frame
        self._stream: sd.InputStream | None = None

    def _callback(self, indata, frames, time_info, status):  # noqa: ANN001
        # indata shape: (frames, 1) float32。展平成一维交给 VAD。
        self._on_frame(indata[:, 0].copy())

    def start(self) -> None:
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SIZE,
            device=self._device,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
