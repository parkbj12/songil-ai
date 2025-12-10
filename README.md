# 웨어러블 라이프로그 기반 개인 맞춤형 이상행동 탐지 및 챗봇 연계 건강관리 시스템

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2+-orange.svg)](https://pytorch.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-brightgreen.svg)](https://www.mongodb.com/cloud/atlas)

## 📋 프로젝트 개요

본 시스템은 웨어러블 기기와 건강 앱에서 수집한 건강 데이터를 기반으로 **LSTM Autoencoder 모델을 활용한 실시간 건강 이상 감지 서비스**를 제공합니다. 특히 홀로 사는 분들의 건강 상태를 지속적으로 모니터링하여 이상 징후를 조기 발견하고, 챗봇을 통해 친절한 건강 관리 피드백을 제공합니다.

### 주요 목적
- 📊 **건강 데이터 수집**: 아이폰 HealthKit, 웨어러블 기기, 수동 입력을 통한 건강 데이터 수집
- 🤖 **LSTM 기반 실시간 이상 감지**: 딥러닝 모델을 활용한 개인 맞춤형 건강 패턴 분석
- 🏠 **고독사 예방**: 홀로 사는 분들의 건강 상태를 지속적으로 모니터링하여 이상 징후 조기 발견
- 💬 **AI 챗봇 피드백**: OpenAI GPT를 활용한 건강 상태에 대한 이해하기 쉬운 설명과 실용적인 조언 제공
- 📧 **자동 알림 시스템**: 이상 패턴 감지 시 이메일 알림 및 긴급 연락망 활용

AI Hub의 '치매 고위험군 웨어러블 라이프로그 데이터셋'을 활용하여 LSTM Autoencoder로 개인의 일상 패턴을 학습하고, 이상행동을 감지하여 챗봇을 통해 건강관리 피드백을 제공하는 시스템입니다.

## ✨ 주요 기능

### 1. 건강 데이터 수집 및 분석
- 📱 **HealthKit 연동**: 아이폰 건강 앱 데이터 자동 수집
- 📊 **다양한 데이터 소스 지원**: XML, JSON, CSV 파일 업로드
- ⌨️ **수동 입력**: 웹 인터페이스를 통한 직접 데이터 입력
- 📈 **실시간 이상 탐지**: LSTM Autoencoder 기반 실시간 건강 패턴 분석

### 2. 이상 탐지 시스템
- 🤖 **LSTM Autoencoder 모델**: 개인 맞춤형 건강 패턴 학습
- 📊 **Reconstruction Error 기반 탐지**: 재구성 오차를 통한 이상 징후 감지
- 🎯 **동적 임계값 설정**: Validation 데이터 기반 자동 임계값 계산
- 📉 **이상 점수 제공**: 0~1 범위의 정량적 이상 점수

### 3. AI 챗봇 시스템
- 💬 **OpenAI GPT 연동**: 자연어 기반 건강 상담
- 📝 **맞춤형 피드백**: 사용자 건강 데이터 기반 개인화된 조언
- 🔔 **알림 관리**: 건강 체크 알림 및 무응답 사용자 확인
- 📊 **통계 정보 제공**: 사용자별 건강 통계 및 이상 탐지 이력

### 4. 알림 및 모니터링 시스템
- 📧 **이메일 알림**: 이상 패턴 감지 시 자동 이메일 발송
- ⏰ **스케줄러**: 정기적인 건강 상태 체크 (30분마다)
- 🚨 **무응답 사용자 감지**: 5분 이상 무응답 시 긴급 알림
- 👨‍👩‍👧 **긴급 연락망**: 보호자/가족에게 자동 알림

### 5. 데이터 관리
- 💾 **MongoDB 저장**: 사용자별 건강 데이터 영구 저장
- 📊 **이력 조회**: 날짜별, 사용자별 데이터 조회
- 📈 **통계 분석**: 이상 탐지 빈도, 평균 점수 등 통계 제공
- 🗑️ **데이터 삭제**: 개인정보 보호를 위한 데이터 삭제 기능

## 🏗️ 프로젝트 구조

```
songil-ai-main/
├── app.py                 # Flask 메인 애플리케이션 (REST API)
├── config.py              # 설정 파일 (환경 변수, 하이퍼파라미터)
├── model.py               # LSTM Autoencoder 모델 정의
├── data_processor.py      # 데이터 처리 및 전처리
├── anomaly_detector.py    # 이상 탐지 로직
├── database.py            # MongoDB 연동 모듈
├── chatbot.py             # AI 챗봇 모듈 (OpenAI GPT)
├── notification.py        # 이메일 알림 시스템
├── scheduler.py           # 건강 상태 체크 스케줄러
├── requirements.txt       # 패키지 의존성
├── Procfile               # Railway/Heroku 배포 설정
├── sample_health_data.xml # 샘플 건강 데이터 파일
├── templates/             # HTML 템플릿
│   ├── index.html         # 메인 대시보드
│   ├── upload.html        # 파일 업로드 페이지
│   └── history.html       # 데이터 이력 페이지
├── static/                # 정적 파일
│   ├── css/
│   │   └── style.css      # 스타일시트
│   └── js/
│       ├── main.js        # 메인 JavaScript
│       ├── upload.js      # 업로드 기능
│       └── history.js     # 이력 조회 기능
└── models/                # 학습된 모델 파일
    ├── lstm_autoencoder.pth  # LSTM 모델 가중치
    └── scaler.pkl         # 데이터 정규화 스케일러
```

## 🚀 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/songil-ai.git
cd songil-ai-main
```

### 2. 가상환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 참고하여 설정하세요:

`.env` 파일 내용:
```env
# MongoDB 설정 (필수)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
# 또는 로컬 MongoDB: mongodb://localhost:27017/

# OpenAI API 설정 (선택사항 - 챗봇 기능 사용 시)
OPENAI_API_KEY=your_openai_api_key_here

# 이메일 알림 설정 (선택사항)
EMAIL_ENABLED=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

**⚠️ 중요**: `.env` 파일은 절대 GitHub에 올리지 마세요! (이미 `.gitignore`에 포함되어 있습니다)

### 5. 모델 파일 확인

`models/` 디렉토리에 다음 파일이 있는지 확인하세요:
- `lstm_autoencoder.pth`: 학습된 LSTM 모델
- `scaler.pkl`: 데이터 정규화 스케일러

모델 파일은 이미 학습되어 포함되어 있습니다.

### 6. 서버 실행

```bash
# 개발 모드
python app.py

# 프로덕션 모드 (Gunicorn 사용)
gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 120
```

### 7. 웹 브라우저 접속

http://localhost:5000

## 📖 사용 방법

### 1. 건강 데이터 입력

#### 방법 1: 직접 입력 (가장 추천! ⭐)
1. 웹 페이지에서 "건강 데이터 입력" 섹션으로 이동
2. 다음 정보 입력:
   - 심박수 (bpm)
   - 걸음수 (steps)
   - 수면 시간 (hours)
   - 체온 (°C)
   - 활동량 (kcal)
3. "이상 탐지 예측" 버튼 클릭
4. 자동으로 분석 및 챗봇 피드백 제공

#### 방법 2: 파일 업로드
1. 건강 앱에서 데이터 내보내기 → XML/JSON 파일 다운로드
2. 웹 페이지에서 "건강 데이터 파일 업로드" 섹션에 파일 업로드
3. 자동으로 분석됩니다!

**지원 파일 형식:**
- XML 파일 (HealthKit 내보내기)
- JSON 파일
- CSV 파일 (수동 정리)

#### 방법 3: HealthKit API 연동
- `/sync_healthkit` 엔드포인트를 통해 아이폰 HealthKit 데이터 자동 동기화

### 2. 모델 정보

모델은 이미 학습되어 `models/` 디렉토리에 저장되어 있습니다:
- `lstm_autoencoder.pth`: LSTM Autoencoder 모델 가중치
- `scaler.pkl`: 데이터 정규화 스케일러

### 3. 챗봇 사용

웹 인터페이스의 챗봇 섹션에서:
- 건강 상태 질문
- 이상 탐지 결과 설명 요청
- 건강 관리 조언 요청

## 🔌 API 엔드포인트

### 건강 데이터 관련
- `POST /predict` - 새 데이터 입력 시 이상 여부 예측
- `POST /upload_health_data` - 건강 데이터 파일 업로드 (JSON/CSV/XML)
- `POST /save_data` - MongoDB에 데이터 저장
- `POST /sync_healthkit` - HealthKit 데이터 동기화

### 사용자 데이터 조회
- `GET /get_user/<user_id>` - 특정 사용자 데이터 조회
- `GET /get_user_anomalies/<user_id>` - 사용자 이상 탐지 이력 조회
- `GET /get_statistics/<user_id>` - 사용자 통계 정보 조회
- `DELETE /delete_user_data/<document_id>` - 사용자 데이터 삭제

### 챗봇
- `POST /chat` - 챗봇 대화 API

### 알림 관리
- `GET /get_notifications/<user_id>` - 사용자 알림 목록 조회
- `POST /mark_notification_read/<notification_id>` - 알림 읽음 표시
- `POST /mark_notification_responded/<notification_id>` - 알림 응답 표시

### 사용자 설정
- `GET /get_user_email/<user_id>` - 사용자 이메일 조회
- `POST /update_user_email` - 사용자 이메일 업데이트
- `GET /get_emergency_contacts/<user_id>` - 긴급 연락망 조회
- `POST /update_emergency_contacts` - 긴급 연락망 업데이트
- `POST /send_emergency_alert` - 긴급 알림 발송

### 시스템
- `GET /health` - 서버 상태 확인
- `GET /` - 웹 대시보드
- `GET /upload` - 파일 업로드 페이지
- `GET /history` - 데이터 이력 페이지

## 💾 데이터베이스 구조

**DB 이름**: `wearable_ai`  
**컬렉션**: `sensor_logs`, `notifications`, `user_settings`

### sensor_logs 컬렉션
```json
{
  "_id": "ObjectId",
  "user_id": "user001",
  "date": "2025-12-04",
  "sensor_data": [
    {
      "time": "09:00",
      "heart_rate": 72,
      "steps": 120,
      "sleep_hours": 7.5,
      "temperature": 36.5,
      "activity": 150
    }
  ],
  "anomaly_score": 0.85,
  "anomaly_detected": true,
  "chatbot_feedback": "오늘 활동량이 평소보다 적어요...",
  "timestamp": "2025-12-04T09:00:00Z",
  "updated_at": "2025-12-04T09:00:00Z"
}
```

### notifications 컬렉션
```json
{
  "_id": "ObjectId",
  "user_id": "user001",
  "notification_type": "health_check",
  "message": "건강 상태를 확인해주세요.",
  "status": "pending",
  "created_at": "2025-12-04T09:00:00Z",
  "read_at": null,
  "responded_at": null
}
```

### user_settings 컬렉션
```json
{
  "_id": "ObjectId",
  "user_id": "user001",
  "email": "user@example.com",
  "emergency_contacts": [
    {
      "name": "보호자1",
      "email": "guardian1@example.com",
      "phone": "010-1234-5678"
    }
  ],
  "updated_at": "2025-12-04T09:00:00Z"
}
```

## 🚢 배포

### Railway/Heroku 배포

**간단한 배포 단계:**
1. Railway 또는 Heroku 계정 생성 및 프로젝트 생성
2. GitHub 저장소 연결
3. 환경 변수 설정 (MongoDB URI, OpenAI API Key 등)
4. `Procfile`이 이미 포함되어 있어 자동 배포 완료!

### 다른 플랫폼 배포

- **Heroku**: `Procfile` 사용
- **Docker**: Dockerfile 생성 필요

## 🔧 설정

### 모델 하이퍼파라미터 (`config.py`)

```python
MODEL_CONFIG = {
    "input_size": 5,            # 센서 데이터 특징 수 (heart_rate, steps, sleep, temperature, activity)
    "hidden_size": 64,          # LSTM hidden 크기
    "num_layers": 2,            # LSTM 레이어 수
    "dropout": 0.2,             # Dropout 비율
    "learning_rate": 0.001,     # 학습률
    "batch_size": 32,           # 배치 크기
    "epochs": 100,              # 에포크 수
    "sequence_length": 60,      # 시계열 윈도우 크기 (분)
}
```

### 이상 탐지 설정

```python
ANOMALY_CONFIG = {
    "threshold_multiplier": 1.0,  # 임계값 배수
    "min_threshold": 0.01,        # 최소 임계값
    "min_anomaly_score": 0.5,    # 최소 이상 점수
    "use_percentile": False,      # Percentile 사용 여부
    "percentile": 95,             # Percentile 값
}
```

## 🏥 고독사 예방 기능

### 지속적인 모니터링
- 24시간 건강 상태 자동 모니터링
- 30분마다 정기적인 건강 체크 알림
- 무응답 사용자 자동 감지 (5분 이상)

### 이상 패턴 조기 발견
- 활동량 급감 감지
- 비정상적인 심박수 패턴 탐지
- 수면 패턴 이상 감지
- 체온 이상 감지

### 자동 알림 시스템
- 이상 패턴 감지 시 즉시 알림
- 사용자 및 지정된 보호자에게 이메일 발송
- 챗봇을 통한 건강 상태 확인 요청

### 긴급 상황 대응
- 심각한 이상 패턴 감지 시 자동으로 긴급 연락망 활용
- 보호자/가족에게 자동 알림 발송
- 응급 상황 대응 프로토콜 실행

## 🤖 모델 정보

### LSTM Autoencoder 모델
- 사전 학습된 LSTM Autoencoder 모델이 `models/` 디렉토리에 포함되어 있습니다.
- 모델은 AI Hub의 '치매 고위험군 웨어러블 라이프로그 데이터셋'을 기반으로 학습되었습니다.
- Reconstruction Error 기반으로 이상 징후를 감지합니다.

## 🐛 트러블슈팅

### MongoDB 연결 오류
- **SSL 핸드셰이크 실패**: 컨테이너 환경에서는 `tlsAllowInvalidCertificates=True` 설정이 자동 적용됩니다.
- **연결 타임아웃**: MongoDB Atlas의 Network Access에서 IP 주소를 허용했는지 확인하세요.
- **인증 실패**: MongoDB URI의 사용자명과 비밀번호가 올바른지 확인하세요. 특수문자는 URL 인코딩이 필요할 수 있습니다.

### 모델 로드 실패
- `models/` 디렉토리에 모델 파일(`lstm_autoencoder.pth`, `scaler.pkl`)이 있는지 확인하세요.
- 모델 파일은 저장소에 포함되어 있어야 합니다.

### OpenAI API 오류
- API 키가 올바른지 확인하세요.
- API 사용량 한도를 확인하세요.
- 챗봇 기능은 선택사항이므로, API 키가 없어도 다른 기능은 정상 작동합니다.

### 이메일 알림 실패
- Gmail 사용 시 앱 비밀번호를 사용해야 합니다.
- SMTP 서버 설정이 올바른지 확인하세요.
- `EMAIL_ENABLED=true`로 설정했는지 확인하세요.

## 📝 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 👥 기여

이슈 리포트와 풀 리퀘스트를 환영합니다!

## 📧 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해주세요.

---

