"""核心引擎: 把 采集 -> VAD -> 控制器 串起来, 供 CLI 和托盘共用。"""

from __future__ import annotations

import threading
from typing import Callable

import numpy as np

from .audio_capture import AudioCapture, resolve_input_device
from .config import Config
from .controllers.base import MicController
from .controllers.virtual_mic import VirtualMicController
from .vad_engine import SileroVAD, VADStateMachine

# 状态回调: (is_active, is_open) -> None
StatusCallback = Callable[[bool, bool], None]


def make_controller(cfg: Config) -> MicController:
    return VirtualMicController(cfg.virtual_output_device, cfg.preroll_ms)


class AutoMicEngine:
    def __init__(self, cfg: Config, on_status: StatusCallback | None = None):
        self._cfg = cfg
        self._on_status = on_status
        self._lock = threading.Lock()

        self._vad: SileroVAD | None = None
        self._sm: VADStateMachine | None = None
        self._controller: MicController | None = None
        self._capture: AudioCapture | None = None
        self._router = None  # DefaultMicRouter | None

        self._active = cfg.start_active
        self._is_open = False

    # ---- 生命周期 ----
    def start(self) -> None:
        # 先确定真实麦克风(在改默认设备之前!), 排除虚拟麦避免自采自
        exclude = self._cfg.route_device_name if self._cfg.auto_route_default_device else ""
        device = resolve_input_device(self._cfg.input_device, exclude)
        # 再把虚拟麦设为系统默认录音设备
        self._route_to_virtual_mic()
        self._vad = SileroVAD()
        self._controller = make_controller(self._cfg)
        self._controller.start()
        self._sm = VADStateMachine(
            threshold=self._cfg.threshold,
            min_speech_ms=self._cfg.min_speech_ms,
            hangover_ms=self._cfg.hangover_ms,
            on_speech_start=self._open_mic,
            on_speech_end=self._close_mic,
        )
        self._capture = AudioCapture(device, self._on_frame)
        self._capture.start()

        # 初始状态: 激活则关麦待命; 暂停则开麦(等于不干预)
        if self._active:
            self._close_mic()
        else:
            self._open_mic()
        self._emit_status()

    def stop(self) -> None:
        if self._capture is not None:
            self._capture.stop()
            self._capture = None
        if self._controller is not None:
            self._controller.stop()
            self._controller = None
        if self._router is not None:
            self._router.restore()
            self._router = None

    def _route_to_virtual_mic(self) -> None:
        """把虚拟麦设为系统默认录音设备 (失败不影响主流程, 用户可手动设)。"""
        self._router = None
        if not self._cfg.auto_route_default_device:
            return
        try:
            from .win_audio import DefaultMicRouter

            router = DefaultMicRouter(self._cfg.route_device_name)
            if router.apply():
                self._router = router
        except Exception:
            self._router = None

    # ---- 控制 ----
    def set_active(self, active: bool) -> None:
        with self._lock:
            self._active = active
            if self._vad is not None:
                self._vad.reset()
            if self._sm is not None:
                self._sm.reset()
            if active:
                self._close_mic()  # 重新待命
            else:
                self._open_mic()   # 暂停 = 麦克风正常常开
            self._emit_status()

    def toggle_active(self) -> None:
        self.set_active(not self._active)

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_open(self) -> bool:
        return self._is_open

    # ---- 内部 ----
    def _on_frame(self, frame: np.ndarray) -> None:
        # 输入增益: 放大电平很低的麦克风(如蓝牙耳机), 同时让 VAD 和游戏都听得更清楚
        gain = self._cfg.input_gain
        if gain != 1.0:
            frame = np.clip(frame * gain, -1.0, 1.0).astype(np.float32)
        if self._active and self._vad is not None and self._sm is not None:
            prob = self._vad(frame)
            self._sm.process(prob)
        if self._controller is not None:
            self._controller.feed(frame)

    def _open_mic(self) -> None:
        self._is_open = True
        if self._controller is not None:
            self._controller.set_open(True)
        self._emit_status()

    def _close_mic(self) -> None:
        self._is_open = False
        if self._controller is not None:
            self._controller.set_open(False)
        self._emit_status()

    def _emit_status(self) -> None:
        if self._on_status is not None:
            self._on_status(self._active, self._is_open)
