import cv2
import time
import numpy as np

def test_resize_time(image_path, new_size=(320, 320), iterations=1000):
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"无法读取图片: {image_path}")
        return

    # 预热一次，避免第一次调用开销影响测试
    _ = cv2.resize(img, new_size)

    start_time = time.time()
    for _ in range(iterations):
        resized_img = cv2.resize(img, new_size)
    end_time = time.time()

    avg_time_ms = (end_time - start_time) / iterations * 1000
    print(f"resize {iterations} 次，平均耗时: {avg_time_ms:.4f} ms")

if __name__ == "__main__":
    # 这里替换成你本地测试用的图片路径
    test_resize_time("test.jpg")

