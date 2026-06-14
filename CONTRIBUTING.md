# Contributing to AutoMic

Thanks for your interest! AutoMic is a small Windows utility, contributions welcome.

## Dev setup

```bat
install.bat
.venv\Scripts\python.exe -m automic.cli    REM console version, prints SPEECH ON/OFF
```

- Python 3.10+ on Windows.
- Core flow: `audio_capture` -> `vad_engine` (Silero VAD + state machine) -> `controllers/virtual_mic` (gates to VB-CABLE). `engine.py` wires it together; `tray.py`/`cli.py` are entry points.

## Building

```bat
build.bat
```

Produces `dist\AutoMic.exe` and, if [Inno Setup](https://jrsoftware.org/isdl.php) is installed, `installer\Output\AutoMic-Setup.exe`. CI builds both on tag push.

## Guidelines

- Keep the app dependency-light and the exe small (we intentionally exclude `torch`).
- Don't bundle VB-CABLE; it's downloaded from the official site at install time.
- Test changes with the console version (`-m automic.cli`) before building the exe.
- Open an issue to discuss larger changes (e.g. noise suppression, push-to-talk mode) first.

## Releasing

Tag a commit `vX.Y.Z` and push the tag; the GitHub Actions workflow builds and publishes the release.
