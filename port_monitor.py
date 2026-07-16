# -*- coding: utf-8 -*-
"""
端口占用监控工具 (Port Monitor)
- 无边框圆角窗口 + 自定义标题栏
- 展示本机端口占用：应用名 / 进程号 / 端口号 / CPU% / 内存% / 操作
- 一键停止（杀进程），杀掉后该行从界面移除
- 标题栏：赞助（微信/支付宝/QQ 收款码切换）、GitHub 跳转、最小化/最大化/关闭

依赖: PySide6, psutil
运行: python port_monitor.py

Copyright (c) 2026 rgh
Project: https://github.com/vfaner/port-monitor

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import sys
import webbrowser

import psutil
from PySide6.QtCore import Qt, QThread, Signal, QPoint, QSize, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter, QFont, QCursor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QDialog,
    QGraphicsDropShadowEffect, QSizePolicy, QMessageBox, QLineEdit, QFrame,
)

# ------------------------------------------------------------------ 配置 ----
GITHUB_URL = "https://github.com/vfaner/port-monitor"
APP_NAME = "端口卫士 · Port Monitor"
APP_VERSION = "1.0.0"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# 收款码：把真实收款码图片放到 assets/ 下即可自动加载
SPONSOR_CHANNELS = [
    ("微信", "#1AAD19", os.path.join(ASSETS_DIR, "wechat.png")),
    ("支付宝", "#1677FF", os.path.join(ASSETS_DIR, "alipay.png")),
    ("QQ", "#12B7F5", os.path.join(ASSETS_DIR, "qq.png")),
]


# ============================================================ 后台扫描线程 ==
from collections import namedtuple

# 逐进程回退时使用的连接包装，补齐 pid 字段
_Conn = namedtuple("_Conn", ["pid", "laddr", "status"])


class ScanThread(QThread):
    """在后台采集端口占用信息，避免界面卡顿。"""
    result = Signal(list)

    def run(self):
        rows = self._collect()
        self.result.emit(rows)

    @staticmethod
    def _collect():
        rows = {}
        try:
            conns = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            conns = ScanThread._collect_per_process()

        for c in conns:
            if not c.laddr:
                continue
            pid = c.pid
            port = c.laddr.port
            # 只关心真正占用端口的进程：有 pid、端口有效、处于监听状态
            # (TCP LISTEN 或 UDP 的 NONE 状态都代表本机在该端口上开放服务)
            if pid is None or not port:
                continue
            if c.status not in (psutil.CONN_LISTEN, psutil.CONN_NONE, "NONE"):
                continue
            key = (pid, port)
            if key in rows:
                continue
            try:
                proc = psutil.Process(pid)
                with proc.oneshot():
                    name = proc.name()
                    cpu = proc.cpu_percent(interval=None)
                    mem = proc.memory_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                name, cpu, mem = "未知进程", 0.0, 0.0
            rows[key] = {
                "name": name,
                "pid": pid,
                "port": port,
                "cpu": cpu,
                "mem": mem,
                "status": c.status,
            }

        data = list(rows.values())
        data.sort(key=lambda r: r["port"])
        return data

    @staticmethod
    def _collect_per_process():
        """无权限读取全局连接时，退化为逐进程采集（仅能拿到当前用户进程）。

        逐进程返回的连接 namedtuple 不含 pid 字段，这里用轻量包装补上，
        使其与 psutil.net_connections() 的元素保持相同接口（.pid/.laddr/.status）。
        """
        conns = []
        for proc in psutil.process_iter(["pid"]):
            try:
                for c in proc.net_connections(kind="inet"):
                    conns.append(_Conn(pid=proc.pid, laddr=c.laddr,
                                       status=c.status))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return conns


# =============================================================== 收款码弹窗 ==
class SponsorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 480)
        self._current = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(
            "#card{background:#ffffff;border-radius:16px;}"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        # 标题行
        top = QHBoxLayout()
        title = QLabel("请作者喝杯咖啡 ☕")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:#222;")
        close = QPushButton("✕")
        close.setCursor(Qt.PointingHandCursor)
        close.setFixedSize(26, 26)
        close.setStyleSheet(
            "QPushButton{border:none;border-radius:13px;color:#888;font-size:14px;}"
            "QPushButton:hover{background:#f0f0f0;color:#333;}"
        )
        close.clicked.connect(self.accept)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(close)
        lay.addLayout(top)

        # 渠道切换按钮
        tabs = QHBoxLayout()
        tabs.setSpacing(10)
        self.tab_btns = []
        for i, (label, color, _) in enumerate(SPONSOR_CHANNELS):
            b = QPushButton(label)
            b.setCursor(Qt.PointingHandCursor)
            b.setCheckable(True)
            b.setFixedHeight(34)
            b.setProperty("accent", color)
            b.clicked.connect(lambda _=False, idx=i: self.switch(idx))
            self.tab_btns.append(b)
            tabs.addWidget(b)
        lay.addLayout(tabs)

        # 二维码显示
        self.qr = QLabel()
        self.qr.setAlignment(Qt.AlignCenter)
        self.qr.setFixedSize(280, 280)
        self.qr.setStyleSheet(
            "background:#fafafa;border:1px dashed #ddd;border-radius:12px;"
        )
        lay.addWidget(self.qr, alignment=Qt.AlignCenter)

        self.tip = QLabel()
        self.tip.setAlignment(Qt.AlignCenter)
        self.tip.setStyleSheet("color:#999;font-size:12px;")
        lay.addWidget(self.tip)

        lay.addStretch()
        self.switch(0)

    def switch(self, idx):
        self._current = idx
        label, color, path = SPONSOR_CHANNELS[idx]
        for i, b in enumerate(self.tab_btns):
            active = i == idx
            c = b.property("accent")
            if active:
                b.setStyleSheet(
                    f"QPushButton{{border:none;border-radius:8px;color:#fff;"
                    f"font-weight:bold;background:{c};}}"
                )
            else:
                b.setStyleSheet(
                    "QPushButton{border:none;border-radius:8px;color:#666;"
                    "background:#f2f3f5;} QPushButton:hover{background:#e8eaed;}"
                )
            b.setChecked(active)

        if os.path.exists(path):
            pix = QPixmap(path).scaled(
                268, 268, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.qr.setPixmap(pix)
            self.tip.setText(f"打开{label}扫一扫，感谢支持！")
        else:
            self.qr.setPixmap(self._placeholder(label, color))
            self.tip.setText(f"将收款码保存为 assets/{os.path.basename(path)}")

    @staticmethod
    def _placeholder(label, color):
        pix = QPixmap(268, 268)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 268, 268, 12, 12)
        p.setPen(QColor("#ffffff"))
        f = QFont()
        f.setPointSize(15)
        f.setBold(True)
        p.setFont(f)
        p.drawText(pix.rect(), Qt.AlignCenter, f"{label}\n收款码\n\n(放入 assets 目录)")
        p.end()
        return pix

    # 支持拖动
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and hasattr(self, "_drag"):
            self.move(e.globalPosition().toPoint() - self._drag)
            e.accept()


# ============================================================= 标题栏按钮 ==
def make_tool_button(text, tip, size=32):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedSize(size, size)
    b.setToolTip(tip)
    return b


# ================================================================= 主窗口 ==
class PortMonitor(QWidget):
    COLS = ["应用名", "进程号", "端口号", "CPU %", "内存 %", "操作"]

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(920, 600)
        self._scanning = False

        # 外层容器（用于圆角 + 阴影）
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        self.container = QFrame()
        self.container.setObjectName("container")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 90))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        outer.addWidget(self.container)

        body = QVBoxLayout(self.container)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body.addWidget(self._build_titlebar())
        body.addWidget(self._build_toolbar())
        body.addWidget(self._build_table(), 1)
        body.addWidget(self._build_statusbar())

        self._apply_style()

        # 自动刷新定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(5000)
        QTimer.singleShot(200, self.refresh)

    # ---------------------------------------------------------- 标题栏 ----
    def _build_titlebar(self):
        bar = QFrame()
        bar.setObjectName("titlebar")
        bar.setFixedHeight(52)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 12, 0)
        h.setSpacing(8)

        logo = QLabel("🛡")
        logo.setStyleSheet("font-size:20px;")
        title = QLabel(APP_NAME)
        title.setObjectName("apptitle")
        h.addWidget(logo)
        h.addWidget(title)
        h.addStretch()

        # 赞助
        self.btn_sponsor = QPushButton("❤ 赞助")
        self.btn_sponsor.setObjectName("sponsor")
        self.btn_sponsor.setCursor(Qt.PointingHandCursor)
        self.btn_sponsor.setFixedHeight(30)
        self.btn_sponsor.clicked.connect(self.open_sponsor)
        h.addWidget(self.btn_sponsor)

        # GitHub / 获取最新版
        self.btn_github = QPushButton("项目地址")
        self.btn_github.setObjectName("github")
        self.btn_github.setCursor(Qt.PointingHandCursor)
        self.btn_github.setFixedHeight(30)
        self.btn_github.setToolTip(GITHUB_URL)
        self.btn_github.clicked.connect(lambda: webbrowser.open(GITHUB_URL))
        h.addWidget(self.btn_github)

        h.addSpacing(6)

        # 窗口控制
        self.btn_min = make_tool_button("—", "最小化")
        self.btn_max = make_tool_button("☐", "最大化 / 还原")
        self.btn_close = make_tool_button("✕", "关闭")
        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.setObjectName("winbtn")
        self.btn_close.setObjectName("winclose")
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self.toggle_max)
        self.btn_close.clicked.connect(self.close)
        h.addWidget(self.btn_min)
        h.addWidget(self.btn_max)
        h.addWidget(self.btn_close)

        self._titlebar = bar
        return bar

    def _build_toolbar(self):
        bar = QFrame()
        bar.setObjectName("toolbar")
        bar.setFixedHeight(52)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 8, 16, 8)
        h.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 搜索应用名 / 端口 / 进程号")
        self.search.setFixedHeight(34)
        self.search.textChanged.connect(self._apply_filter)
        h.addWidget(self.search, 1)

        self.btn_refresh = QPushButton("⟳ 刷新")
        self.btn_refresh.setObjectName("primary")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.clicked.connect(self.refresh)
        h.addWidget(self.btn_refresh)
        return bar

    def _build_table(self):
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.verticalHeader().setDefaultSectionSize(46)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, len(self.COLS)):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 100)
        hh.setHighlightSections(False)
        return self.table

    def _build_statusbar(self):
        bar = QFrame()
        bar.setObjectName("statusbar")
        bar.setFixedHeight(34)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 16, 0)
        self.status = QLabel("准备就绪")
        self.status.setObjectName("statuslabel")
        h.addWidget(self.status)
        h.addStretch()
        ver = QLabel(f"© 2026 rgh  ·  v{APP_VERSION}  ·  每 5 秒自动刷新")
        ver.setObjectName("statuslabel")
        h.addWidget(ver)
        return bar

    # ---------------------------------------------------------- 数据 ----
    def refresh(self):
        if self._scanning:
            return
        self._scanning = True
        self.btn_refresh.setEnabled(False)
        self.status.setText("正在扫描端口占用…")
        self._thread = ScanThread()
        self._thread.result.connect(self._on_result)
        self._thread.start()

    def _on_result(self, rows):
        self._rows = rows
        self.table.setRowCount(0)
        for r in rows:
            self._add_row(r)
        self._apply_filter(self.search.text())
        self._scanning = False
        self.btn_refresh.setEnabled(True)
        self.status.setText(f"共发现 {len(rows)} 个端口占用")

    def _add_row(self, r):
        row = self.table.rowCount()
        self.table.insertRow(row)

        def cell(text, align=Qt.AlignVCenter | Qt.AlignLeft, color=None):
            it = QTableWidgetItem(str(text))
            it.setTextAlignment(align)
            if color:
                it.setForeground(QColor(color))
            return it

        self.table.setItem(row, 0, cell("  " + r["name"]))
        self.table.setItem(row, 1, cell(r["pid"], Qt.AlignCenter))

        port_item = cell(r["port"], Qt.AlignCenter, "#1677FF")
        f = port_item.font()
        f.setBold(True)
        port_item.setFont(f)
        self.table.setItem(row, 2, port_item)

        self.table.setItem(row, 3, cell(f"{r['cpu']:.1f}", Qt.AlignCenter,
                                        self._heat(r["cpu"], 50)))
        self.table.setItem(row, 4, cell(f"{r['mem']:.1f}", Qt.AlignCenter,
                                        self._heat(r["mem"], 20)))

        # 操作：停止按钮
        btn = QPushButton("停止")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("killbtn")
        btn.setFixedSize(72, 30)
        btn.clicked.connect(lambda _=False, pid=r["pid"], name=r["name"]:
                            self.kill_process(pid, name))
        wrap = QWidget()
        wl = QHBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setAlignment(Qt.AlignCenter)
        wl.addWidget(btn)
        self.table.setCellWidget(row, 5, wrap)

    @staticmethod
    def _heat(value, threshold):
        if value >= threshold:
            return "#E5484D"
        if value >= threshold / 2:
            return "#F5A623"
        return "#555555"

    def _apply_filter(self, text):
        text = (text or "").strip().lower()
        for row in range(self.table.rowCount()):
            if not text:
                self.table.setRowHidden(row, False)
                continue
            hay = " ".join(
                self.table.item(row, c).text().lower()
                for c in range(5) if self.table.item(row, c)
            )
            self.table.setRowHidden(row, text not in hay)

    def kill_process(self, pid, name):
        ret = QMessageBox.question(
            self, "确认停止",
            f"确定要停止进程吗？\n\n应用名：{name}\n进程号：{pid}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            QMessageBox.warning(
                self, "权限不足",
                f"无法停止进程 {pid}（{name}）。\n"
                f"该进程可能属于其他用户或系统进程，请用管理员/ sudo 运行本工具。",
            )
            return
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "停止失败", f"停止进程时出错：\n{e}")
            return
        # 移除该 pid 对应的所有行
        self._remove_rows_by_pid(pid)
        self.status.setText(f"已停止进程 {pid}（{name}）")

    def _remove_rows_by_pid(self, pid):
        for row in reversed(range(self.table.rowCount())):
            item = self.table.item(row, 1)
            if item and item.text() == str(pid):
                self.table.removeRow(row)

    def open_sponsor(self):
        dlg = SponsorDialog(self)
        # 居中于主窗口
        geo = self.geometry()
        dlg.move(geo.center() - QPoint(dlg.width() // 2, dlg.height() // 2))
        dlg.exec()

    # ------------------------------------------------- 窗口拖动 / 最大化 ----
    def toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._on_titlebar(e):
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and hasattr(self, "_drag") and self._drag:
            if self.isMaximized():
                self.showNormal()
            self.move(e.globalPosition().toPoint() - self._drag)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        if self._on_titlebar(e):
            self.toggle_max()

    def _on_titlebar(self, e):
        pos = e.position().toPoint()
        # 标题栏区域（考虑外层 margin 14 + 标题栏高度 52）
        return 14 <= pos.y() <= 14 + 52 and pos.x() >= 14

    # ---------------------------------------------------------- 样式 ----
    def _apply_style(self):
        self.setStyleSheet("""
            #container {
                background: #f5f6f8;
                border-radius: 14px;
            }
            #titlebar {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #4b6cb7, stop:1 #182848);
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }
            #apptitle { color: #ffffff; font-size: 15px; font-weight: bold; }
            #sponsor {
                color: #fff; background: rgba(255,255,255,0.15);
                border: none; border-radius: 15px; padding: 0 14px; font-size: 13px;
            }
            #sponsor:hover { background: #ff5a7a; }
            #github {
                color: #fff; background: rgba(255,255,255,0.15);
                border: none; border-radius: 15px; padding: 0 14px; font-size: 13px;
            }
            #github:hover { background: rgba(255,255,255,0.32); }
            #winbtn {
                color: #eaeaea; background: transparent;
                border: none; border-radius: 6px; font-size: 14px;
            }
            #winbtn:hover { background: rgba(255,255,255,0.22); }
            #winclose {
                color: #eaeaea; background: transparent;
                border: none; border-radius: 6px; font-size: 14px;
            }
            #winclose:hover { background: #e5484d; color: #fff; }

            #toolbar { background: #f5f6f8; }
            QLineEdit {
                background: #ffffff; border: 1px solid #e2e4e8;
                border-radius: 17px; padding: 0 16px; font-size: 13px; color:#333;
            }
            QLineEdit:focus { border: 1px solid #4b6cb7; }
            #primary {
                color: #fff; background: #4b6cb7; border: none;
                border-radius: 17px; padding: 0 20px; font-size: 13px; font-weight: bold;
            }
            #primary:hover { background: #3a559c; }
            #primary:disabled { background: #a9b6d6; }

            QTableWidget {
                background: #ffffff; border: none; margin: 0 14px;
                border-radius: 10px; gridline-color: transparent;
                font-size: 13px; color: #333;
            }
            QTableWidget::item {
                border-bottom: 1px solid #f0f1f3; padding: 0 6px;
            }
            QHeaderView::section {
                background: #ffffff; color: #8a8f99; border: none;
                border-bottom: 2px solid #eef0f3; padding: 10px 6px;
                font-weight: bold; font-size: 12px;
            }
            #killbtn {
                color: #E5484D; background: #fdecec; border: none;
                border-radius: 15px; font-size: 12px; font-weight: bold;
            }
            #killbtn:hover { background: #E5484D; color: #fff; }

            #statusbar {
                background: #f5f6f8;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }
            #statuslabel { color: #9aa0aa; font-size: 12px; }

            QScrollBar:vertical {
                background: transparent; width: 8px; margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: #cfd3da; border-radius: 4px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #b0b6c0; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
        """)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = PortMonitor()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
