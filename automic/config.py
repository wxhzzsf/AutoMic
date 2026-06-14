"""配置: 数据类 + 从 yaml 读取 / 生成带注释的默认配置。"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict, dataclass, field

import yaml

# 采样率固定 16kHz, Silero VAD 要求每帧 512 样本 (约 32ms)。
SAMPLE_RATE = 16000
FRAME_SIZE = 512
FRAME_MS = 1000.0 * FRAME_SIZE / SAMPLE_RATE  # 单帧时长(ms), 约 32ms


@dataclass
class Config:
    # 输入麦克风设备名 (留空 = 系统默认录音设备)。可填名称的一部分, 大小写不敏感。
    input_device: str = ""

    # 输入增益(放大倍数)。蓝牙耳机等电平很低的麦克风调大(如 8~16), 否则检测不到人声。
    input_gain: float = 1.0

    # 虚拟声卡输出设备名 (默认匹配 VB-Cable 的 "CABLE Input")
    virtual_output_device: str = "CABLE Input"

    # 自动把虚拟麦设为系统默认录音设备 (免手动去 Windows 声音设置), 退出时自动恢复
    auto_route_default_device: bool = True
    # 设为默认的录音设备名 (游戏读它; VB-Cable 的录音端是 "CABLE Output")
    route_device_name: str = "CABLE Output"

    # --- VAD 状态机参数 ---
    # 人声概率阈值 (0~1), 越高越不容易开麦
    threshold: float = 0.5
    # 必须连续检出人声多少毫秒才开麦 -> 过滤单次敲键/点鼠标的短脉冲
    min_speech_ms: int = 120
    # 停止说话后保持开麦多久再关闭 -> 避免一句话中间停顿被切碎
    hangover_ms: int = 400

    # 模式C: 开麦前保留多少毫秒的预滚音频, 避免切掉第一个字
    preroll_ms: int = 200

    # 启动时是否立即激活 (False = 启动后处于暂停, 需在托盘里开启)
    start_active: bool = True

    def normalized(self) -> "Config":
        """约束取值范围, 防止配置写坏。"""
        self.input_gain = min(max(self.input_gain, 1.0), 64.0)
        self.auto_route_default_device = bool(self.auto_route_default_device)
        self.threshold = min(max(self.threshold, 0.05), 0.95)
        self.min_speech_ms = max(self.min_speech_ms, 0)
        self.hangover_ms = max(self.hangover_ms, 0)
        self.preroll_ms = max(self.preroll_ms, 0)
        return self


_YAML_TEMPLATE = """\
# ===== AutoMic 配置 (改完保存后重启程序生效) =====
# 工作方式: 真麦克风 -> AutoMic(检测人声) -> 虚拟声卡 CABLE Input -> 游戏麦克风选 CABLE Output
# 需先安装 VB-Audio Virtual Cable: https://vb-audio.com/Cable/

# 麦克风设备名 (留空=系统默认)。可只填名字的一部分, 例如 "USB" 或 "Realtek"。
input_device: "{input_device}"

# 输入增益(放大倍数)。蓝牙耳机等麦克风电平很低、检测不到人声时调大, 如 8 或 16。
input_gain: {input_gain}

# 虚拟声卡输入端名称 (VB-Cable 默认是 CABLE Input)
virtual_output_device: "{virtual_output_device}"

# 自动把虚拟麦设为系统默认录音设备(免手动设置), 退出 AutoMic 时自动恢复成原来的麦克风
auto_route_default_device: {auto_route_default_device}
# 设为默认的录音设备名 (游戏读它; VB-Cable 的录音端是 CABLE Output)
route_device_name: "{route_device_name}"

# --- 人声检测灵敏度 ---
threshold: {threshold}        # 人声概率阈值 0~1, 调高=更难开麦(更防误触), 调低=更灵敏
min_speech_ms: {min_speech_ms}     # 连续多少毫秒人声才开麦, 调高=更防键盘误触发
hangover_ms: {hangover_ms}      # 停说话后延迟多少毫秒关麦, 调高=话中停顿不会被切

# 模式C: 开麦前保留的预滚音频毫秒数, 防止切掉第一个字
preroll_ms: {preroll_ms}

# 启动后是否立即生效 (false = 启动处于暂停状态)
start_active: {start_active}
"""


def app_dir() -> str:
    """配置文件所在目录。

    打包成 exe 时用 %APPDATA%\\AutoMic (装到 Program Files 后 exe 目录不可写);
    开发时用项目根目录。
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.dirname(sys.executable)
        path = os.path.join(base, "AutoMic")
        os.makedirs(path, exist_ok=True)
        return path
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def config_path() -> str:
    return os.path.join(app_dir(), "config.yaml")


def load_config(path: str | None = None) -> Config:
    """读取配置; 不存在则生成默认 config.yaml 并返回默认值。"""
    path = path or config_path()
    if not os.path.exists(path):
        cfg = Config()
        save_default_config(path, cfg)
        return cfg.normalized()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**known).normalized()


def save_default_config(path: str, cfg: Config | None = None) -> None:
    cfg = cfg or Config()
    text = _YAML_TEMPLATE.format(
        input_device=cfg.input_device,
        input_gain=cfg.input_gain,
        virtual_output_device=cfg.virtual_output_device,
        auto_route_default_device=str(cfg.auto_route_default_device).lower(),
        route_device_name=cfg.route_device_name,
        threshold=cfg.threshold,
        min_speech_ms=cfg.min_speech_ms,
        hangover_ms=cfg.hangover_ms,
        preroll_ms=cfg.preroll_ms,
        start_active=str(cfg.start_active).lower(),
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def save_config(cfg: Config, path: str | None = None) -> None:
    """托盘改了设置后回写 (保留模板注释)。"""
    save_default_config(path or config_path(), cfg)
