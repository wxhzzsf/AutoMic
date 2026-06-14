"""系统托盘 GUI (普通用户入口)。

图标颜色: 绿色=正在开麦(说话), 蓝色=已启用待命(没说话), 灰色=已暂停。
右键菜单: 启用/暂停、切换 A/C 模式、选择麦克风、打开配置、退出。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

import sounddevice as sd
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from . import __app_name__, __version__
from .config import Config, config_path, load_config, save_config
from .engine import AutoMicEngine

_COLORS = {
    "open": (46, 204, 113),     # 绿: 开麦
    "standby": (52, 152, 219),  # 蓝: 待命
    "paused": (149, 165, 166),  # 灰: 暂停
}


def _make_icon(color: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 圆底
    d.ellipse((4, 4, 60, 60), fill=color)
    # 简易麦克风图形 (白色)
    w = (255, 255, 255)
    d.rounded_rectangle((26, 16, 38, 40), radius=6, fill=w)
    d.arc((22, 28, 42, 46), start=0, end=180, fill=w, width=3)
    d.line((32, 46, 32, 52), fill=w, width=3)
    d.line((25, 52, 39, 52), fill=w, width=3)
    return img


class TrayApp:
    def __init__(self) -> None:
        self._cfg: Config = load_config()
        self._engine: AutoMicEngine | None = None
        self._restart_lock = threading.Lock()
        self._icon = Icon(
            __app_name__,
            icon=_make_icon(_COLORS["paused"]),
            title=__app_name__,
            menu=self._build_menu(),
        )

    # ---- 引擎管理 ----
    def _start_engine(self) -> None:
        self._engine = AutoMicEngine(self._cfg, on_status=self._on_status)
        try:
            self._engine.start()
        except Exception as exc:
            self._engine = None
            # 不再自动回退到模式A (模式A 会死锁), 保留用户配置, 仅提示。
            self._notify(f"启动失败: {exc}")

    def _restart_engine(self) -> None:
        with self._restart_lock:
            if self._engine is not None:
                self._engine.stop()
                self._engine = None
            self._start_engine()

    # ---- 状态 / 图标 ----
    def _on_status(self, active: bool, is_open: bool) -> None:
        if not active:
            key = "paused"
        elif is_open:
            key = "open"
        else:
            key = "standby"
        self._icon.icon = _make_icon(_COLORS[key])
        state = {"paused": "已暂停", "open": "开麦中", "standby": "待命中"}[key]
        self._icon.title = f"{__app_name__} - {state}"

    def _notify(self, msg: str) -> None:
        try:
            self._icon.notify(msg, __app_name__)
        except Exception:
            pass

    # ---- 菜单 ----
    def _build_menu(self) -> Menu:
        return Menu(
            MenuItem(f"{__app_name__} {__version__}", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(
                "启用 (检测到人声才开麦)",
                self._on_toggle_active,
                checked=lambda i: self._engine is not None and self._engine.is_active,
            ),
            Menu.SEPARATOR,
            MenuItem("麦克风", self._device_items()),
            MenuItem(
                "自动设为默认麦克风 (游戏免设置)",
                self._on_toggle_autoroute,
                checked=lambda i: self._cfg.auto_route_default_device,
            ),
            MenuItem("打开配置文件", self._open_config),
            Menu.SEPARATOR,
            MenuItem("退出", self._on_quit),
        )

    def _device_items(self):
        items = [
            MenuItem(
                "系统默认",
                lambda i: self._set_device(""),
                checked=lambda i: not self._cfg.input_device,
                radio=True,
            )
        ]
        seen = set()
        for dev in sd.query_devices():
            name = dev["name"]
            if dev.get("max_input_channels", 0) > 0 and name not in seen:
                seen.add(name)
                items.append(
                    MenuItem(
                        name[:40],
                        (lambda n: lambda i: self._set_device(n))(name),
                        checked=(lambda n: lambda i: self._cfg.input_device == n)(name),
                        radio=True,
                    )
                )
        return Menu(*items)

    # ---- 菜单回调 ----
    def _on_toggle_active(self, icon, item) -> None:  # noqa: ANN001
        if self._engine is not None:
            self._engine.toggle_active()

    def _on_toggle_autoroute(self, icon, item) -> None:  # noqa: ANN001
        self._cfg.auto_route_default_device = not self._cfg.auto_route_default_device
        save_config(self._cfg)
        self._restart_engine()
        self._icon.update_menu()

    def _set_device(self, name: str) -> None:
        if self._cfg.input_device == name:
            return
        self._cfg.input_device = name
        save_config(self._cfg)
        self._restart_engine()
        self._icon.update_menu()

    def _open_config(self, icon, item) -> None:  # noqa: ANN001
        path = config_path()
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            self._notify(f"打开配置失败: {exc}")

    def _on_quit(self, icon, item) -> None:  # noqa: ANN001
        if self._engine is not None:
            self._engine.stop()
            self._engine = None
        icon.stop()

    # ---- 运行 ----
    def run(self) -> None:
        def setup(icon):  # noqa: ANN001
            icon.visible = True
            self._start_engine()

        self._icon.run(setup=setup)


def main() -> int:
    TrayApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
