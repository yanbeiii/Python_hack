import sys
import json
import os
import ctypes
import win32gui
import win32con

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QTextEdit, QPushButton, QVBoxLayout,
    QGridLayout, QInputDialog, QMenu, QSystemTrayIcon, QStyle, QAction, QMainWindow
)
from PyQt5.QtGui import QPainter, QColor, QBrush
from PyQt5.QtCore import Qt


DATA_FILE = "tasks.json"


class TaskQuadrant(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("任务四象限")
        self.setGeometry(100, 100, 800, 600)

        # 无边框 + 背景透明 + 不显示任务栏图标
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.tasks = {
            "重要且紧急": [],
            "重要但不紧急": [],
            "不重要但紧急": [],
            "不重要不紧急": []
        }

        self.text_edits = {}
        self.init_ui()
        self.load_tasks()

        self.resize(800, 600)
        self.move_to_bottom_right()
        #self.set_to_desktop()  # 关键：置于桌面最底层，确保显示正常


        self.init_tray_icon()

    def init_ui(self):
        central_widget = QWidget()
        layout = QGridLayout()
        quadrant_names = list(self.tasks.keys())

        for i in range(2):
            for j in range(2):
                name = quadrant_names[i * 2 + j]

                sub_layout = QVBoxLayout()
                label = QLabel(name)
                label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")

                text_edit = QTextEdit()
                text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
                text_edit.customContextMenuRequested.connect(lambda pos, n=name: self.show_task_menu(n, pos))
                text_edit.setStyleSheet("""
                    background-color: rgba(255, 255, 255, 40);
                    border-radius: 6px;
                """)

                btn = QPushButton("添加任务")
                btn.setStyleSheet("background-color: #4CAF50; color: white;")
                btn.clicked.connect(lambda _, n=name: self.add_task(n))

                sub_layout.addWidget(label)
                sub_layout.addWidget(text_edit)
                sub_layout.addWidget(btn)

                layout.addLayout(sub_layout, i, j)
                self.text_edits[name] = text_edit

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def add_task(self, name):
        task, ok = QInputDialog.getText(self, "添加任务", f"添加到「{name}」的任务：")
        if ok and task:
            self.tasks[name].append(task)
            self.refresh(name)
            self.save_tasks()

    def show_task_menu(self, quadrant, pos):
        cursor = self.text_edits[quadrant].cursorForPosition(pos)
        cursor.select(cursor.LineUnderCursor)
        selected_text = cursor.selectedText()

        if not selected_text.strip():
            return

        menu = QMenu()
        edit_action = menu.addAction("编辑任务")
        delete_action = menu.addAction("删除任务")

        action = menu.exec_(self.mapToGlobal(pos))

        if action == edit_action:
            new_text, ok = QInputDialog.getText(self, "编辑任务", "修改任务：", text=selected_text)
            if ok and new_text:
                idx = self.tasks[quadrant].index(selected_text)
                self.tasks[quadrant][idx] = new_text
        elif action == delete_action:
            self.tasks[quadrant].remove(selected_text)

        self.refresh(quadrant)
        self.save_tasks()

    def refresh(self, name):
        self.text_edits[name].clear()
        for task in self.tasks[name]:
            self.text_edits[name].append(f"{task}")

    def save_tasks(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    def load_tasks(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
            for name in self.tasks:
                self.refresh(name)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(30, 30, 30, 80)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # 禁止拖动，覆盖事件让窗口固定
    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def moveEvent(self, event):
        self.move_to_bottom_right()

    def set_to_desktop(self):
        hwnd = int(self.winId())
        progman = win32gui.FindWindow("Progman", None)

        # 发送消息，创建 WorkerW 窗口
        win32gui.SendMessageTimeout(progman,
            0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)

        workerw = None

        def enum_windows(hwnd_enum, param):
            nonlocal workerw
            if win32gui.GetClassName(hwnd_enum) == "WorkerW":
                if win32gui.FindWindowEx(hwnd_enum, 0, "SHELLDLL_DefView", None) is None:
                    workerw = hwnd_enum
            return True

        win32gui.EnumWindows(enum_windows, None)

        if workerw:
            win32gui.SetParent(hwnd, workerw)
        else:
            win32gui.SetParent(hwnd, progman)

        win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

        self.show()
        self.raise_()
        self.activateWindow()

    def init_tray_icon(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray.setToolTip("任务四象限")

        menu = QMenu()
        restore_action = QAction("显示")
        quit_action = QAction("退出")

        restore_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.close)

        menu.addAction(restore_action)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def closeEvent(self, event):
        self.tray.hide()
        event.accept()

    def hideEvent(self, event):
        if self.isMinimized():
            self.hide()
            event.ignore()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()
            self.move_to_bottom_right()

    def move_to_bottom_right(self, margin_right=20, margin_bottom=40):
        screen_rect = QApplication.primaryScreen().availableGeometry()
        x = screen_rect.right() - self.width() - margin_right
        y = screen_rect.bottom() - self.height() - margin_bottom
        self.move(x, y)


if __name__ == "__main__":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("quadrant.task.manager")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = TaskQuadrant()
    window.show()
    sys.exit(app.exec_())
