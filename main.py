import time
import cv2
import numpy as np
from ultralytics import YOLO
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QPushButton, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap
from typing import Optional

# 모듈 선택을 위한 전역 변수
selected_module = None

# 설정 상수
CONF_THRESHOLD = 0.3
DIST_THRESHOLD = 1200  # cm
FOCAL_LENGTH = 400
RESIZE_WIDTH = 1280
RESIZE_HEIGHT = 720

KNOWN_HEIGHTS = {
    0: 160,  # 사람
    2: 150,  # 자동차
    3: 100,  # 오토바이
    5: 350,  # 버스
    7: 350   # 트럭
}
CLASS_COLORS = {2: (0, 255, 0), 5: (255, 255, 0), 7: (255, 0, 255)}
VALID_CLASS_IDS = list(KNOWN_HEIGHTS.keys())

# YOLO 모델 로드
model = YOLO(r"/Users/seongbaepark/Desktop/workspace/privateWorkspace/python/telosGithub/lanedetection_final/best.pt")

# 경고 배너 이미지 불러오기
warning_banner = cv2.imread("warning_banner.png", cv2.IMREAD_UNCHANGED)
if warning_banner is not None:
    warning_banner = cv2.resize(warning_banner, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

def draw_text_with_background(img, text, org, font, scale, color, thickness):
    (tw, th), base = cv2.getTextSize(text, font, scale, thickness)
    x, y = org
    cv2.rectangle(img, (x, y - th - base), (x + tw + 4, y + base), (0, 0, 0), -1)
    cv2.putText(img, text, org, font, scale, color, thickness)

def overlay_warning_banner(frame, banner_img, x, y):
    bh, bw = banner_img.shape[:2]
    fh, fw = frame.shape[:2]
    if x >= fw or x + bw <= 0 or y >= fh or y + bh <= 0:
        return
    x1_frame = max(x, 0)
    y1_frame = max(y, 0)
    x1_banner = max(0, -x)
    y1_banner = max(0, -y)
    x2_frame = min(fw, x + bw)
    y2_frame = min(fh, y + bh)
    x2_banner = x2_frame - x
    y2_banner = y2_frame - y
    if banner_img.shape[2] == 4:
        alpha = banner_img[y1_banner:y2_banner, x1_banner:x2_banner, 3] / 255.0
        for c in range(3):
            frame[y1_frame:y2_frame, x1_frame:x2_frame, c] = (
                frame[y1_frame:y2_frame, x1_frame:x2_frame, c] * (1 - alpha) + 
                banner_img[y1_banner:y2_banner, x1_banner:x2_banner, c] * alpha
            ).astype(np.uint8)
    else:
        frame[y1_frame:y2_frame, x1_frame:x2_frame] = banner_img[y1_banner:y2_banner, x1_banner:x2_banner]

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    finished_signal = pyqtSignal()

    def __init__(self, module_name: str, video_path: str):
        super().__init__()
        self.module_name = module_name
        self.video_path = video_path
        self.running = True

    def run(self):
        # 선택된 모듈 동적 로드
        if self.module_name == "line_check":
            import line_check
            line_check_module = line_check
        elif self.module_name == "line_check_sobel":
            import line_check_sobel
            line_check_module = line_check_sobel
        else:
            print(f"Unknown module: {self.module_name}")
            return

        # 모듈에서 필요한 함수들 가져오기
        LaneTracker = line_check_module.LaneTracker
        line_check_func = line_check_module.line_check
        src = line_check_module.src
        dst = line_check_module.dst

        # 비디오 캡처 및 출력 설정
        cap = cv2.VideoCapture(self.video_path)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # 출력 비디오 크기 설정
        # out = cv2.VideoWriter("output.avi", fourcc, 30, (RESIZE_WIDTH, RESIZE_HEIGHT))
        out = cv2.VideoWriter("output.mp4", fourcc, 30, (RESIZE_WIDTH, RESIZE_HEIGHT))

        # 차선 정보 클래스 선언
        LT = LaneTracker(nwindows=9, margin=200, minimum=30)

        # 메인 루프
        warning_counter = 3
        frame_idx = 0

        while cap.isOpened() and self.running:
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (RESIZE_WIDTH, RESIZE_HEIGHT))

            # 차선 곡선 검출 및 시각화
            lane_vis = line_check_func(frame, src, dst, LT)
            result_frame = lane_vis.copy()

            # YOLO 객체 검출
            results = model(frame, conf=CONF_THRESHOLD, iou=0.5)
            collision_warning = False

            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf.item())
                class_id = int(box.cls.item())
                pixel_height = y2 - y1
                if class_id in VALID_CLASS_IDS and conf > CONF_THRESHOLD and pixel_height > 20:
                    known_height = KNOWN_HEIGHTS.get(class_id, 170)
                    distance_cm = (known_height * FOCAL_LENGTH) / pixel_height
                    distance_m = distance_cm / 100
                    if distance_cm < DIST_THRESHOLD:
                        collision_warning = True
                        box_color = (0, 0, 255)
                        thickness = 3
                    else:
                        box_color = CLASS_COLORS.get(class_id, (255, 255, 255))
                        thickness = 2
                    cv2.rectangle(result_frame, (x1, y1), (x2, y2), box_color, thickness)
                    dist_label = f"{distance_m:.1f}m"
                    class_label = str(class_id)  # 간단한 클래스 ID 사용
                    draw_text_with_background(result_frame, dist_label, (x1, y2 + 25),
                                             cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    cv2.circle(result_frame, (int((x1 + x2) / 2), int(y2)), 5, (255, 0, 0), -1)

            warning_counter = min(warning_counter + 5, 30) if collision_warning else max(warning_counter - 1, 0)
            if warning_counter > 0 and warning_banner is not None:
                banner_width = warning_banner.shape[1]
                x_pos = int((RESIZE_WIDTH - banner_width) / 2)
                y_pos = -90
                overlay_warning_banner(result_frame, warning_banner, x_pos, y_pos)

            fps = 1.0 / (time.time() - start_time)
            cv2.putText(result_frame, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            out.write(result_frame)
            self.change_pixmap_signal.emit(result_frame)

            frame_idx += 1

        cap.release()
        out.release()
        self.finished_signal.emit()

    def stop(self):
        self.running = False

# 프로그램 시작 
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread: Optional[VideoThread] = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("YOLO, OPEN CV를 활용한 차선감지")
        self.setGeometry(100, 100, 1400, 800)

        # 메인 위젯과 레이아웃
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 컨트롤 패널
        control_layout = QHBoxLayout()
        
        # 모듈 선택 콤보박스
        self.module_combo = QComboBox()
        self.module_combo.addItems(["line_check", "line_check_sobel"])
        self.module_combo.setCurrentText("line_check")
        control_layout.addWidget(QLabel("Module:"))
        control_layout.addWidget(self.module_combo)

        # 비디오 선택 콤보박스
        self.video_combo = QComboBox()
        self.video_combo.addItems(["/Users/seongbaepark/Desktop/workspace/privateWorkspace/python/lanedetection_final/project_video.mp4", 
                                   "/Users/seongbaepark/Desktop/workspace/privateWorkspace/python/lanedetection_final/challenge_video.mp4", 
                                   "/Users/seongbaepark/Desktop/workspace/privateWorkspace/python/lanedetection_final/harder_challenge_video.mp4"])
        self.video_combo.setCurrentText("/Users/seongbaepark/Desktop/workspace/privateWorkspace/python/lanedetection_final/harder_challenge_video.mp4")
        control_layout.addWidget(QLabel("Video:"))
        control_layout.addWidget(self.video_combo)

        # 시작 버튼
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_video)
        control_layout.addWidget(self.start_button)

        # 중지 버튼
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_video)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)

        layout.addLayout(control_layout)

        # 비디오 표시 라벨
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(1280, 720)
        self.video_label.setStyleSheet("border: 2px solid black;")
        layout.addWidget(self.video_label)

    # 비디오 시작 
    def start_video(self):
        # 스레드가 실행중이 아니거나,  None인 경우에만 새 스레드를 시작
        if self.thread is None or not self.thread.running:
            module_name = self.module_combo.currentText()
            video_path = self.video_combo.currentText()
            
            self.thread = VideoThread(module_name, video_path)
            self.thread.change_pixmap_signal.connect(self.update_image)
            self.thread.finished_signal.connect(self.video_finished)
            self.thread.start()
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.module_combo.setEnabled(False)
            self.video_combo.setEnabled(False)


    # 비디오 중지 
    def stop_video(self):
        print(r"self.thread:", self.thread)
        # 스레드가 실행중인 경우에만 중지
        if self.thread and self.thread.running:
            print(r"동작 테스트:")
            self.thread.stop()
            self.thread.wait()
            
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.module_combo.setEnabled(True)
            self.video_combo.setEnabled(True)

    # 비디오가 끝났을 때 호출되는 메소드
    def video_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.module_combo.setEnabled(True)
        self.video_combo.setEnabled(True)

    # OpenCV 이미지를 PyQt 라벨에 표시하는 메소드
    def update_image(self, cv_img):
        """OpenCV 이미지를 PyQt 라벨에 표시"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_qt_format.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
        self.video_label.setPixmap(QPixmap.fromImage(p))

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
