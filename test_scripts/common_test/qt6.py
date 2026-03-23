import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout

def main():
    app = QApplication(sys.argv)

    # 创建窗口
    window = QWidget()
    window.setWindowTitle("PyQt6 简单窗口")
    window.resize(300, 150)

    # 添加一个标签
    label = QLabel("你好，PyQt6！", parent=window)

    # 使用垂直布局
    layout = QVBoxLayout()
    layout.addWidget(label)
    window.setLayout(layout)

    # 显示窗口
    window.show()

    # 启动事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
