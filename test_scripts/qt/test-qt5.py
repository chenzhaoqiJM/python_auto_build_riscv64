import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QListWidget, QSplitter, QAction, QToolBar
)
from PyQt5.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt5 界面测试 - 中等复杂度")
        self.resize(900, 600)

        # === 菜单栏 ===
        menu = self.menuBar()
        file_menu = menu.addMenu("文件")
        edit_menu = menu.addMenu("编辑")

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # === 工具栏 ===
        toolbar = QToolBar("工具栏")
        toolbar.addAction(exit_action)
        self.addToolBar(toolbar)

        # === 中心布局 ===
        splitter = QSplitter(Qt.Horizontal)  # 左右分栏
        self.setCentralWidget(splitter)

        # 左边：列表
        self.list_widget = QListWidget()
        self.list_widget.addItems(["用户管理", "订单管理", "数据分析"])
        splitter.addWidget(self.list_widget)

        # 右边：表单 + 表格
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # --- 表单区域 ---
        form_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入名字")

        self.role_combo = QComboBox()
        self.role_combo.addItems(["管理员", "用户", "访客"])

        add_button = QPushButton("添加")
        add_button.clicked.connect(self.add_entry)

        form_layout.addWidget(QLabel("姓名:"))
        form_layout.addWidget(self.name_input)
        form_layout.addWidget(QLabel("角色:"))
        form_layout.addWidget(self.role_combo)
        form_layout.addWidget(add_button)

        right_layout.addLayout(form_layout)

        # --- 表格区域 ---
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["姓名", "角色"])
        right_layout.addWidget(self.table)

        splitter.addWidget(right_widget)

    def add_entry(self):
        """点击按钮，向表格添加新行"""
        name = self.name_input.text().strip()
        role = self.role_combo.currentText()

        if not name:
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(role))

        # 清空输入框
        self.name_input.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
