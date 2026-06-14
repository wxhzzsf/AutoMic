# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包脚本: 产出单文件 AutoMic.exe (内置 Python + Silero 模型)。

打包: pyinstaller automic.spec  (或直接运行 build.bat)
"""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 把 silero_vad 自带的 onnx 模型一起打进 exe
datas = collect_data_files("silero_vad")
# onnxruntime 的动态库
binaries = collect_dynamic_libs("onnxruntime")

hiddenimports = ["pystray._win32", "comtypes", "pycaw"]

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["torch", "matplotlib", "tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AutoMic",
    icon="assets/automic.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 托盘程序, 不弹黑窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
