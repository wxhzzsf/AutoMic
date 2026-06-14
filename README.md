# AutoMic

[![Build & Release](https://github.com/wxhzzsf/AutoMic/actions/workflows/release.yml/badge.svg)](https://github.com/wxhzzsf/AutoMic/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Voice-activated microphone for games.** Built for playing with **Open Mic** on:
only your **human voice** is passed through to your teammates, while **keyboard and
mouse sounds are intercepted** and never reach them. Your mic stays silent until you
actually speak. Made with games like PUBG in mind. (中文说明见下方。)

The interception is done by the **Silero VAD (Voice Activity Detection) neural
network**, which tells real human speech apart from transient noises (key clicks,
mouse clicks), plus a minimum-speech-duration filter so a single keystroke never
opens the mic. When you're not talking, AutoMic outputs silence to your teammates —
so they only ever hear your voice, not your clicky keyboard or mouse.

## How it works

```
Real mic -> AutoMic (detects speech, outputs silence when you're quiet)
         -> VB-CABLE (virtual audio cable) -> the game's microphone
```

AutoMic listens to your **real** mic (never muted, so detection always works) and
forwards audio to a virtual cable only while you're talking. The game listens to the
virtual cable. Nothing is injected into the game and no keystrokes are simulated, so
**it is unrelated to anti-cheat** (works with PUBG/BattlEye): selecting a virtual mic
is no different from picking any USB mic.

## Install (one click)

1. Download **`AutoMic-Setup.exe`** from the [Releases](https://github.com/wxhzzsf/AutoMic/releases) page and run it.
2. The installer will, in one go:
   - install AutoMic,
   - download & silently install the **VB-CABLE** virtual audio driver from the official site (skip the checkbox if you already have it),
   - create shortcuts and (optionally) start AutoMic with Windows.
3. If VB-CABLE was just installed, **reboot once** when asked.

After that, just run AutoMic. It **automatically routes the virtual mic as your
default recording device** (and restores your real mic when you quit), so you don't
have to touch Windows sound settings. In the game, set voice chat to **Open Mic**.

> Keep AutoMic running (it lives in the system tray) while you play.

## Tray controls

A small tray icon shows the state:

- **Gray** = paused · **Blue** = enabled, standby (not speaking) · **Green** = mic open (speaking)

Right-click for: enable/pause, pick microphone, toggle "auto set as default mic",
open config, quit.

## Tuning (optional)

Tray -> "open config file" edits `config.yaml` (in `%APPDATA%\AutoMic`). Restart after saving:

| key | meaning |
|---|---|
| `threshold` | speech probability 0–1; raise it (e.g. 0.6) if it opens too easily |
| `min_speech_ms` | how long speech must persist before opening; raise to reject key clicks |
| `hangover_ms` | how long to stay open after you stop (avoids choppiness) |
| `preroll_ms` | audio kept before opening so the first syllable isn't clipped |
| `input_gain` | amplify a very quiet mic before detection |
| `input_device` | mic name substring (empty = system default) |
| `auto_route_default_device` | auto-set the virtual mic as default recording device |

## Build from source

Requires Python 3.10+ ([download](https://www.python.org/downloads/), tick *Add to PATH*).

```bat
install.bat            REM create venv + install deps
.venv\Scripts\python.exe -m automic        REM run the tray app
.venv\Scripts\python.exe -m automic.cli    REM console debug version
build.bat              REM build dist\AutoMic.exe and (if Inno Setup is installed) the installer
```

To also build the installer locally, install [Inno Setup](https://jrsoftware.org/isdl.php).
CI builds both automatically on tag push (see `.github/workflows/release.yml`).

## Project structure

```
automic/
  config.py            config load/defaults (%APPDATA%\AutoMic\config.yaml)
  audio_capture.py     mic capture (16kHz/512-sample frames) + device resolve
  vad_engine.py        Silero VAD + open/close state machine
  engine.py            capture -> VAD -> controller wiring
  win_audio.py         set/restore default recording device (IPolicyConfig)
  controllers/
    base.py            controller interface
    virtual_mic.py     gate audio to VB-CABLE + pre-roll buffer
  cli.py               console entry
  tray.py              system-tray GUI entry
app.py                 PyInstaller entry
automic.spec           PyInstaller config
installer/AutoMic.iss  Inno Setup one-click installer
tools/make_icon.py     generates assets/automic.ico
```

## FAQ

- **Tray stays gray / "virtual cable not found"**: VB-CABLE isn't installed or needs a reboot.
- **First syllable cut off**: increase `preroll_ms` or lower `min_speech_ms`.
- **Keyboard still opens the mic**: increase `threshold` and `min_speech_ms`.
- **My voice is very quiet**: increase `input_gain`.

## Acknowledgements

- [Silero VAD](https://github.com/snakers4/silero-vad) — speech detection model (MIT)
- [VB-CABLE](https://vb-audio.com/Cable/) by VB-Audio — virtual audio device (donationware; downloaded at install, not bundled)

## License

MIT — see [LICENSE](LICENSE).

---

# AutoMic（中文）

**专为游戏「开放麦克风（Open Mic）」打造。** 只把你的**人声**传给队友，**键盘和鼠标的声音会被拦截**、不会传出去；不说话时麦克风保持静默。专为吃鸡（PUBG）这类开麦场景设计。

拦截靠 **Silero VAD 人声检测神经网络**（能区分人声和键盘/鼠标瞬态噪声），再叠加「最短人声时长」过滤，单次敲键不会让麦打开。不说话时 AutoMic 向队友输出静音——队友只会听到你的人声，不会听到你噼里啪啦的键盘和鼠标声。

## 原理

```
真麦克风 → AutoMic（检测人声，不说话时输出静音）→ VB-CABLE 虚拟声卡 → 游戏麦克风
```

AutoMic 听你的**真麦**（永不静音，所以检测一直正常），只在你说话时把声音转发给虚拟声卡。游戏听虚拟声卡。不注入游戏、不模拟按键，**与反作弊无关**（PUBG/BattlEye 适用）。

## 一键安装

1. 到 [Releases](https://github.com/wxhzzsf/AutoMic/releases) 下载 **`AutoMic-Setup.exe`** 并运行。
2. 安装包会一次性完成：装 AutoMic、从官网下载并静默安装 **VB-CABLE** 虚拟声卡（已装过可取消勾选）、建快捷方式、可选开机自启。
3. 若刚装了 VB-CABLE，按提示**重启一次**。

之后直接运行 AutoMic，它会**自动把虚拟麦设为系统默认录音设备**（退出时自动恢复成你的真麦），无需手动改 Windows 声音设置。游戏里语音设成「开放麦克风」。

> 玩的时候让 AutoMic 一直挂在托盘。

## 托盘

灰=暂停，蓝=待命（没说话），绿=开麦（正在说话）。右键可：启用/暂停、选麦克风、开关「自动设为默认麦克风」、打开配置、退出。

## 调参

托盘 →「打开配置文件」改 `config.yaml`（在 `%APPDATA%\AutoMic`），存盘后重启：`threshold`（阈值，调高更防误触）、`min_speech_ms`（更防键盘误触）、`hangover_ms`（防切碎）、`preroll_ms`（防切第一个字）、`input_gain`（电平低的麦放大）。

## 许可

MIT。VB-CABLE 为 VB-Audio 的捐赠制软件，安装时从官网下载、未二次打包分发。
