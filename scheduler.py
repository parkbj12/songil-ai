"""
스케줄러 모듈
6시간마다 챗봇 알림 발송 및 8시간 무응답 감지
"""
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError as e:
    print(f"경고: apscheduler 모듈을 가져올 수 없습니다: {e}")
    print("pip install apscheduler를 실행하여 설치해주세요.")
    raise

from datetime import datetime, timedelta
from typing import Dict, Optional
import config


class HealthCheckScheduler:
    """건강 상태 체크 스케줄러"""
    
    def __init__(self, db_manager=None, chatbot=None, notification_manager=None):
        """
        Args:
            db_manager: MongoDBManager 인스턴스
            chatbot: HealthChatbot 인스턴스
            notification_manager: NotificationManager 인스턴스
        """
        self.db_manager = db_manager
        self.chatbot = chatbot
        self.notification_manager = notification_manager
        self.scheduler = BackgroundScheduler()
        self.user_responses = {}  # {user_id: last_response_time}
        
    def start(self):
        """스케줄러 시작"""
        # 운영 모드: 서버 시작 후 30분 뒤에 첫 알림, 그 다음부터 30분마다 챗봇 알림 발송
        self.scheduler.add_job(
            func=self.send_health_check_notifications,
            trigger=IntervalTrigger(minutes=30),
            id='health_check_notifications',
            name='30분마다 건강 상태 체크 알림',
            replace_existing=True,
            next_run_time=datetime.now() + timedelta(minutes=30)  # 서버 시작 후 30분 뒤에 첫 실행
        )
        
        # 운영 모드: 24시간마다 무응답 사용자 확인
        self.scheduler.add_job(
            func=self.check_no_response_users,
            trigger=IntervalTrigger(hours=24),
            id='check_no_response',
            name='24시간마다 무응답 사용자 확인',
            replace_existing=True
        )
        
        self.scheduler.start()
        print("건강 상태 체크 스케줄러가 시작되었습니다.")
        print("- 서버 시작 후 30분 뒤에 첫 알림 발송, 그 다음부터 30분마다 챗봇 알림 발송")
        print("- 24시간마다 무응답 사용자 확인 (5분 이상 무응답 시 이메일 발송)")
    
    def stop(self):
        """스케줄러 중지"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("건강 상태 체크 스케줄러가 중지되었습니다.")
    
    def update_user_response(self, user_id: str):
        """사용자 응답 시간 업데이트"""
        self.user_responses[user_id] = datetime.now()
        print(f"사용자 {user_id}의 응답 시간이 업데이트되었습니다: {self.user_responses[user_id]}")
    
    def get_last_response_time(self, user_id: str) -> Optional[datetime]:
        """사용자의 마지막 응답 시간 조회"""
        return self.user_responses.get(user_id)
    
    def send_health_check_notifications(self):
        """30분마다 건강 상태 체크 알림 발송"""
        if not self.chatbot or not self.db_manager:
            print("챗봇 또는 DB 매니저가 초기화되지 않았습니다.")
            return
        
        print(f"[{datetime.now()}] 건강 상태 체크 알림 발송 시작...")
        
        # 활성 사용자 목록 가져오기
        try:
            # 최근 30일 내 데이터가 있는 사용자
            pipeline = [
                {
                    "$match": {
                        "timestamp": {
                            "$gte": datetime.now() - timedelta(days=30)
                        }
                    }
                },
                {
                    "$group": {
                        "_id": "$user_id",
                        "last_activity": {"$max": "$timestamp"}
                    }
                }
            ]
            
            active_users = list(self.db_manager.collection.aggregate(pipeline))
            
            # 활성 사용자가 없으면 알림 발송하지 않음
            if not active_users:
                print("활성 사용자가 없습니다. 알림을 발송하지 않습니다.")
                return
            
            for user_info in active_users:
                user_id = user_info["_id"]
                
                # 챗봇 알림 메시지 생성
                notification_message = self._create_health_check_message(user_id)
                
                # MongoDB에 알림 저장
                if self.db_manager:
                    try:
                        self.db_manager.save_notification(
                            user_id=user_id,
                            notification_type="health_check",
                            message=notification_message,
                            status="pending"
                        )
                        print(f"사용자 {user_id}에게 건강 상태 체크 알림 저장: {notification_message}")
                    except Exception as e:
                        print(f"알림 저장 실패 ({user_id}): {e}")
                
                # 응답 시간 초기화 (알림 발송 시점)
                # 실제로는 사용자가 응답할 때까지 기다림
                if user_id not in self.user_responses:
                    self.user_responses[user_id] = None  # 아직 응답 없음
                
        except Exception as e:
            print(f"건강 상태 체크 알림 발송 실패: {e}")
    
    def _create_health_check_message(self, user_id: str) -> str:
        """건강 상태 체크 메시지 생성"""
        messages = [
            "안녕하세요! 건강 상태를 확인하고 싶습니다. 오늘 컨디션은 어떠신가요?",
            "건강 상태 체크 시간입니다. 오늘 하루는 어떠셨나요?",
            "안녕하세요! 오늘 건강 상태는 어떤가요? 괜찮으시다면 간단히 답변해주세요.",
            "건강 상태 확인 알림입니다. 오늘 컨디션을 알려주세요.",
            "안녕하세요! 오늘 하루 건강하게 보내셨나요? 상태를 알려주시면 감사하겠습니다."
        ]
        
        import random
        base_message = random.choice(messages)
        
        # 사용자 통계 정보 추가
        if self.db_manager:
            try:
                stats = self.db_manager.get_statistics(user_id)
                if stats.get("total_logs", 0) > 0:
                    base_message += f"\n\n최근 활동: 총 {stats['total_logs']}회 기록, 이상 탐지 {stats['anomaly_count']}회"
            except:
                pass
        
        return base_message
    
    def check_no_response_users(self):
        """5분 이상 응답이 없는 사용자 확인 및 이메일 발송"""
        if not self.notification_manager or not self.db_manager:
            return
        
        print(f"[{datetime.now()}] 무응답 사용자 확인 중...")
        
        current_time = datetime.now()
        # 운영 모드: 5분 이상 무응답 시 이메일 발송
        no_response_threshold = timedelta(minutes=5)
        
        # MongoDB에서 최근 건강 체크 알림 조회
        try:
            notification_collection = self.db_manager.db.get_collection("notifications")
            
            # 최근 1시간 내 발송된 건강 체크 알림 조회
            recent_notifications = notification_collection.find({
                "notification_type": "health_check",
                "created_at": {
                    "$gte": current_time - timedelta(hours=1)
                },
                "status": {"$in": ["pending", "read"]}  # 응답하지 않은 알림만
            })
            
            for notif in recent_notifications:
                user_id = notif["user_id"]
                created_at = notif["created_at"]
                time_since_notification = current_time - created_at
                
                # 5분 이상 응답이 없으면
                if time_since_notification >= no_response_threshold:
                    # 이미 이메일을 보냈는지 확인 (중복 방지)
                    existing_email = notification_collection.find_one({
                        "user_id": user_id,
                        "notification_type": "no_response_email",
                        "created_at": {
                            "$gte": created_at  # 같은 건강 체크 알림에 대한 이메일
                        }
                    })
                    
                    if not existing_email:
                        print(f"경고: 사용자 {user_id}가 {time_since_notification} 동안 응답이 없습니다.")
                        
                        # 이메일 알림 발송
                        self._send_no_response_email(user_id, time_since_notification, notif.get("_id"))
        
        except Exception as e:
            print(f"무응답 사용자 확인 실패: {e}")
        
        # 메모리 기반 확인 (백업)
        for user_id, last_response_time in self.user_responses.items():
            if last_response_time is None:
                continue
            
            time_since_response = current_time - last_response_time
            
            if time_since_response >= no_response_threshold:
                print(f"경고: 사용자 {user_id}가 {time_since_response} 동안 응답이 없습니다 (메모리 기반 확인).")
    
    def _send_no_response_email(self, user_id: str, time_since_response: timedelta, 
                                health_check_notification_id=None):
        """무응답 사용자에게 이메일 알림 발송"""
        try:
            hours = int(time_since_response.total_seconds() / 3600)
            
            # MongoDB에 이메일 알림 기록 저장
            if self.db_manager and health_check_notification_id:
                try:
                    self.db_manager.save_notification(
                        user_id=user_id,
                        notification_type="no_response_email",
                        message=f"건강 상태 체크 알림 발송 후 {hours}시간 동안 응답이 없습니다.",
                        status="sent"
                    )
                except Exception as e:
                    print(f"이메일 알림 기록 저장 실패: {e}")
            
            # 이메일 내용 생성
            subject = f"🚨 건강 상태 확인 요청 - {user_id}님"
            body = f"""
건강 상태 확인 요청

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 건강 상태 확인 알림
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{user_id}님께 알려드립니다.

건강 상태 체크 알림 발송 후 {hours}시간이 지났지만 응답이 없습니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 확인 요청
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 웹 대시보드에 접속하여 건강 상태를 입력해주세요
2. 챗봇에 간단히 응답해주세요 (예: "괜찮습니다", "좋습니다")
3. 이상이 있으시면 즉시 연락주세요

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
본 알림은 건강 상태 모니터링 시스템에서 자동으로 발송되었습니다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # 챗봇 메시지로도 알림 표시 (이메일 발송 전에 먼저 저장)
            email_sent = False
            if self.db_manager:
                try:
                    minutes = int(time_since_response.total_seconds() / 60)
                    chatbot_message = f"⚠️ 응답이 없어서 이메일 알림을 발송했습니다.\n\n건강 상태 체크 알림 발송 후 {minutes}분 동안 응답이 없어 이메일로 알림을 보냈습니다. 건강 상태를 확인해주세요."
                    
                    self.db_manager.save_notification(
                        user_id=user_id,
                        notification_type="no_response_chatbot",
                        message=chatbot_message,
                        status="pending"
                    )
                    print(f"챗봇 알림 메시지 저장 완료: {user_id}")
                except Exception as e:
                    print(f"챗봇 알림 메시지 저장 실패: {e}")
            
            # 사용자 이메일 주소 가져오기
            user_email = self.notification_manager._get_user_email(user_id)
            
            if not user_email:
                print(f"경고: 사용자 {user_id}의 이메일 주소를 찾을 수 없습니다. 챗봇 알림만 발송되었습니다.")
                return
            
            # 이메일 발송
            try:
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                import smtplib
                import ssl
                
                msg = MIMEMultipart()
                msg['From'] = self.notification_manager.sender_email
                msg['To'] = user_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
                
                # SMTP 서버 설정에 따라 TLS 또는 SSL 사용
                if self.notification_manager.smtp_port == 465:
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(
                        self.notification_manager.smtp_server,
                        self.notification_manager.smtp_port,
                        context=context
                    ) as server:
                        server.login(
                            self.notification_manager.sender_email,
                            self.notification_manager.sender_password
                        )
                        server.send_message(msg)
                else:
                    with smtplib.SMTP(
                        self.notification_manager.smtp_server,
                        self.notification_manager.smtp_port
                    ) as server:
                        server.starttls()
                        server.login(
                            self.notification_manager.sender_email,
                            self.notification_manager.sender_password
                        )
                        server.send_message(msg)
                
                print(f"무응답 알림 이메일 발송 완료: {user_id} ({user_email})")
                email_sent = True
            except Exception as email_error:
                print(f"이메일 발송 실패 ({user_id}): {email_error}. 챗봇 알림은 이미 저장되었습니다.")
            
        except Exception as e:
            print(f"무응답 알림 이메일 발송 실패 ({user_id}): {e}")

