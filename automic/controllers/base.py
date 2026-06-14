"""控制器接口。"""

from __future__ import annotations

import abc

import numpy as np


class MicController(abc.ABC):
    """所有控制器统一接口: VAD 用 set_open 告诉它该不该开麦。"""

    @abc.abstractmethod
    def start(self) -> None:
        """初始化资源 (打开设备等)。"""

    @abc.abstractmethod
    def set_open(self, is_open: bool) -> None:
        """开麦(True) / 关麦(False)。"""

    def feed(self, frame: np.ndarray) -> None:
        """喂入实时音频帧 (模式C 需要; 模式A 忽略)。"""

    @abc.abstractmethod
    def stop(self) -> None:
        """释放资源, 退出时恢复到安全状态。"""
