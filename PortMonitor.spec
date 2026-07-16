# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec: 端口卫士 / Port Monitor
- 单文件 --onefile
- 无控制台窗口 --windowed
- 打包 assets/ 目录（含收款码、README）
- 排除不需要的 Qt 大模块，减小体积
"""
import sys
from pathlib import Path

APP_NAME = "PortMonitor"
ROOT = Path(SPECPATH).resolve()

datas = [(str(ROOT / "assets"), "assets")]

# 只需要 QtCore / QtGui / QtWidgets，把其他大模块（QtWebEngine、Qt3D、Multimedia 等）排除
excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtWebView",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras", "PySide6.Qt3DLogic",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQml", "PySide6.QtQuickWidgets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
    "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects",
    "PySide6.QtHelp", "PySide6.QtSql", "PySide6.QtDesigner",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSpatialAudio", "PySide6.QtStateMachine",
    "PySide6.QtScxml", "PySide6.QtSvg", "PySide6.QtSvgWidgets",
    "PySide6.QtTest", "PySide6.QtTextToSpeech",
    "tkinter", "unittest", "pydoc_data", "test",
]

a = Analysis(
    ["port_monitor.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 平台差异
if sys.platform == "darwin":
    icon = str(ROOT / "assets" / "icon.icns") if (ROOT / "assets" / "icon.icns").exists() else None
elif sys.platform == "win32":
    icon = str(ROOT / "assets" / "icon.ico") if (ROOT / "assets" / "icon.ico").exists() else None
else:
    icon = None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # 关掉 UPX：macOS 上会导致启动被 Gatekeeper 拦；节省的空间不值
    console=False,    # 无黑窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None, # 让 PyInstaller 自己决定（macOS 会是当前架构）
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

# macOS 额外打成 .app 包
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier="com.rgh.portmonitor",
        info_plist={
            "CFBundleName": "端口卫士",
            "CFBundleDisplayName": "端口卫士 Port Monitor",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
