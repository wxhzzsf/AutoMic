"""命令行入口 (高级用户 / 调试用)。普通用户请用托盘版 (run_tray)。"""

from __future__ import annotations

import argparse
import sys
import time

from . import __app_name__, __version__
from .audio_capture import list_devices
from .config import config_path, load_config
from .engine import AutoMicEngine


def _on_status(active: bool, is_open: bool) -> None:
    state = "SPEECH ON  (开麦)" if is_open else "SPEECH OFF (关麦)"
    if not active:
        state = "PAUSED     (暂停, 麦克风常开)"
    print(f"\r[{time.strftime('%H:%M:%S')}] {state}        ", end="", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="automic", description=f"{__app_name__} {__version__} - 语音激活开麦"
    )
    parser.add_argument(
        "--list-devices", action="store_true", help="列出所有音频设备后退出"
    )
    parser.add_argument("--config", default=None, help="指定 config.yaml 路径")
    args = parser.parse_args(argv)

    if args.list_devices:
        print(list_devices())
        return 0

    cfg = load_config(args.config)
    print(f"{__app_name__} {__version__}")
    print(f"配置文件: {args.config or config_path()}")
    print(
        f"麦克风='{cfg.input_device or '系统默认'}'  虚拟声卡='{cfg.virtual_output_device}'  "
        f"阈值={cfg.threshold}  最短人声={cfg.min_speech_ms}ms  "
        f"hangover={cfg.hangover_ms}ms"
    )

    engine = AutoMicEngine(cfg, on_status=_on_status)
    try:
        engine.start()
    except Exception as exc:
        print(f"\n启动失败: {exc}", file=sys.stderr)
        return 1

    print("运行中... 说话试试 (Ctrl+C 退出)\n")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n正在退出...")
    finally:
        engine.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
