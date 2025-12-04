"""
설정 파일
환경 변수 및 하이퍼파라미터 관리
"""
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB 설정
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = "wearable_ai"
COLLECTION_NAME = "sensor_logs"

# OpenAI API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-3.5-turbo"

# 모델 하이퍼파라미터
MODEL_CONFIG = {
    "input_size": 23,  # 센서 데이터 특징 수 (자동으로 계산됨, train.py에서 업데이트)
    "hidden_size": 64,
    "num_layers": 2,
    "dropout": 0.2,
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100,
    "sequence_length": 60,  # 60분 단위 시계열 윈도우
}

# 데이터 전처리 설정
DATA_CONFIG = {
    "window_size": 60,  # 분 단위
    "test_size": 0.2,
    "validation_size": 0.1,
    "missing_value_strategy": "mean",  # "zero", "mean", "median"
}

# 이상 탐지 설정
ANOMALY_CONFIG = {
    "threshold_multiplier": 1.0,  # validation 평균 + (multiplier * 표준편차)
    "min_threshold": 0.01,  # 최소 임계값 (너무 낮은 임계값 방지)
    "min_anomaly_score": 0.5,  # 최소 이상 점수
    "use_percentile": False,  # True면 percentile 사용, False면 mean+std 사용
    "percentile": 95,  # percentile 사용 시 몇 퍼센트 사용
}

# Flask 설정
FLASK_CONFIG = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": True,
    "use_reloader": False,  # Windows에서 자동 리로더 비활성화 (오류 방지)
}

# 알림 시스템 설정
NOTIFICATION_CONFIG = {
    "email_enabled": os.getenv("EMAIL_ENABLED", "false").lower() == "true",
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "sender_email": os.getenv("SENDER_EMAIL", ""),
    "sender_password": os.getenv("SENDER_PASSWORD", ""),  # Gmail의 경우 앱 비밀번호 사용
    
    # 알림 레벨 (이상 점수 기준)
    "alert_levels": {
        "low": 1.0,        # 낮은 이상 점수
        "medium": 2.0,     # 중간 이상 점수
        "high": 5.0,       # 높은 이상 점수
        "critical": 10.0   # 심각한 이상 점수
    },
    
    # 사용자별 이메일 주소 (서버 실행 중에만 메모리에 저장, 재시작 시 초기화됨)
    "user_emails": {
        # 서버 재시작 시마다 비어있게 시작 (사용자가 직접 입력)
        # "user001": "user@example.com",
    },
    
    # 긴급 연락망 (사용자별 보호자/가족 연락처)
    "emergency_contacts": {
        # "user001": [
        #     {"name": "보호자1", "email": "guardian1@example.com", "phone": "010-1234-5678"},
        #     {"name": "보호자2", "email": "guardian2@example.com", "phone": "010-9876-5432"}
        # ],
    }
}

# 모델 파일 경로
MODEL_SAVE_PATH = "models/lstm_autoencoder.pth"
SCALER_SAVE_PATH = "models/scaler.pkl"

# 데이터 파일 경로
DATA_BASE_PATH = "128.치매 고위험군 라이프로그/01.데이터"
DATA_TRAIN_PATH = os.path.join(DATA_BASE_PATH, "1.Training/원천데이터")
DATA_VAL_PATH = os.path.join(DATA_BASE_PATH, "2.Validation/원천데이터")

# 개별 데이터 파일 경로
TRAIN_ACTIVITY_PATH = os.path.join(DATA_TRAIN_PATH, "1.걸음걸이/train_activity.csv")
TRAIN_SLEEP_PATH = os.path.join(DATA_TRAIN_PATH, "2.수면/train_sleep.csv")
TRAIN_MMSE_PATH = os.path.join(DATA_TRAIN_PATH, "3.인지기능/train_mmse.csv")

VAL_ACTIVITY_PATH = os.path.join(DATA_VAL_PATH, "1.걸음걸이/val_activity.csv")
VAL_SLEEP_PATH = os.path.join(DATA_VAL_PATH, "2.수면/val_sleep.csv")
VAL_MMSE_PATH = os.path.join(DATA_VAL_PATH, "3.인지기능/val_mmse.csv")

