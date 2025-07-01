# Lane Detection with YOLO Object Detection

이 프로젝트는 차선 검출과 YOLO 객체 검출을 결합한 자동차 안전 시스템입니다. PyQt5를 사용한 GUI 인터페이스를 통해 두 가지 다른 차선 검출 모듈을 선택하여 사용할 수 있습니다.

## 기능

- **차선 검출**: 두 가지 다른 알고리즘 선택 가능
  - `line_check.py`: 기본 차선 검출 알고리즘
  - `line_check_sobel.py`: Sobel 필터를 사용한 개선된 차선 검출 알고리즘
- **YOLO 객체 검출**: 차량, 사람, 버스, 트럭 등 검출
- **거리 측정**: 검출된 객체까지의 거리 계산
- **충돌 경고**: 가까운 객체에 대한 경고 시스템
- **PyQt5 GUI**: 사용자 친화적인 인터페이스

## 설치

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. YOLO 모델 파일 준비:
   - `C:\Users\USER\Downloads\notyet\best.pt` 경로에 YOLO 모델 파일이 있어야 합니다.
   - 또는 `main_simple.py`에서 모델 경로를 수정하세요.

## 사용법

### 테스트 버전 실행 (권장)
```bash
python test_gui.py
```
- YOLO 모델 없이도 차선 검출 기능만 테스트 가능
- 더 안정적이고 빠른 실행

### GUI 버전 실행 (YOLO 포함)
```bash
python main_simple.py
```

### GUI 기능

1. **Module 선택**: 
   - `line_check`: 기본 차선 검출 알고리즘
   - `line_check_sobel`: Sobel 필터 기반 차선 검출 알고리즘

2. **Video 선택**:
   - `project_video.mp4`
   - `challenge_video.mp4` 
   - `harder_challenge_video.mp4`

3. **Start/Stop 버튼**: 비디오 재생 시작/정지

### 콘솔 버전 실행
```bash
python main.py
```

## 파일 구조

```
lanedetection_final/
├── main.py                 # 원본 콘솔 버전
├── main_simple.py          # PyQt5 GUI 버전 (YOLO 포함)
├── test_gui.py             # 테스트 GUI 버전 (차선 검출만)
├── line_check.py           # 기본 차선 검출 모듈
├── line_check_sobel.py     # Sobel 필터 기반 차선 검출 모듈
├── requirements.txt        # 필요한 패키지 목록
├── README.md              # 이 파일
├── project_video.mp4      # 테스트 비디오
├── challenge_video.mp4    # 테스트 비디오
├── harder_challenge_video.mp4  # 테스트 비디오
├── warning_banner.png     # 경고 배너 이미지
└── output.avi            # 출력 비디오 (자동 생성)
```

## 주요 설정

`main_simple.py`에서 다음 상수들을 조정할 수 있습니다:

```python
CONF_THRESHOLD = 0.3        # YOLO 신뢰도 임계값
DIST_THRESHOLD = 1200       # 충돌 경고 거리 (cm)
FOCAL_LENGTH = 400          # 카메라 초점 거리
RESIZE_WIDTH = 1280         # 비디오 너비
RESIZE_HEIGHT = 720         # 비디오 높이
```

## 알고리즘 설명

### line_check.py
- HLS 색상 공간을 사용한 차선 검출
- CLAHE (Contrast Limited Adaptive Histogram Equalization) 적용
- 슬라이딩 윈도우 기반 차선 추적

### line_check_sobel.py  
- Sobel 필터를 사용한 엣지 검출
- 색상 임계값과 결합한 이진화
- 모폴로지 연산으로 노이즈 제거

## 출력

- 실시간 비디오 스트림에 차선과 객체 검출 결과 표시
- 검출된 객체에 대한 거리 정보 표시
- 충돌 위험이 있는 경우 경고 배너 표시
- FPS 정보 표시
- 결과를 `output.avi` 파일로 저장

## 문제 해결

### 1. PyQt5 설치 오류
```bash
pip install PyQt5
```

### 2. YOLO 모델 로딩 오류
PyTorch 2.6+ 버전에서 발생하는 보안 관련 오류입니다.

**해결 방법:**
- `test_gui.py`를 사용하여 차선 검출만 테스트
- 또는 기본 YOLO 모델 사용: `model = YOLO('yolov8n.pt')`

**오류 메시지 예시:**
```
_pickle.UnpicklingError: Weights only load failed...
```

### 3. 비디오 파일 없음
- 테스트 비디오 파일들이 프로젝트 폴더에 있는지 확인하세요.
- 비디오 파일 경로를 수정하세요.

### 4. 모듈 import 오류
- `line_check.py`와 `line_check_sobel.py` 파일이 같은 폴더에 있는지 확인하세요.

## 권장 사용 순서

1. **먼저 테스트**: `python test_gui.py`로 차선 검출 기능 테스트
2. **모듈 비교**: 두 모듈 간 성능 차이 확인
3. **YOLO 테스트**: `python main_simple.py`로 전체 기능 테스트

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 제작되었습니다. 