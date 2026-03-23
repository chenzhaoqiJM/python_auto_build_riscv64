import cv2

# 打开摄像头，0 是默认设备编号，如有多个摄像头可改为 1、2 等
cap = cv2.VideoCapture('/dev/video1')

# 检查是否成功打开
if not cap.isOpened():
    print("无法打开摄像头")
    exit()

while True:
    # 读取一帧图像
    ret, frame = cap.read()
    if not ret:
        print("无法接收图像，退出...")
        break

    # 显示图像
    cv2.imshow('USB Camera', frame)

    # 按下 'q' 键退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 释放资源
cap.release()
cv2.destroyAllWindows()
