import socket
import json
import os
import configparser
import time
import threading

from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List




class SocketClient():

    
    def __init__(self):
        # 현재 파일의 부모 디렉토리 경로를 가져옴
        current_dir = Path(__file__).parent.parent
        config = configparser.ConfigParser()
        # 부모 디렉토리의 resource 폴더 경로를 설정
        resource_path = current_dir / "resource"

        # resource 폴더 내의 serverinfo.ini 파일을 읽어옴
        config.read(resource_path/"serverinfo.ini")

        # ip, port 정보 읽어오기 
        self.SERVER_IP = config['SERVER']['ip']
        self.PORT = config['SERVER']['port']
        self.VIDEO_PORT  = config['SERVER']['video_port']

        self.chunk_size = 4096

        print(f"Connecting to server at {self.SERVER_IP}:{int(self.PORT)}") 

        # 소켓 초기화
        self.sock = None
        # 스레드 관련 변수
        self.running = False
        # 스레드 객체
        self.thread = None

        # 데이터 전송을 위한 락
        self.data_lock = threading.Lock()
        # 현재 전송할 데이터
        self.current_data = None


    # 소켓 연결 함수
    def socket_connet(self, isVideoSocket=False):
        # 소켓연결 로직을 두개로 분기. 
        # isVideoSocket이 True면 비디오 서버로 연결
        # False면 일반 서버로 연결
        if isVideoSocket: 
            print(f"[SocketClient] Connecting to video server at {self.SERVER_IP}:{int(self.VIDEO_PORT)}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.SERVER_IP, int(self.VIDEO_PORT)))    
        else:
            print(f"[SocketClient] Connecting to normal {self.SERVER_IP}:{int(self.PORT)}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.SERVER_IP, int(self.PORT)))

    # 소켓 스레드 시작 함수
    def start(self, isVideoSocket=False):
        self.running = True
        # 데이터 전송 방식 분기 
        # isVideoSocket이 True면 비디오 전송 스레드 시작
        # False면 일반 데이터 전송 스레드 시작
        if isVideoSocket:
            self.thread = threading.Thread(target=self._send_video_loop, daemon=True)
        else:
            self.thread = threading.Thread(target=self._send_loop, daemon=True)
        self.thread.start()


    # 데이터 설정 함수
    # 영상 스레드에서 호출하여 데이터를 설정
    def set_data(self, label, distance, frame_no):
        """영상 스레드에서 호출할 데이터 설정 함수"""
        with self.data_lock:

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


            print("[Log] ", timestamp, label, distance, frame_no)

            log_data = TCPSendData(
                timestamp=timestamp,
                label=label,
                distance=distance,
                frame=frame_no
            )

            self.current_data = log_data

    # 데이터가 설정되면 스레드가 데이터를 전송하도록 함
    def _send_loop(self):
        try:
            while self.running:
                with self.data_lock:
                    data_to_send = self.current_data

                if data_to_send:
                    try:
                        self.sock.sendall(data_to_send.encode())
                        response = self.sock.recv(1024).decode()
                        print(f"[SocketClient] Server response: {response}")
                    except Exception as e:
                        print(f"[SocketClient] Error: {e}")
                        self.running = False
                        break

                time.sleep(0.1)  # 전송 간격
        finally:
            self._cleanup()


    # 비디오 전송을 위한 스레드 함수
    # 비디오 파일을 서버로 전송하는 역할을 함
    def _send_video_loop(self):
        current_path = Path(__file__).parent.parent

        file_path =current_path/"output.mp4"  # 실제 파일 경로
        # 파일명과 파일 크기를 먼저 보냄
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)
        header = f"{filename}:{filesize}".encode().ljust(256, b' ')  # 고정 길이 header
        self.sock.sendall(header)
        print("[Client] Sending video file:", filename)

        # 파일 전송
        with open(file_path, "rb") as f:
            # 동영상 파일 전달을 중간에 끊을 필요가 없으므로 별도의 스레드 플래그를 삽입하지 않음. 
            while True:            
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                self.sock.sendall(chunk)
        print("[Client] Video file transfer completed.")
        self._cleanup()

            

    # 소켓 연결 종료 함수
    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        self._cleanup()
        print("[SocketClient] Stopped")


    # 소켓 자원 정리 함수
    def _cleanup(self):
        print("[SocketClient] Cleaning up resources")
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None




## 데이터 전송을 위한 클래스
@dataclass
class TCPSendData:
    timestamp: float
    label: str
    distance: float
    frame: int


    # 속성들을 JSON 문자열로 변환하고 bytes로 인코딩하는 메서드
    def encode(self) -> bytes:
        """
        객체를 JSON 문자열로 변환 후 bytes로 인코딩
        """
        data_dict = {
            "timestamp": self.timestamp,
            "label": self.label,
            "distance": self.distance,
            "frame": self.frame
        }
        json_str = json.dumps(data_dict)
        return json_str.encode()
    