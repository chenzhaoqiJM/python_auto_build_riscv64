import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

app = QApplication(sys.argv)

# 创建一个窗口
window = QWidget()
window.setWindowTitle('PyQt5 测试窗口')
window.setGeometry(100, 100, 280, 80)  # x, y, width, height

# 创建一个标签
label = QLabel('<h2>PyQt5 已成功运行！</h2>', parent=window)
label.move(60, 15)

window.show()

sys.exit(app.exec_())
