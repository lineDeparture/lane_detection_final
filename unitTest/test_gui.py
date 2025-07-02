import time
import cv2
import numpy as np
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QComboBox, QPushButton, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap

# 설정 상수
RESIZE_WIDTH = 1280
RESIZE_HEIGHT = 720

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    finished_signal = pyqtSignal()

    def __init__(self, module_name, video_path):
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

        # 비디오 캡처
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print(f"비디오 파일을 열 수 없습니다: {self.video_path}")
            return

        # 차선 정보 클래스 선언
        LT = LaneTracker(nwindows=9, margin=200, minimum=30)

        while cap.isOpened() and self.running:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame = cv2.resize(frame, (RESIZE_WIDTH, RESIZE_HEIGHT))

            try:
                # 차선 곡선 검출 및 시각화
                result_frame = line_check_func(frame, src, dst, LT)
                
                # FPS 표시
                cv2.putText(result_frame, f"Module: {self.module_name}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                
                self.change_pixmap_signal.emit(result_frame)
                
            except Exception as e:
                print(f"프레임 처리 오류: {e}")
                # 오류 발생 시 원본 프레임 표시
                cv2.putText(frame, f"Error: {e}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                self.change_pixmap_signal.emit(frame)

        cap.release()
        self.finished_signal.emit()

    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Lane Detection Test")
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
        self.video_combo.addItems(["project_video.mp4", "challenge_video.mp4", "harder_challenge_video.mp4"])
        self.video_combo.setCurrentText("harder_challenge_video.mp4")
        control_layout.addWidget(QLabel("Video:"))
        control_layout.addWidget(self.video_combo)

        # 시작/정지 버튼
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_video)
        control_layout.addWidget(self.start_button)

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

    def start_video(self):
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

    def stop_video(self):
        if self.thread and self.thread.running:
            self.thread.stop()
            self.thread.wait()
            
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.module_combo.setEnabled(True)
            self.video_combo.setEnabled(True)

    def video_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.module_combo.setEnabled(True)
        self.video_combo.setEnabled(True)

    def update_image(self, cv_img):
        """OpenCV 이미지를 PyQt 라벨에 표시"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_qt_format.scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)
        self.video_label.setPixmap(QPixmap.fromImage(p))

    def closeEvent(self, event):
        if self.thread and self.thread.running:
            self.thread.stop()
            self.thread.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 