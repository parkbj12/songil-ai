"""
Flask 메인 애플리케이션
REST API 및 웹 대시보드 제공

주요 목적:
- 아이폰 건강앱(HealthKit)과 연동하여 사용자 건강 데이터 실시간 수집
- LSTM Autoencoder 모델 기반 실시간 건강 이상 감지
- 홀로 사는 분들의 건강 상태 지속 모니터링 및 고독사 예방
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import xml.etree.ElementTree as ET
import torch
import numpy as np
import pandas as pd
from datetime import datetime
import os
import json
import socket
import config
from model import LSTMAutoencoder
from data_processor import DataProcessor
from anomaly_detector import AnomalyDetector
from database import MongoDBManager
from chatbot import HealthChatbot
from notification import NotificationManager
from scheduler import HealthCheckScheduler


app = Flask(__name__)
# CORS 설정 - 모든 도메인에서 접속 허용
CORS(app, resources={r"/*": {"origins": "*"}})

# 전역 변수
model = None
data_processor = None
anomaly_detector = None
db_manager = None
chatbot = None
notification_manager = None
health_scheduler = None


def convert_numpy_types(obj):
    """
    numpy 타입을 Python 기본 타입으로 변환 (JSON 직렬화를 위해)
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    return obj


def load_model():
    """모델 로드"""
    global model, data_processor, anomaly_detector
    
    # 현재 작업 디렉토리 확인
    current_dir = os.getcwd()
    print(f"현재 작업 디렉토리: {current_dir}")
    print(f"모델 파일 경로: {config.MODEL_SAVE_PATH}")
    
    # 절대 경로로도 시도
    model_path = config.MODEL_SAVE_PATH
    if not os.path.exists(model_path):
        # 상대 경로로 시도
        model_path = os.path.join(current_dir, config.MODEL_SAVE_PATH)
        print(f"상대 경로 시도: {model_path}")
    
    if not os.path.exists(model_path):
        # 디렉토리 내용 확인
        models_dir = os.path.join(current_dir, "models")
        print(f"models 디렉토리 존재 여부: {os.path.exists(models_dir)}")
        if os.path.exists(models_dir):
            print(f"models 디렉토리 내용: {os.listdir(models_dir)}")
        return False, f"모델 파일을 찾을 수 없습니다. 경로: {config.MODEL_SAVE_PATH}, 현재 디렉토리: {current_dir}"
    
    try:
        # 모델 로드
        print(f"모델 파일 로드 시도: {model_path}")
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        # checkpoint에서 input_size 가져오기 (저장된 config 사용)
        saved_input_size = checkpoint['config'].get('input_size', config.MODEL_CONFIG["input_size"])
        
        model = LSTMAutoencoder(
            input_size=saved_input_size,
            hidden_size=checkpoint['config']['hidden_size'],
            num_layers=checkpoint['config']['num_layers'],
            dropout=checkpoint['config']['dropout']
        )
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        # Data Processor 로드
        data_processor = DataProcessor()
        scaler_path = config.SCALER_SAVE_PATH
        if not os.path.exists(scaler_path):
            scaler_path = os.path.join(current_dir, config.SCALER_SAVE_PATH)
        
        if os.path.exists(scaler_path):
            print(f"Scaler 파일 로드: {scaler_path}")
            data_processor.load_scaler(scaler_path)
        else:
            return False, f"Scaler 파일을 찾을 수 없습니다. 경로: {config.SCALER_SAVE_PATH}"
        
        # feature_names 설정 (5개 특징 고정)
        # heart_rate, steps, sleep, temperature, activity
        data_processor.feature_names = ['heart_rate', 'steps', 'sleep', 'temperature', 'activity']
        print(f"feature_names 설정: {data_processor.feature_names}")
        
        # Anomaly Detector 생성
        anomaly_detector = AnomalyDetector(model)
        
        # 임계값 설정 (모델 파일에서 로드 또는 기본값 사용)
        if 'threshold' in checkpoint:
            # 모델 파일에 저장된 임계값 사용
            anomaly_detector.threshold = checkpoint['threshold']
            print(f"모델 파일에서 임계값 로드: {anomaly_detector.threshold:.6f}")
        else:
            # 기본 임계값 사용
            min_threshold = config.ANOMALY_CONFIG.get("min_threshold", 0.01)
            anomaly_detector.threshold = min_threshold
            print(f"기본 임계값 사용: {min_threshold:.4f}")
        
        return True, "모델 로드 완료"
    except Exception as e:
        import traceback
        return False, f"모델 로드 실패: {str(e)}\n{traceback.format_exc()}"


def initialize_services():
    """서비스 초기화"""
    global db_manager, chatbot, notification_manager, health_scheduler
    
    # 서버 시작 시 이메일 주소 초기화 (재시작 시마다 비어있게)
    config.NOTIFICATION_CONFIG["user_emails"] = {}
    print("이메일 주소 저장소 초기화 완료 (서버 재시작 시마다 비어있게 시작)")
    
    # MongoDB 연결
    try:
        db_manager = MongoDBManager()
        db_manager.connect()
        db_manager.create_indexes()
    except Exception as e:
        print(f"MongoDB 연결 실패: {e}")
        db_manager = None
    
    # 챗봇 초기화
    chatbot = HealthChatbot(use_openai=bool(config.OPENAI_API_KEY))
    
    # 알림 시스템 초기화
    try:
        notification_manager = NotificationManager(db_manager=db_manager, chatbot=chatbot)
        if notification_manager.email_enabled:
            print("이메일 알림 시스템이 활성화되었습니다.")
        else:
            print("이메일 알림 시스템이 비활성화되어 있습니다. (.env 파일에서 EMAIL_ENABLED=true로 설정하세요)")
    except Exception as e:
        print(f"알림 시스템 초기화 실패: {e}")
        notification_manager = None
    
    # 건강 상태 체크 스케줄러 초기화
    try:
        health_scheduler = HealthCheckScheduler(
            db_manager=db_manager,
            chatbot=chatbot,
            notification_manager=notification_manager
        )
        health_scheduler.start()
    except Exception as e:
        print(f"건강 상태 체크 스케줄러 초기화 실패: {e}")
        health_scheduler = None


# 앱 시작 시 모델 및 서비스 초기화 (gunicorn에서도 실행되도록)
# 함수 정의 후에 호출해야 함
import sys

print("=" * 50, flush=True)
print("웨어러블 이상행동 탐지 시스템 시작", flush=True)
print("=" * 50, flush=True)
sys.stdout.flush()

# 모델 로드
try:
    success, message = load_model()
    sys.stdout.flush()
    if not success:
        print(f"경고: {message}", flush=True)
        print("모델 없이 서버를 시작합니다. 예측 기능은 사용할 수 없습니다.", flush=True)
    else:
        print(f"[OK] {message}", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"모델 로드 중 오류 발생: {str(e)}", flush=True)
    import traceback
    print(traceback.format_exc(), flush=True)
    success = False

# 서비스 초기화
try:
    initialize_services()
    print("서비스 초기화 완료", flush=True)
    sys.stdout.flush()
except Exception as e:
    print(f"서비스 초기화 중 오류 발생: {str(e)}", flush=True)
    import traceback
    print(traceback.format_exc(), flush=True)

print("=" * 50, flush=True)
sys.stdout.flush()


@app.route('/')
def index():
    """웹 대시보드"""
    return render_template('index.html')


@app.route('/upload')
def upload():
    """건강 데이터 업로드 페이지"""
    return render_template('upload.html')


@app.route('/history')
def history():
    """데이터 조회 페이지"""
    return render_template('history.html')


@app.route('/favicon.ico')
def favicon():
    """Favicon 처리 (404 에러 방지)"""
    return '', 204  # No Content


@app.route('/predict', methods=['POST'])
def predict():
    """
    이상 탐지 예측 API
    
    요청 형식:
    {
        "user_id": "user001",
        "sensor_data": [
            {"time": "09:00", "heart_rate": 72, "steps": 120, ...},
            ...
        ]
    }
    """
    if model is None or anomaly_detector is None:
        return jsonify({"error": "모델이 로드되지 않았습니다."}), 500
    
    try:
        # JSON 데이터 확인
        if not request.is_json:
            return jsonify({"error": "Content-Type이 application/json이어야 합니다."}), 400
        
        data = request.json
        if data is None:
            return jsonify({"error": "요청 데이터가 비어있습니다."}), 400
        
        user_id = data.get("user_id")
        sensor_data = data.get("sensor_data", [])
        
        if not sensor_data:
            return jsonify({"error": "sensor_data가 필요합니다."}), 400
        
        if not isinstance(sensor_data, list):
            return jsonify({"error": "sensor_data는 배열이어야 합니다."}), 400
        
        # 시계열 데이터 준비
        # sensor_data를 시퀀스로 변환
        sequence_length = config.MODEL_CONFIG["sequence_length"]
        
        # 데이터가 부족하면 마지막 데이터로 자동 채우기
        if len(sensor_data) < sequence_length:
            if len(sensor_data) > 0:
                import copy
                last_data = sensor_data[-1]
                # 마지막 데이터를 복사하여 60개까지 채우기
                while len(sensor_data) < sequence_length:
                    if isinstance(last_data, dict):
                        sensor_data.append(copy.deepcopy(last_data))
                    else:
                        sensor_data.append(last_data)
            else:
                return jsonify({
                    "error": f"최소 1개의 데이터 포인트가 필요합니다."
                }), 400
        
        # 특징 추출 (리스트 컴프리헨션으로 최적화)
        feature_values = [
            [float(sd.get(feature_name, 0.0)) for feature_name in data_processor.feature_names]
            for sd in sensor_data[-sequence_length:]  # 최근 sequence_length개만 사용
        ]
        
        # 전처리 (메모리 최적화 - float32 사용)
        feature_array = np.array(feature_values, dtype=np.float32)
        feature_array_normalized = data_processor.normalize(feature_array, fit=False)
        feature_array_normalized = feature_array_normalized.reshape(1, sequence_length, -1).astype(np.float32)
        
        # 이상 탐지 (최적화: 모델 추론을 한 번만 실행하고 특징 분석도 함께 수행)
        # feature_names가 있는 경우에만 특징 분석 포함
        include_analysis = bool(data_processor.feature_names and len(data_processor.feature_names) > 0)
        
        try:
            anomaly_result = anomaly_detector.detect_single(
                feature_array_normalized,
                include_feature_analysis=include_analysis,
                feature_names=data_processor.feature_names if include_analysis else None
            )
        except Exception as e:
            # 특징 분석 실패 시 기본 이상 탐지만 수행
            print(f"특징 분석 중 오류 발생, 기본 이상 탐지만 수행: {e}")
            anomaly_result = anomaly_detector.detect_single(
                feature_array_normalized,
                include_feature_analysis=False,
                feature_names=None
            )
        
        # 특징별 분석 결과 추출
        feature_analysis = anomaly_result.get("feature_analysis", {})
        
        # 챗봇 피드백 생성 (비동기 처리 가능하도록 선택적)
        user_data = {
            "user_id": user_id,
            "sensor_data": sensor_data
        }
        # 챗봇 피드백은 빠른 응답을 위해 rule-based로 먼저 생성하고,
        # 필요시 OpenAI API는 백그라운드에서 처리할 수 있도록 개선
        feedback = chatbot.generate_feedback(anomaly_result, user_data)
        
        # 이상 탐지 시 알림 발송 (비동기 처리 - 응답 속도 개선)
        # 알림은 백그라운드 스레드에서 처리하고 즉시 응답 반환
        notification_result = None
        if notification_manager and anomaly_result.get("is_anomaly", False):
            # 이메일 발송을 스레드로 비동기 처리하여 응답 지연 방지
            import threading
            def send_alert_async():
                try:
                    result = notification_manager.send_alert(
                        user_id=user_id,
                        anomaly_result=anomaly_result,
                        user_data=user_data
                    )
                    print(f"비동기 알림 발송 완료: {result}")
                except Exception as e:
                    print(f"비동기 알림 발송 실패: {e}")
            
            # 백그라운드 스레드에서 알림 발송
            alert_thread = threading.Thread(target=send_alert_async, daemon=True)
            alert_thread.start()
            
            # 즉시 응답을 위해 알림 발송 중임을 표시
            notification_result = {"sent": "processing", "message": "알림 발송 중..."}
        
        response = {
            "user_id": user_id,
            "anomaly_detected": anomaly_result["is_anomaly"],
            "anomaly_score": anomaly_result["anomaly_score"],
            "reconstruction_error": anomaly_result["reconstruction_error"],
            "threshold": anomaly_result["threshold"],
            "feature_analysis": feature_analysis,
            "chatbot_feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
        
        # 알림 결과 추가
        if notification_result:
            response["notification"] = notification_result
        
        # numpy 타입을 Python 기본 타입으로 변환 (JSON 직렬화를 위해)
        response = convert_numpy_types(response)
        
        return jsonify(response)
        
    except KeyError as e:
        return jsonify({"error": f"필수 필드가 누락되었습니다: {str(e)}"}), 400
    except ValueError as e:
        return jsonify({"error": f"데이터 형식 오류: {str(e)}"}), 400
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"예측 오류: {error_detail}")
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500


@app.route('/save_data', methods=['POST'])
def save_data():
    """
    MongoDB에 데이터 저장
    
    요청 형식:
    {
        "user_id": "user001",
        "date": "2025-11-06",
        "sensor_data": [...],
        "anomaly_score": 0.85,
        "anomaly_detected": true,
        "chatbot_feedback": "..."
    }
    """
    if db_manager is None:
        return jsonify({"error": "MongoDB가 연결되지 않았습니다."}), 500
    
    try:
        data = request.json
        user_id = data.get("user_id")
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        sensor_data = data.get("sensor_data", [])
        anomaly_score = data.get("anomaly_score")
        anomaly_detected = data.get("anomaly_detected", False)
        chatbot_feedback = data.get("chatbot_feedback")
        
        document_id = db_manager.save_sensor_log(
            user_id=user_id,
            date=date,
            sensor_data=sensor_data,
            anomaly_score=anomaly_score,
            anomaly_detected=anomaly_detected,
            chatbot_feedback=chatbot_feedback
        )
        
        return jsonify({
            "success": True,
            "document_id": document_id,
            "message": "데이터 저장 완료"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_user/<user_id>', methods=['GET'])
def get_user(user_id):
    """
    사용자 데이터 조회
    
    쿼리 파라미터:
    - date: 특정 날짜 (선택)
    - limit: 조회 개수 제한 (기본값: 100)
    """
    if db_manager is None:
        # MongoDB가 연결되지 않았을 때 빈 데이터 반환
        return jsonify({
            "user_id": user_id,
            "count": 0,
            "data": [],
            "message": "MongoDB가 연결되지 않았습니다. 데이터가 없습니다."
        }), 200
    
    try:
        date = request.args.get('date')
        limit = int(request.args.get('limit', 100))
        
        user_data = db_manager.get_user_data(
            user_id=user_id,
            date=date,
            limit=limit
        )
        
        return jsonify({
            "user_id": user_id,
            "count": len(user_data),
            "data": user_data
        })
        
    except Exception as e:
        # 에러 발생 시에도 빈 데이터 반환 (500 에러 대신)
        return jsonify({
            "user_id": user_id,
            "count": 0,
            "data": [],
            "error": str(e)
        }), 200


@app.route('/delete_user_data/<document_id>', methods=['DELETE'])
def delete_user_data(document_id):
    """사용자 데이터 삭제"""
    if db_manager is None:
        return jsonify({"error": "MongoDB가 연결되지 않았습니다."}), 500
    
    try:
        success = db_manager.delete_user_data(document_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "데이터가 삭제되었습니다."
            })
        else:
            return jsonify({
                "success": False,
                "error": "삭제할 데이터를 찾을 수 없습니다."
            }), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_user_anomalies/<user_id>', methods=['GET'])
def get_user_anomalies(user_id):
    """
    사용자 이상 탐지 기록 조회
    
    쿼리 파라미터:
    - start_date: 시작 날짜 (선택)
    - end_date: 종료 날짜 (선택)
    """
    if db_manager is None:
        return jsonify({"error": "MongoDB가 연결되지 않았습니다."}), 500
    
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        anomalies = db_manager.get_user_anomalies(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            "user_id": user_id,
            "count": len(anomalies),
            "anomalies": anomalies
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_statistics/<user_id>', methods=['GET'])
def get_statistics(user_id):
    """사용자 통계 정보 조회"""
    # 기본 통계 반환 (MongoDB 연결 여부와 관계없이)
    default_stats = {
        "user_id": user_id,
        "total_logs": 0,
        "anomaly_count": 0,
        "anomaly_rate": 0,
        "avg_anomaly_score": 0,
        "max_anomaly_score": 0,
        "min_anomaly_score": 0
    }
    
    if db_manager is None:
        # MongoDB가 연결되지 않았을 때 기본 통계 반환
        return jsonify(default_stats), 200
    
    try:
        stats = db_manager.get_statistics(user_id)
        return jsonify(stats)
    except Exception as e:
        # 에러 발생 시 기본 통계 반환 (500 에러 대신)
        print(f"통계 조회 오류: {e}")
        default_stats["error"] = str(e)
        return jsonify(default_stats), 200


@app.route('/chat', methods=['POST'])
def chat():
    """
    챗봇 대화 API
    
    요청 형식:
    {
        "message": "오늘 건강 상태는 어때?",
        "user_id": "user001" (선택)
    }
    """
    if chatbot is None:
        return jsonify({"error": "챗봇이 초기화되지 않았습니다."}), 500
    
    try:
        data = request.json
        message = data.get("message")
        user_id = data.get("user_id", "user001")
        
        if not message:
            return jsonify({"error": "message가 필요합니다."}), 400
        
        # 사용자 컨텍스트 가져오기 (선택)
        context = None
        if user_id and db_manager:
            stats = db_manager.get_statistics(user_id)
            context = stats
        
        response = chatbot.chat(message, context)
        
        # 사용자 응답 시간 업데이트 (스케줄러가 있으면)
        if health_scheduler:
            health_scheduler.update_user_response(user_id)
        
        return jsonify({
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """헬스 체크"""
    status = {
        "model_loaded": model is not None,
        "db_connected": db_manager is not None if db_manager else False,
        "chatbot_ready": chatbot is not None
    }
    return jsonify(status)


@app.route('/get_notifications/<user_id>', methods=['GET'])
def get_notifications(user_id):
    """
    사용자의 대기 중인 알림 조회
    
    Returns:
        대기 중인 알림 리스트
    """
    if db_manager is None:
        return jsonify({"notifications": []}), 200
    
    try:
        notifications = db_manager.get_pending_notifications(user_id)
        return jsonify({
            "notifications": notifications,
            "count": len(notifications)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/mark_notification_read/<notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    """알림을 읽음으로 표시"""
    if db_manager is None:
        return jsonify({"error": "MongoDB가 연결되지 않았습니다."}), 500
    
    try:
        count = db_manager.mark_notification_read(notification_id)
        return jsonify({
            "success": count > 0,
            "message": "알림이 읽음으로 표시되었습니다."
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/mark_notification_responded/<notification_id>', methods=['POST'])
def mark_notification_responded(notification_id):
    """알림에 응답했다고 표시"""
    if db_manager is None:
        return jsonify({"error": "MongoDB가 연결되지 않았습니다."}), 500
    
    try:
        count = db_manager.mark_notification_responded(notification_id)
        
        # 스케줄러에 응답 시간 업데이트
        if health_scheduler and count > 0:
            # 알림에서 user_id 가져오기
            notification_collection = db_manager.db.get_collection("notifications")
            from bson import ObjectId
            notif = notification_collection.find_one({"_id": ObjectId(notification_id)})
            if notif:
                health_scheduler.update_user_response(notif["user_id"])
        
        return jsonify({
            "success": count > 0,
            "message": "응답이 기록되었습니다."
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/upload_health_data', methods=['POST'])
def upload_health_data():
    """
    건강 데이터 파일 업로드 (가장 쉬운 방법!)
    
    아이폰 건강앱에서 내보낸 JSON 파일 또는 CSV 파일을 업로드하여 분석합니다.
    
    지원 형식:
    - XML 파일 (아이폰 건강앱 내보내기) ⭐ 권장
    - JSON 파일 (아이폰 건강앱 내보내기)
    - CSV 파일 (수동 정리)
    
    요청:
    - file: 업로드할 파일 (JSON 또는 CSV)
    - user_id: 사용자 ID
    """
    if model is None or anomaly_detector is None:
        return jsonify({"error": "모델이 로드되지 않았습니다."}), 500
    
    if 'file' not in request.files:
        return jsonify({"error": "파일이 없습니다."}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id', 'user001')
    
    if file.filename == '':
        return jsonify({"error": "파일이 선택되지 않았습니다."}), 400
    
    try:
        # 파일 이름 안전하게 처리 (Windows 호환성)
        try:
            filename = secure_filename(file.filename)
        except Exception as e:
            # secure_filename 실패 시 원본 파일명 사용 (특수문자 제거)
            filename = file.filename or 'uploaded_file'
            filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
        
        file_extension = os.path.splitext(filename)[1].lower()
        
        # JSON 파일 처리
        if file_extension == '.json':
            # 파일 포인터를 처음으로 이동
            try:
                file.seek(0)
            except (OSError, AttributeError) as e:
                # 파일 객체가 seek를 지원하지 않거나 오류 발생 시
                print(f"파일 포인터 이동 실패 (무시하고 계속): {e}")
            
            try:
                health_data_dict = json.load(file)
            except json.JSONDecodeError as e:
                return jsonify({"error": f"JSON 파일 파싱 실패: {str(e)}"}), 400
            except Exception as e:
                return jsonify({"error": f"JSON 파일 읽기 실패: {str(e)}"}), 400
            
            # HealthKit 내보내기 JSON 형식 처리
            health_data = []
            
            # 다양한 JSON 형식 지원
            if isinstance(health_data_dict, dict):
                # HealthKit 내보내기 형식 처리
                for key, value in health_data_dict.items():
                    if isinstance(value, list):
                        for entry in value:
                            if isinstance(entry, dict):
                                # HealthKit 형식 변환
                                entry_type = key.lower().replace(' ', '_').replace('-', '_')
                                if 'value' in entry or 'quantity' in entry:
                                    health_data.append({
                                        "type": entry_type,
                                        "value": entry.get('value') or entry.get('quantity') or entry.get('count', 0),
                                        "unit": entry.get('unit', ''),
                                        "timestamp": entry.get('timestamp') or entry.get('date') or datetime.now().isoformat()
                                    })
            elif isinstance(health_data_dict, list):
                # 이미 배열 형식인 경우
                health_data = health_data_dict
        
        # XML 파일 처리 (아이폰 건강앱 내보내기 형식)
        elif file_extension == '.xml':
            # XML 파일 읽기 (파일 객체를 문자열로 읽어서 파싱)
            try:
                file.seek(0)  # 파일 포인터를 처음으로
            except (OSError, AttributeError) as e:
                # 파일 객체가 seek를 지원하지 않거나 오류 발생 시
                print(f"파일 포인터 이동 실패 (무시하고 계속): {e}")
            
            xml_content = file.read()
            if isinstance(xml_content, bytes):
                try:
                    xml_content = xml_content.decode('utf-8')
                except UnicodeDecodeError:
                    # UTF-8 디코딩 실패 시 다른 인코딩 시도
                    xml_content = xml_content.decode('cp949', errors='ignore')
            
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                return jsonify({"error": f"XML 파일 파싱 실패: {str(e)}"}), 400
            
            health_data = []
            
            # 네임스페이스 처리
            ns = {}
            if root.tag.startswith('{'):
                ns_uri = root.tag.split('}')[0][1:]
                ns = {'ns': ns_uri, '': ns_uri}  # 기본 네임스페이스도 추가
            
            # CDA 형식인지 확인 (ClinicalDocument)
            is_cda = 'ClinicalDocument' in root.tag or 'clinicaldocument' in root.tag.lower()
            
            if is_cda:
                # CDA (HL7 Clinical Document Architecture) 형식 처리
                print("CDA 형식 XML 파일 감지")
                
                # CDA 네임스페이스 정의
                cda_ns = {'cda': 'urn:hl7-org:v3', 'ns': 'urn:hl7-org:v3', '': 'urn:hl7-org:v3'}
                
                # XML 구조 디버깅 (처음 10개 요소만)
                print("XML 구조 분석 중...")
                all_elements = []
                for elem in root.iter():
                    tag = elem.tag
                    if '}' in tag:
                        tag = tag.split('}')[1]
                    all_elements.append(tag)
                    if len(all_elements) >= 20:  # 처음 20개만
                        break
                print(f"발견된 XML 요소들: {set(all_elements[:20])}")
                
                # observation 요소 찾기 (다양한 방법)
                observations = []
                
                # 방법 1: 네임스페이스 포함 패턴
                for pattern in ['.//{urn:hl7-org:v3}observation', './/observation', 
                               './/cda:observation', './/ns:observation',
                               './/{urn:hl7-org:v3}Observation', './/Observation']:
                    try:
                        found = root.findall(pattern, cda_ns)
                        if found:
                            observations.extend(found)
                            print(f"패턴 '{pattern}'으로 {len(found)}개 발견")
                    except Exception as e:
                        pass
                
                # 방법 2: 모든 요소 순회하며 observation 찾기
                if not observations:
                    for elem in root.iter():
                        tag_lower = elem.tag.lower()
                        if '}' in tag_lower:
                            tag_lower = tag_lower.split('}')[1]
                        if 'observation' in tag_lower:
                            observations.append(elem)
                    
                    if observations:
                        print(f"모든 요소 순회로 {len(observations)}개 observation 발견")
                
                # 방법 3: entry 요소 안의 observation 찾기
                if not observations:
                    entries = []
                    for elem in root.iter():
                        tag_lower = elem.tag.lower()
                        if '}' in tag_lower:
                            tag_lower = tag_lower.split('}')[1]
                        if 'entry' in tag_lower:
                            entries.append(elem)
                    
                    print(f"Entry 요소 {len(entries)}개 발견")
                    for entry in entries:
                        for child in entry.iter():
                            tag_lower = child.tag.lower()
                            if '}' in tag_lower:
                                tag_lower = tag_lower.split('}')[1]
                            if 'observation' in tag_lower:
                                observations.append(child)
                    
                    if observations:
                        print(f"Entry 안에서 {len(observations)}개 observation 발견")
                
                # 방법 4: section 요소 안의 observation 찾기
                if not observations:
                    sections = []
                    for elem in root.iter():
                        tag_lower = elem.tag.lower()
                        if '}' in tag_lower:
                            tag_lower = tag_lower.split('}')[1]
                        if 'section' in tag_lower:
                            sections.append(elem)
                    
                    print(f"Section 요소 {len(sections)}개 발견")
                    for section in sections:
                        for child in section.iter():
                            tag_lower = child.tag.lower()
                            if '}' in tag_lower:
                                tag_lower = tag_lower.split('}')[1]
                            if 'observation' in tag_lower or 'entry' in tag_lower:
                                if 'observation' in tag_lower:
                                    observations.append(child)
                                else:  # entry 안의 observation 찾기
                                    for subchild in child.iter():
                                        sub_tag_lower = subchild.tag.lower()
                                        if '}' in sub_tag_lower:
                                            sub_tag_lower = sub_tag_lower.split('}')[1]
                                        if 'observation' in sub_tag_lower:
                                            observations.append(subchild)
                    
                    if observations:
                        print(f"Section 안에서 {len(observations)}개 observation 발견")
                
                print(f"CDA 파일에서 총 {len(observations)}개의 observation 요소를 찾았습니다.")
                
                # Record 요소도 찾기 (HealthKit 형식일 수 있음)
                # recordTarget은 제외하고 실제 건강 데이터가 있는 Record만 찾기
                records = []
                
                # 모든 요소 순회하며 실제 Record 찾기 (recordTarget 제외)
                for elem in root.iter():
                    tag = elem.tag
                    tag_lower = tag.lower()
                    
                    # 네임스페이스 제거
                    if '}' in tag_lower:
                        tag_lower = tag_lower.split('}')[1]
                    
                    # recordTarget, recordTarget 등은 제외
                    if tag_lower == 'record' and 'target' not in tag_lower:
                        # type 속성이 있는 Record만 선택 (실제 건강 데이터)
                        if elem.get('type') or elem.get('recordType'):
                            records.append(elem)
                            print(f"Record 발견: type={elem.get('type') or elem.get('recordType')}")
                
                # 패턴으로도 찾기 (recordTarget 제외)
                if not records:
                    for pattern in ['.//Record', './/record', './/HKRecord']:
                        try:
                            found = root.findall(pattern, cda_ns) if cda_ns else root.findall(pattern)
                            if found:
                                # type 속성이 있는 것만 필터링
                                filtered = [r for r in found if r.get('type') or r.get('recordType')]
                                if filtered:
                                    records.extend(filtered)
                                    print(f"패턴 '{pattern}'으로 {len(filtered)}개 Record 발견")
                                    break
                        except:
                            pass
                
                if records:
                    print(f"CDA 파일에서 {len(records)}개의 실제 Record 요소를 발견했습니다. observation으로 변환합니다.")
                    observations.extend(records)
                else:
                    print("실제 건강 데이터가 있는 Record 요소를 찾지 못했습니다.")
                
                # observation이 없으면 모든 요소 확인
                if not observations:
                    print("Observation 요소를 찾지 못했습니다. XML 구조를 더 자세히 분석합니다...")
                    # 모든 자식 요소 확인
                    for i, child in enumerate(root[:10]):
                        print(f"루트 자식 {i}: {child.tag}")
                        for j, grandchild in enumerate(child[:5]):
                            print(f"  - 자식 {j}: {grandchild.tag}")
                    
                    # entry나 다른 요소에서 직접 데이터 추출 시도
                    print("Entry나 다른 요소에서 직접 데이터 추출 시도...")
                    # 모든 entry 요소를 observation으로 간주
                    for elem in root.iter():
                        tag_lower = elem.tag.lower()
                        if '}' in tag_lower:
                            tag_lower = tag_lower.split('}')[1]
                        if 'entry' in tag_lower:
                            # entry 안에 observation이 없으면 entry 자체를 사용
                            has_obs = False
                            for child in elem.iter():
                                child_tag = child.tag.lower()
                                if '}' in child_tag:
                                    child_tag = child_tag.split('}')[1]
                                if 'observation' in child_tag:
                                    has_obs = True
                                    break
                            if not has_obs:
                                observations.append(elem)
                    
                    if observations:
                        print(f"Entry 요소를 observation으로 사용: {len(observations)}개")
                
                # CDA code 시스템 매핑 (LOINC 코드)
                code_mapping = {
                    '8867-4': 'heart_rate',  # Heart rate
                    '55423-8': 'steps',  # Step count
                    '9279-1': 'sleep',  # Sleep analysis
                    '8310-5': 'temperature',  # Body temperature
                    '55424-6': 'activity',  # Active energy burned
                    '55425-3': 'distance',  # Distance walking/running
                }
                
                # 표시명 기반 매핑
                display_name_mapping = {
                    'heart rate': 'heart_rate',
                    'heartrate': 'heart_rate',
                    '심박수': 'heart_rate',
                    'step': 'steps',
                    '걸음': 'steps',
                    'sleep': 'sleep',
                    '수면': 'sleep',
                    'temperature': 'temperature',
                    '체온': 'temperature',
                    'energy': 'activity',
                    '활동량': 'activity',
                    'distance': 'distance',
                    '거리': 'distance',
                }
                
                for obs in observations:
                    # code 요소에서 타입 추출 (다양한 방법 시도)
                    code_elem = None
                    for pattern in ['.//code', './/cda:code', './/ns:code', 'code', 'cda:code']:
                        code_elem = obs.find(pattern, cda_ns) if cda_ns else obs.find(pattern)
                        if code_elem is not None:
                            break
                    
                    # code 요소가 없으면 직접 속성에서 추출
                    if code_elem is None:
                        code_elem = obs
                    
                    data_type = None
                    
                    # 1. code 속성에서 추출
                    code_attr = code_elem.get('code')
                    if code_attr and code_attr in code_mapping:
                        data_type = code_mapping[code_attr]
                    
                    # 2. displayName에서 추출
                    if not data_type:
                        display_name = code_elem.get('displayName', '').lower()
                        if not display_name:
                            display_name = code_elem.get('displayName', '').lower()
                        for key, mapped in display_name_mapping.items():
                            if key in display_name:
                                data_type = mapped
                                break
                    
                    # 3. 타입명에서 직접 추출 (예: HKQuantityTypeIdentifierHeartRate)
                    if not data_type:
                        type_attr = code_elem.get('type') or obs.get('type')
                        if type_attr:
                            type_lower = type_attr.lower()
                            if 'heart' in type_lower or '심박' in type_lower:
                                data_type = 'heart_rate'
                            elif 'step' in type_lower or '걸음' in type_lower:
                                data_type = 'steps'
                            elif 'sleep' in type_lower or '수면' in type_lower:
                                data_type = 'sleep'
                            elif 'temperature' in type_lower or '체온' in type_lower:
                                data_type = 'temperature'
                            elif 'energy' in type_lower or '활동' in type_lower:
                                data_type = 'activity'
                            elif 'distance' in type_lower or '거리' in type_lower:
                                data_type = 'distance'
                    
                    # 4. 태그 이름에서 추출
                    if not data_type:
                        tag_name = obs.tag.lower()
                        if '}' in tag_name:
                            tag_name = tag_name.split('}')[1]
                        for key, mapped in display_name_mapping.items():
                            if key in tag_name:
                                data_type = mapped
                                break
                    
                    if not data_type:
                        # 알 수 없는 타입이지만 값이 있으면 일반 타입으로 처리
                        print(f"알 수 없는 데이터 타입, code: {code_attr}, displayName: {code_elem.get('displayName')}, type: {type_attr}")
                        continue
                    
                    # value 요소에서 값 추출 (다양한 방법 시도)
                    value = None
                    
                    # 1. value 요소에서 추출 (CDA 형식)
                    value_elem = obs.find('.//value') or obs.find('.//cda:value', cda_ns)
                    if value_elem is not None:
                        value = value_elem.get('value')
                        if not value and value_elem.text:
                            value = value_elem.text
                    
                    # 2. value 속성에서 직접 추출 (HealthKit Record 형식)
                    if not value:
                        value = obs.get('value') or obs.get('quantity')
                    
                    # 3. 하위 요소에서 추출
                    if not value:
                        for value_elem_name in ['value', 'Value', 'quantity', 'Quantity']:
                            value_elem = obs.find(value_elem_name)
                            if value_elem is not None and value_elem.text:
                                value = value_elem.text
                                break
                    
                    if not value:
                        continue
                    
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue
                    
                    # effectiveTime 또는 authorTime에서 타임스탬프 추출 (다양한 방법 시도)
                    timestamp = None
                    
                    # 1. CDA 형식: effectiveTime 또는 authorTime 요소
                    time_elem = obs.find('.//effectiveTime') or obs.find('.//authorTime') or \
                               obs.find('.//cda:effectiveTime', cda_ns) or obs.find('.//cda:authorTime', cda_ns)
                    
                    if time_elem is not None:
                        timestamp = time_elem.get('value')
                        if not timestamp and time_elem.text:
                            timestamp = time_elem.text
                    
                    # 2. HealthKit Record 형식: startDate, date, creationDate 속성
                    if not timestamp:
                        for date_attr in ['startDate', 'date', 'creationDate', 'startdate', 'Date', 'CreationDate']:
                            timestamp = obs.get(date_attr)
                            if timestamp:
                                break
                    
                    # 3. 하위 요소에서 추출
                    if not timestamp:
                        for date_elem_name in ['startDate', 'date', 'startdate', 'Date', 'effectiveTime', 'authorTime']:
                            date_elem = obs.find(date_elem_name)
                            if date_elem is not None and date_elem.text:
                                timestamp = date_elem.text
                                break
                            
                            # CDA 네임스페이스 포함
                            date_elem = obs.find(f'.//cda:{date_elem_name}', cda_ns)
                            if date_elem is not None:
                                timestamp = date_elem.get('value') or date_elem.text
                                if timestamp:
                                    break
                    
                    if not timestamp:
                        timestamp = datetime.now().isoformat()
                    
                    # unit 요소에서 단위 추출
                    unit = ''
                    unit_elem = obs.find('.//unit') or obs.find('.//cda:unit', cda_ns)
                    if unit_elem is not None:
                        unit = unit_elem.get('value') or unit_elem.text or ''
                    
                    health_data.append({
                        "type": data_type,
                        "value": value,
                        "unit": unit,
                        "timestamp": timestamp
                    })
                
            else:
                # 일반 HealthKit XML 형식 처리
                print("일반 HealthKit XML 형식 처리")
                
                # Record 요소 찾기
                records = []
                for pattern in ['.//Record', './/record', './/HKRecord',
                               './/{urn:hl7-org:v3}Record', './/ns:Record']:
                    try:
                        found = root.findall(pattern, ns) if ns else root.findall(pattern)
                        if found:
                            records.extend(found)
                            break
                    except:
                        pass
                
                # 모든 요소 순회하며 Record 찾기
                if not records:
                    for elem in root.iter():
                        tag_lower = elem.tag.lower()
                        if '}' in tag_lower:
                            tag_lower = tag_lower.split('}')[1]
                        if 'record' in tag_lower:
                            records.append(elem)
                
                print(f"XML 파일에서 {len(records)}개의 Record 요소를 찾았습니다.")
                
                # 타입 매핑
                type_mapping = {
                    'HKQuantityTypeIdentifierHeartRate': 'heart_rate',
                    'HKQuantityTypeIdentifierStepCount': 'steps',
                    'HKCategoryTypeIdentifierSleepAnalysis': 'sleep',
                    'HKQuantityTypeIdentifierBodyTemperature': 'temperature',
                    'HKQuantityTypeIdentifierActiveEnergyBurned': 'activity',
                    'HKQuantityTypeIdentifierDistanceWalkingRunning': 'distance',
                    'HKQuantityTypeIdentifierFlightsClimbed': 'flights_climbed',
                    'HKQuantityTypeIdentifierRestingHeartRate': 'resting_heart_rate',
                }
                
                for record in records:
                    # type 속성 추출
                    record_type = record.get('type') or record.get('recordType') or record.get('Type')
                    if not record_type:
                        continue
                    
                    mapped_type = type_mapping.get(record_type, None)
                    if not mapped_type:
                        continue
                    
                    # 값 추출
                    value = record.get('value') or record.get('quantity') or record.get('Value')
                    if not value:
                        for value_elem_name in ['value', 'Value', 'quantity', 'Quantity']:
                            value_elem = record.find(value_elem_name)
                            if value_elem is not None and value_elem.text:
                                value = value_elem.text
                                break
                    
                    if not value:
                        continue
                    
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        continue
                    
                    # 타임스탬프 추출
                    timestamp = record.get('startDate') or record.get('date') or record.get('creationDate')
                    if not timestamp:
                        for date_elem_name in ['startDate', 'date', 'startdate', 'Date']:
                            date_elem = record.find(date_elem_name)
                            if date_elem is not None and date_elem.text:
                                timestamp = date_elem.text
                                break
                    
                    if not timestamp:
                        timestamp = datetime.now().isoformat()
                    
                    # 단위 추출
                    unit = record.get('unit') or record.get('Unit') or ''
                    if not unit:
                        unit_elem = record.find('unit') or record.find('Unit')
                        if unit_elem is not None:
                            unit = unit_elem.text or ''
                    
                    health_data.append({
                        "type": mapped_type,
                        "value": value,
                        "unit": unit,
                        "timestamp": timestamp
                    })
            
            print(f"처리된 건강 데이터: {len(health_data)}개")
        
        # CSV 파일 처리
        elif file_extension == '.csv':
            # 파일 포인터를 처음으로 이동
            try:
                file.seek(0)
            except (OSError, AttributeError) as e:
                # 파일 객체가 seek를 지원하지 않거나 오류 발생 시
                print(f"파일 포인터 이동 실패 (무시하고 계속): {e}")
            
            try:
                df = pd.read_csv(file, encoding='utf-8')
            except UnicodeDecodeError:
                # UTF-8로 읽기 실패 시 다른 인코딩 시도
                try:
                    file.seek(0)
                except (OSError, AttributeError):
                    pass
                df = pd.read_csv(file, encoding='cp949')  # Windows 기본 인코딩
            except Exception as e:
                return jsonify({"error": f"CSV 파일 읽기 실패: {str(e)}"}), 400
            health_data = []
            
            # CSV를 HealthKit 형식으로 변환
            # 컬럼명 매핑
            column_mapping = {
                'heart_rate': 'heart_rate',
                '심박수': 'heart_rate',
                'heartRate': 'heart_rate',
                'steps': 'steps',
                '걸음수': 'steps',
                'stepCount': 'steps',
                'sleep': 'sleep',
                '수면': 'sleep',
                'sleepAnalysis': 'sleep',
                'temperature': 'temperature',
                '체온': 'temperature',
                'activity': 'activity',
                '활동량': 'activity',
            }
            
            # 각 행마다 하나의 health_data 엔트리 생성
            for _, row in df.iterrows():
                timestamp = row.get('time') or row.get('timestamp') or row.get('시간') or datetime.now().isoformat()
                
                # 각 컬럼을 확인하여 health_data에 추가
                for col in df.columns:
                    mapped_type = column_mapping.get(col, column_mapping.get(col.lower(), None))
                    if mapped_type and pd.notna(row[col]):
                        health_data.append({
                            "type": mapped_type,
                            "value": float(row[col]),
                            "unit": "bpm" if mapped_type == "heart_rate" else ("count" if mapped_type == "steps" else ("hours" if mapped_type == "sleep" else "")),
                            "timestamp": str(timestamp)
                        })
        else:
            return jsonify({"error": f"지원하지 않는 파일 형식입니다. (.json, .csv, .xml 파일만 가능)"}), 400
        
        if not health_data:
            # 더 자세한 오류 메시지 제공
            error_msg = "파일에서 건강 데이터를 찾을 수 없습니다."
            debug_info = {}
            
            if file_extension == '.xml':
                error_msg += " XML 파일을 파싱했지만 건강 데이터를 찾을 수 없습니다."
                
                # XML 구조 정보 추가 (디버깅용)
                try:
                    file.seek(0)
                    xml_content = file.read()
                    if isinstance(xml_content, bytes):
                        xml_content = xml_content.decode('utf-8')
                    root = ET.fromstring(xml_content)
                    
                    # XML 구조 분석
                    elements_found = []
                    for elem in root.iter():
                        tag = elem.tag
                        if '}' in tag:
                            tag = tag.split('}')[1]
                        if tag not in elements_found:
                            elements_found.append(tag)
                        if len(elements_found) >= 30:  # 처음 30개만
                            break
                    
                    debug_info = {
                        "root_element": root.tag.split('}')[-1] if '}' in root.tag else root.tag,
                        "elements_found": elements_found[:20],  # 처음 20개만
                        "total_elements_checked": len(elements_found)
                    }
                    
                    # observation, entry, record 등이 있는지 확인
                    has_observation = any('observation' in e.lower() for e in elements_found)
                    has_entry = any('entry' in e.lower() for e in elements_found)
                    # recordTarget은 제외하고 실제 Record만 확인
                    has_record = any('record' in e.lower() and 'target' not in e.lower() for e in elements_found)
                    has_section = any('section' in e.lower() for e in elements_found)
                    
                    # type 속성이 있는 Record 요소 확인
                    has_record_with_type = False
                    try:
                        for elem in root.iter():
                            tag = elem.tag.lower()
                            if '}' in tag:
                                tag = tag.split('}')[1]
                            if tag == 'record' and 'target' not in tag:
                                if elem.get('type') or elem.get('recordType'):
                                    has_record_with_type = True
                                    break
                    except:
                        pass
                    
                    debug_info['has_record_with_type'] = has_record_with_type
                    
                    debug_info.update({
                        "has_observation": has_observation,
                        "has_entry": has_entry,
                        "has_record": has_record,
                        "has_section": has_section
                    })
                    
                    error_msg += f" 발견된 요소: {', '.join(elements_found[:10])}..."
                    
                    # 파일이 헤더만 있는지 확인
                    if not has_record_with_type:
                        error_msg += "<br><br>⚠️ <strong>이 파일은 헤더 정보만 포함되어 있습니다.</strong>"
                        error_msg += "<br>실제 건강 데이터(심박수, 걸음수, 수면 등)가 포함된 전체 XML 파일이 필요합니다."
                        error_msg += "<br><br><strong>해결 방법:</strong>"
                        error_msg += "<br>1. 아이폰 건강 앱 열기"
                        error_msg += "<br>2. 프로필(우측 상단) → 데이터 내보내기"
                        error_msg += "<br>3. 전체 데이터가 포함된 XML 파일 다운로드 (파일이 클 수 있음)"
                        error_msg += "<br>4. 다운로드가 완료될 때까지 기다리기"
                        error_msg += "<br>5. 완전한 XML 파일 다시 업로드"
                    else:
                        error_msg += " 아이폰 건강앱에서 '데이터 내보내기'로 다운로드한 전체 XML 파일인지 확인해주세요."
                    
                except Exception as e:
                    debug_info["parse_error"] = str(e)
                    error_msg += " 아이폰 건강앱에서 '데이터 내보내기'로 다운로드한 전체 XML 파일인지 확인해주세요."
            
            elif file_extension == '.json':
                error_msg += " JSON 파일 형식을 확인해주세요."
            elif file_extension == '.csv':
                error_msg += " CSV 파일에 heart_rate, steps, sleep 등의 컬럼이 있는지 확인해주세요."
            
            return jsonify({
                "error": error_msg,
                "file_type": file_extension,
                "hint": "파일이 올바른 형식인지, 아이폰 건강앱에서 내보낸 전체 파일인지 확인해주세요.",
                "debug_info": debug_info
            }), 400
        
        # sync_healthkit과 동일한 로직 사용
        # HealthKit 데이터를 센서 데이터 형식으로 변환
        sensor_data = []
        current_data = {}
        
        for entry in health_data:
            timestamp = entry.get("timestamp", datetime.now().isoformat())
            entry_type = entry.get("type")
            value = entry.get("value", 0)
            
            # 시간별로 데이터 그룹화
            time_key = timestamp[:13]  # 시간까지 (YYYY-MM-DDTHH)
            
            if time_key not in current_data:
                current_data[time_key] = {
                    "time": timestamp[:16] if len(timestamp) >= 16 else timestamp[:13] + ":00",
                    "heart_rate": 0,
                    "steps": 0,
                    "sleep": 0,
                    "temperature": 0,
                    "activity": 0
                }
            
            # 데이터 타입별로 매핑
            type_mapping = {
                "heart_rate": "heart_rate",
                "heartRate": "heart_rate",
                "Heart Rate": "heart_rate",
                "steps": "steps",
                "stepCount": "steps",
                "Step Count": "steps",
                "sleep": "sleep",
                "sleepAnalysis": "sleep",
                "Sleep Analysis": "sleep",
                "temperature": "temperature",
                "bodyTemperature": "temperature",
                "Body Temperature": "temperature",
                "activity": "activity",
                "activeEnergy": "activity",
                "Active Energy": "activity",
            }
            
            mapped_type = type_mapping.get(entry_type, type_mapping.get(entry_type.lower(), None))
            
            if mapped_type == "heart_rate":
                current_data[time_key]["heart_rate"] = float(value)
            elif mapped_type == "steps":
                current_data[time_key]["steps"] = float(value)
            elif mapped_type == "sleep":
                current_data[time_key]["sleep"] = float(value)
            elif mapped_type == "temperature":
                current_data[time_key]["temperature"] = float(value)
            elif mapped_type == "activity":
                current_data[time_key]["activity"] = float(value)
        
        # 시간순 정렬
        sensor_data = sorted(current_data.values(), key=lambda x: x["time"])
        
        if not sensor_data:
            return jsonify({"error": "유효한 센서 데이터가 없습니다."}), 400
        
        # 시계열 데이터 준비
        sequence_length = config.MODEL_CONFIG["sequence_length"]
        if len(sensor_data) < sequence_length:
            # 부족한 데이터는 첫 번째 데이터로 패딩 (0 대신 실제 데이터 복제)
            padding_needed = sequence_length - len(sensor_data)
            first_data = sensor_data[0] if sensor_data else {
                "time": datetime.now().isoformat()[:16],
                "heart_rate": 65, "steps": 5000, "sleep": 7, "temperature": 36.3, "activity": 300
            }
            for i in range(padding_needed):
                sensor_data.insert(0, {
                    "time": first_data["time"],
                    "heart_rate": first_data.get("heart_rate", 65),
                    "steps": first_data.get("steps", 5000),
                    "sleep": first_data.get("sleep", 7),
                    "temperature": first_data.get("temperature", 36.3),
                    "activity": first_data.get("activity", 300)
                })
        
        # 특징 추출
        feature_values = []
        for sd in sensor_data[-sequence_length:]:
            features = []
            for feature_name in data_processor.feature_names:
                features.append(sd.get(feature_name, 0))
            feature_values.append(features)
        
        # 전처리
        feature_array = np.array(feature_values)
        feature_array_normalized = data_processor.normalize(feature_array, fit=False)
        feature_array_normalized = feature_array_normalized.reshape(1, sequence_length, -1)
        
        # 이상 탐지
        anomaly_result = anomaly_detector.detect_single(feature_array_normalized)
        
        # 특징별 분석
        feature_analysis = anomaly_detector.analyze_anomaly_pattern(
            feature_array_normalized,
            data_processor.feature_names
        )
        
        # 챗봇 피드백 생성
        user_data_dict = {
            "user_id": user_id,
            "sensor_data": sensor_data
        }
        feedback = chatbot.generate_feedback(anomaly_result, user_data_dict)
        
        # 이상 탐지 시 알림 발송 (비동기 처리 - 응답 속도 개선)
        # 알림은 백그라운드 스레드에서 처리하고 즉시 응답 반환
        notification_result = None
        if notification_manager and anomaly_result.get("is_anomaly", False):
            # 이메일 발송을 스레드로 비동기 처리하여 응답 지연 방지
            import threading
            def send_alert_async():
                try:
                    result = notification_manager.send_alert(
                        user_id=user_id,
                        anomaly_result=anomaly_result,
                        user_data=user_data_dict
                    )
                    print(f"비동기 알림 발송 완료: {result}")
                except Exception as e:
                    print(f"비동기 알림 발송 실패: {e}")
            
            # 백그라운드 스레드에서 알림 발송
            alert_thread = threading.Thread(target=send_alert_async, daemon=True)
            alert_thread.start()
            
            # 즉시 응답을 위해 알림 발송 중임을 표시
            notification_result = {"sent": "processing", "message": "알림 발송 중..."}
        
        response = {
            "success": True,
            "message": "건강 데이터 파일 업로드 및 분석 완료",
            "user_id": user_id,
            "sensor_data": sensor_data,  # 센서 데이터 추가 (저장 기능용)
            "anomaly_detected": anomaly_result["is_anomaly"],
            "anomaly_score": float(anomaly_result["anomaly_score"]),
            "reconstruction_error": float(anomaly_result["reconstruction_error"]),
            "threshold": float(anomaly_result["threshold"]),
            "feature_analysis": feature_analysis,
            "chatbot_feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
        
        # 알림 결과 추가
        if notification_result:
            response["notification"] = notification_result
        
        # numpy 타입 변환
        response = convert_numpy_types(response)
        
        # MongoDB에 저장
        if db_manager:
            try:
                db_manager.save_sensor_log(
                    user_id=user_id,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    sensor_data=sensor_data,
                    anomaly_score=anomaly_result["anomaly_score"],
                    anomaly_detected=anomaly_result["is_anomaly"],
                    chatbot_feedback=feedback
                )
            except Exception as e:
                print(f"MongoDB 저장 실패: {e}")
        
        return jsonify(response)
        
    except json.JSONDecodeError as e:
        return jsonify({"error": f"JSON 파일 형식이 올바르지 않습니다: {str(e)}"}), 400
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/sync_healthkit', methods=['POST'])
def sync_healthkit():
    """
    HealthKit 데이터 동기화 API
    
    아이폰 건강앱(HealthKit)에서 수집한 데이터를 받아서 분석하고 저장합니다.
    
    요청 형식:
    {
        "user_id": "user001",
        "device_type": "iPhone",
        "health_data": [
            {
                "type": "heart_rate",
                "value": 72,
                "unit": "bpm",
                "timestamp": "2025-11-06T09:00:00Z"
            },
            {
                "type": "steps",
                "value": 1000,
                "unit": "count",
                "timestamp": "2025-11-06T09:00:00Z"
            },
            {
                "type": "sleep",
                "value": 7.5,
                "unit": "hours",
                "timestamp": "2025-11-06T09:00:00Z"
            }
        ]
    }
    """
    if model is None or anomaly_detector is None:
        return jsonify({"error": "모델이 로드되지 않았습니다."}), 500
    
    try:
        data = request.json
        user_id = data.get("user_id")
        device_type = data.get("device_type", "iPhone")
        health_data = data.get("health_data", [])
        
        if not health_data:
            return jsonify({"error": "health_data가 필요합니다."}), 400
        
        # HealthKit 데이터를 센서 데이터 형식으로 변환
        sensor_data = []
        current_data = {}
        
        # HealthKit 데이터를 시간순으로 정렬하고 센서 데이터 형식으로 변환
        for entry in health_data:
            timestamp = entry.get("timestamp", datetime.now().isoformat())
            entry_type = entry.get("type")
            value = entry.get("value", 0)
            
            # 시간별로 데이터 그룹화
            time_key = timestamp[:13]  # 시간까지 (YYYY-MM-DDTHH)
            
            if time_key not in current_data:
                current_data[time_key] = {
                    "time": timestamp[:16],  # YYYY-MM-DDTHH:MM
                    "heart_rate": 0,
                    "steps": 0,
                    "sleep": 0,
                    "temperature": 0,
                    "activity": 0
                }
            
            # 데이터 타입별로 매핑 (다양한 HealthKit 데이터 타입 자동 처리)
            # HealthKit에서 올 수 있는 다양한 타입들을 자동으로 매핑
            type_mapping = {
                # 직접 매핑
                "heart_rate": "heart_rate",
                "heartRate": "heart_rate",
                "Heart Rate": "heart_rate",
                "steps": "steps",
                "stepCount": "steps",
                "Step Count": "steps",
                "sleep": "sleep",
                "sleepAnalysis": "sleep",
                "Sleep Analysis": "sleep",
                "temperature": "temperature",
                "bodyTemperature": "temperature",
                "Body Temperature": "temperature",
                "activity": "activity",
                "activeEnergy": "activity",
                "Active Energy": "activity",
                "activeEnergyBurned": "activity",
                # 추가 지원 타입
                "distance": "distance",
                "walkingDistance": "distance",
                "Walking Distance": "distance",
                "flightsClimbed": "flights_climbed",
                "Flights Climbed": "flights_climbed",
                "restingHeartRate": "resting_heart_rate",
                "Resting Heart Rate": "resting_heart_rate",
                "walkingHeartRateAverage": "walking_heart_rate",
                "Walking Heart Rate Average": "walking_heart_rate",
            }
            
            # 타입 매핑 (대소문자 무시)
            mapped_type = type_mapping.get(entry_type, type_mapping.get(entry_type.lower(), None))
            
            if mapped_type:
                # 매핑된 타입에 따라 저장
                if mapped_type == "heart_rate":
                    current_data[time_key]["heart_rate"] = float(value)
                elif mapped_type == "steps":
                    current_data[time_key]["steps"] = float(value)
                elif mapped_type == "sleep":
                    current_data[time_key]["sleep"] = float(value)
                elif mapped_type == "temperature":
                    current_data[time_key]["temperature"] = float(value)
                elif mapped_type == "activity":
                    current_data[time_key]["activity"] = float(value)
                # 기타 타입은 로그만 남기고 무시 (필요시 추가 가능)
            else:
                # 알 수 없는 타입도 로그로 남기기
                print(f"알 수 없는 HealthKit 데이터 타입: {entry_type}, 값: {value}")
        
        # 시간순 정렬
        sensor_data = sorted(current_data.values(), key=lambda x: x["time"])
        
        if not sensor_data:
            return jsonify({"error": "유효한 센서 데이터가 없습니다."}), 400
        
        # 시계열 데이터 준비
        sequence_length = config.MODEL_CONFIG["sequence_length"]
        if len(sensor_data) < sequence_length:
            # 부족한 데이터는 첫 번째 데이터로 패딩 (0 대신 실제 데이터 복제)
            padding_needed = sequence_length - len(sensor_data)
            first_data = sensor_data[0] if sensor_data else {
                "time": datetime.now().isoformat()[:16],
                "heart_rate": 65, "steps": 5000, "sleep": 7, "temperature": 36.3, "activity": 300
            }
            for i in range(padding_needed):
                sensor_data.insert(0, {
                    "time": first_data["time"],
                    "heart_rate": first_data.get("heart_rate", 65),
                    "steps": first_data.get("steps", 5000),
                    "sleep": first_data.get("sleep", 7),
                    "temperature": first_data.get("temperature", 36.3),
                    "activity": first_data.get("activity", 300)
                })
        
        # 특징 추출
        feature_values = []
        for sd in sensor_data[-sequence_length:]:  # 최근 sequence_length개만 사용
            features = []
            for feature_name in data_processor.feature_names:
                features.append(sd.get(feature_name, 0))
            feature_values.append(features)
        
        # 전처리
        feature_array = np.array(feature_values)
        feature_array_normalized = data_processor.normalize(feature_array, fit=False)
        feature_array_normalized = feature_array_normalized.reshape(1, sequence_length, -1)
        
        # 이상 탐지
        anomaly_result = anomaly_detector.detect_single(feature_array_normalized)
        
        # 특징별 분석
        feature_analysis = anomaly_detector.analyze_anomaly_pattern(
            feature_array_normalized,
            data_processor.feature_names
        )
        
        # 챗봇 피드백 생성
        user_data_dict = {
            "user_id": user_id,
            "sensor_data": sensor_data
        }
        feedback = chatbot.generate_feedback(anomaly_result, user_data_dict)
        
        # 이상 탐지 시 알림 발송 (비동기 처리 - 응답 속도 개선)
        # 알림은 백그라운드 스레드에서 처리하고 즉시 응답 반환
        notification_result = None
        if notification_manager and anomaly_result.get("is_anomaly", False):
            # 이메일 발송을 스레드로 비동기 처리하여 응답 지연 방지
            import threading
            def send_alert_async():
                try:
                    result = notification_manager.send_alert(
                        user_id=user_id,
                        anomaly_result=anomaly_result,
                        user_data=user_data_dict
                    )
                    print(f"비동기 알림 발송 완료: {result}")
                except Exception as e:
                    print(f"비동기 알림 발송 실패: {e}")
            
            # 백그라운드 스레드에서 알림 발송
            alert_thread = threading.Thread(target=send_alert_async, daemon=True)
            alert_thread.start()
            
            # 즉시 응답을 위해 알림 발송 중임을 표시
            notification_result = {"sent": "processing", "message": "알림 발송 중..."}
        
        response = {
            "success": True,
            "message": "HealthKit 데이터 동기화 완료",
            "user_id": user_id,
            "device_type": device_type,
            "anomaly_detected": anomaly_result["is_anomaly"],
            "anomaly_score": float(anomaly_result["anomaly_score"]),
            "reconstruction_error": float(anomaly_result["reconstruction_error"]),
            "threshold": float(anomaly_result["threshold"]),
            "feature_analysis": feature_analysis,
            "chatbot_feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }
        
        # 알림 결과 추가
        if notification_result:
            response["notification"] = notification_result
        
        # numpy 타입 변환
        response = convert_numpy_types(response)
        
        # MongoDB에 저장 (선택)
        if db_manager:
            try:
                db_manager.save_sensor_log(
                    user_id=user_id,
                    date=datetime.now().strftime("%Y-%m-%d"),
                    sensor_data=sensor_data,
                    anomaly_score=anomaly_result["anomaly_score"],
                    anomaly_detected=anomaly_result["is_anomaly"],
                    chatbot_feedback=feedback
                )
            except Exception as e:
                print(f"MongoDB 저장 실패: {e}")
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/get_user_email/<user_id>', methods=['GET'])
def get_user_email(user_id):
    """
    사용자 이메일 주소 조회 API (MongoDB에서 조회)
    
    Returns:
        {
            "success": True,
            "email": "user@example.com" or ""
        }
    """
    if db_manager is None:
        return jsonify({
            "success": True,
            "email": ""
        })
    
    try:
        settings = db_manager.get_user_settings(user_id)
        email = settings.get("email", "")
        return jsonify({
            "success": True,
            "email": email
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update_user_email', methods=['POST'])
def update_user_email():
    """
    사용자 이메일 주소 업데이트 API (MongoDB에 저장)
    
    요청 형식:
    {
        "user_id": "user001",
        "email": "user@example.com"
    }
    """
    if db_manager is None:
        return jsonify({"error": "MongoDB가 연결되지 않았습니다."}), 500
    
    try:
        data = request.json
        user_id = data.get("user_id")
        email = data.get("email", "").strip()
        
        if not user_id:
            return jsonify({"error": "user_id가 필요합니다."}), 400
        
        if not email:
            return jsonify({"error": "email이 필요합니다."}), 400
        
        # MongoDB에 저장
        success = db_manager.save_user_settings(user_id, email=email)
        
        if success:
            # config에도 업데이트 (메모리 캐시)
            config.NOTIFICATION_CONFIG["user_emails"][user_id] = email
            print(f"사용자 {user_id}의 이메일 주소 저장 완료: {email}")
            
            return jsonify({
                "success": True,
                "message": "이메일 주소가 저장되었습니다.",
                "user_id": user_id,
                "email": email
            })
        else:
            return jsonify({"error": "이메일 주소 저장에 실패했습니다."}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_emergency_contacts/<user_id>', methods=['GET'])
def get_emergency_contacts(user_id):
    """
    사용자 긴급 연락망 조회 API (MongoDB에서 조회)
    
    Returns:
        {
            "success": True,
            "contacts": [{"name": "...", "email": "...", "phone": "..."}, ...]
        }
    """
    if db_manager is None:
        return jsonify({
            "success": True,
            "contacts": []
        })
    
    try:
        settings = db_manager.get_user_settings(user_id)
        contacts = settings.get("emergency_contacts", [])
        return jsonify({
            "success": True,
            "contacts": contacts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/update_emergency_contacts', methods=['POST'])
def update_emergency_contacts():
    """
    사용자 긴급 연락망 업데이트 API (MongoDB에 저장)
    
    요청 형식:
    {
        "user_id": "user001",
        "contacts": [
            {"name": "보호자1", "email": "guardian1@example.com", "phone": "010-1234-5678"},
            {"name": "보호자2", "email": "guardian2@example.com", "phone": "010-9876-5432"}
        ]
    }
    """
    if db_manager is None:
        return jsonify({"error": "MongoDB가 연결되지 않았습니다."}), 500
    
    try:
        data = request.json
        user_id = data.get("user_id")
        contacts = data.get("contacts", [])
        
        if not user_id:
            return jsonify({"error": "user_id가 필요합니다."}), 400
        
        # 입력 검증
        for contact in contacts:
            if not contact.get("name") or not contact.get("email"):
                return jsonify({"error": "이름과 이메일은 필수 항목입니다."}), 400
        
        # MongoDB에 저장
        success = db_manager.save_user_settings(user_id, emergency_contacts=contacts)
        
        if success:
            # config에도 업데이트 (메모리 캐시)
            config.NOTIFICATION_CONFIG["emergency_contacts"][user_id] = contacts
            print(f"사용자 {user_id}의 긴급 연락망 저장 완료: {len(contacts)}개 연락처")
            
            return jsonify({
                "success": True,
                "message": "긴급 연락망이 저장되었습니다.",
                "user_id": user_id,
                "contacts": contacts
            })
        else:
            return jsonify({"error": "긴급 연락망 저장에 실패했습니다."}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/send_emergency_alert', methods=['POST'])
def send_emergency_alert():
    """
    긴급 알림 수동 전송 API
    
    요청 형식:
    {
        "user_id": "user001"
    }
    """
    if notification_manager is None:
        return jsonify({"error": "알림 시스템이 초기화되지 않았습니다."}), 500
    
    try:
        data = request.json
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({"error": "user_id가 필요합니다."}), 400
        
        # 긴급 상황을 나타내는 높은 이상 점수로 설정
        emergency_anomaly_result = {
            "is_anomaly": True,
            "anomaly_score": 15.0,  # 매우 높은 점수로 설정하여 긴급 알림 발송
            "reconstruction_error": 0.5,
            "threshold": 0.01
        }
        
        # 사용자 데이터 (빈 데이터로 설정 - 긴급 상황)
        user_data = {
            "user_id": user_id,
            "sensor_data": [{
                "heart_rate": 0,
                "steps": 0,
                "sleep": 0,
                "temperature": 0
            }]
        }
        
        # 긴급 알림 전송 (비동기 처리 - Railway 네트워크 제한 대응)
        # Railway에서 SMTP 연결이 차단될 수 있으므로 비동기로 처리하고 즉시 응답 반환
        import threading
        def send_emergency_alert_async():
            try:
                success = notification_manager.send_emergency_alert(
                    user_id=user_id,
                    anomaly_result=emergency_anomaly_result,
                    user_data=user_data,
                    is_manual_emergency=True
                )
                if success:
                    print(f"[성공] 긴급 알림 발송 완료: {user_id}")
                else:
                    print(f"[실패] 긴급 알림 발송 실패: {user_id} (Railway 네트워크 제한 가능성)")
            except Exception as e:
                print(f"[오류] 긴급 알림 발송 중 예외 발생: {e}")
        
        # 백그라운드 스레드에서 긴급 알림 발송
        alert_thread = threading.Thread(target=send_emergency_alert_async, daemon=True)
        alert_thread.start()
        
        # Railway 네트워크 제한으로 인해 실패할 수 있지만, 사용자에게는 발송 시도 중임을 알림
        return jsonify({
            "success": True,
            "message": "긴급 알림 발송을 시도했습니다. (Railway 네트워크 제한으로 인해 실패할 수 있습니다)",
            "user_id": user_id,
            "note": "이메일 발송이 실패할 경우, 직접 연락하시거나 Railway의 네트워크 설정을 확인해주세요."
        })
        
    except Exception as e:
        import traceback
        import sys
        # 인코딩 오류 방지를 위해 에러 메시지를 안전하게 처리
        try:
            error_msg = str(e)
            print(f"긴급 알림 전송 오류: {error_msg}")
            traceback.print_exc()
        except UnicodeEncodeError:
            # 인코딩 오류 발생 시 ASCII로만 출력
            error_msg = repr(e)
            print(f"긴급 알림 전송 오류 (인코딩 문제): {error_msg}")
        
        # JSON 응답은 UTF-8이므로 안전
        safe_error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
        return jsonify({"error": f"긴급 알림 전송 중 오류가 발생했습니다: {safe_error_msg}"}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("웨어러블 이상행동 탐지 시스템 시작")
    print("=" * 50)
    
    # 모델 로드
    success, message = load_model()
    if not success:
        print(f"경고: {message}")
        print("모델 없이 서버를 시작합니다. 예측 기능은 사용할 수 없습니다.")
    else:
        print(f"[OK] {message}")
    
    # 서비스 초기화
    initialize_services()
    
    # 로컬 IP 주소 가져오기
    def get_local_ip():
        """로컬 네트워크 IP 주소 가져오기"""
        try:
            # 외부 서버에 연결하여 로컬 IP 확인
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"
    
    local_ip = get_local_ip()
    port = config.FLASK_CONFIG['port']
    
    print(f"\n{'='*50}")
    print("서버 시작 완료!")
    print(f"{'='*50}")
    print(f"로컬 접속: http://localhost:{port}")
    print(f"네트워크 접속: http://{local_ip}:{port}")
    print(f"{'='*50}")
    print("같은 네트워크의 다른 기기에서 위의 네트워크 접속 주소를 사용하세요.")
    print("Windows 방화벽이 차단하는 경우, 방화벽 설정에서 포트를 허용해주세요.")
    print(f"{'='*50}\n")
    
    try:
        app.run(
            host=config.FLASK_CONFIG['host'],
            port=config.FLASK_CONFIG['port'],
            debug=config.FLASK_CONFIG['debug'],
            use_reloader=config.FLASK_CONFIG.get('use_reloader', False)  # Windows 오류 방지
        )
    except KeyboardInterrupt:
        print("\n서버 종료 중...")
    finally:
        # 스케줄러 종료
        if health_scheduler:
            health_scheduler.stop()
        # MongoDB 연결 종료
        if db_manager:
            db_manager.disconnect()
        print("서버가 종료되었습니다.")

