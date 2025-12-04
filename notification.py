"""
알림 시스템 모듈
이상 탐지 시 이메일, 웹 알림 등을 발송
"""
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import json
from typing import Dict, List, Optional
import config


class NotificationManager:
    """알림 관리 클래스"""
    
    def __init__(self, db_manager=None, chatbot=None):
        """
        알림 시스템 초기화
        
        Args:
            db_manager: MongoDBManager 인스턴스 (선택)
            chatbot: HealthChatbot 인스턴스 (선택, 개인화된 권장 조치 생성용)
        """
        self.db_manager = db_manager
        self.chatbot = chatbot
        self.email_enabled = config.NOTIFICATION_CONFIG.get("email_enabled", False)
        self.smtp_server = config.NOTIFICATION_CONFIG.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = config.NOTIFICATION_CONFIG.get("smtp_port", 587)
        self.sender_email = config.NOTIFICATION_CONFIG.get("sender_email", "")
        self.sender_password = config.NOTIFICATION_CONFIG.get("sender_password", "")
        
        # 알림 레벨 설정
        self.alert_levels = config.NOTIFICATION_CONFIG.get("alert_levels", {
            "low": 1.0,      # 낮은 이상 점수
            "medium": 2.0,   # 중간 이상 점수
            "high": 5.0,    # 높은 이상 점수
            "critical": 10.0  # 심각한 이상 점수
        })
        
        # 사용자별 긴급 연락망 (MongoDB에서 로드하거나 설정 파일에서)
        self.emergency_contacts = {}
    
    def send_email_alert(self, user_id: str, anomaly_result: Dict, 
                        user_data: Dict = None) -> bool:
        """
        이메일 알림 발송
        
        Args:
            user_id: 사용자 ID
            anomaly_result: 이상 탐지 결과
            user_data: 사용자 데이터 (선택)
            
        Returns:
            발송 성공 여부
        """
        if not self.email_enabled or not self.sender_email:
            return False
        
        try:
            # 수신자 이메일 가져오기 (사용자 설정 또는 기본값)
            recipient_email = self._get_user_email(user_id)
            if not recipient_email:
                print(f"경고: 사용자 {user_id}의 이메일 주소를 찾을 수 없습니다.")
                return False
            
            # 알림 레벨 결정
            alert_level = self._determine_alert_level(anomaly_result["anomaly_score"])
            
            # 이메일 내용 생성
            subject, body = self._create_email_content(
                user_id, anomaly_result, alert_level, user_data
            )
            
            # 이메일 발송
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # 포트에 따라 TLS 또는 SSL 사용
            if self.smtp_port == 465:
                # SSL 사용 (네이버 메일 465 포트)
                # 타임아웃 설정 (10초) - Railway 네트워크 지연 대응
                import ssl
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context, timeout=10) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
            else:
                # TLS 사용 (587 포트, 네이버 메일 기본)
                # 타임아웃 설정 (10초) - Railway 네트워크 지연 대응
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
            
            print(f"이메일 알림 발송 완료: {recipient_email}")
            return True
            
        except Exception as e:
            print(f"이메일 알림 발송 실패: {str(e)}")
            return False
    
    def send_emergency_alert(self, user_id: str, anomaly_result: Dict,
                            user_data: Dict = None, is_manual_emergency: bool = False) -> bool:
        """
        긴급 상황 알림 발송 (보호자/긴급 연락망)
        
        Args:
            user_id: 사용자 ID
            anomaly_result: 이상 탐지 결과
            user_data: 사용자 데이터 (선택)
            is_manual_emergency: 수동 응급 연락 여부 (True면 이상 탐지 결과 섹션 제외)
            
        Returns:
            발송 성공 여부
        """
        # 이메일 기능 활성화 확인
        if not self.email_enabled:
            print(f"경고: 이메일 알림이 비활성화되어 있습니다. 긴급 알림을 발송할 수 없습니다.")
            return False
        
        # 발신자 이메일 설정 확인
        if not self.sender_email or not self.sender_password:
            print(f"경고: 발신자 이메일 또는 비밀번호가 설정되지 않았습니다. 긴급 알림을 발송할 수 없습니다.")
            print(f"  - sender_email: {'설정됨' if self.sender_email else '미설정'}")
            print(f"  - sender_password: {'설정됨' if self.sender_password else '미설정'}")
            return False
        
        # 긴급 연락망 가져오기
        emergency_contacts = self._get_emergency_contacts(user_id)
        if not emergency_contacts:
            print(f"경고: 사용자 {user_id}의 긴급 연락망이 설정되지 않았습니다.")
            return False
        
        print(f"[긴급 알림] 사용자 {user_id}의 긴급 연락망 {len(emergency_contacts)}개 발견")
        
        success_count = 0
        for contact in emergency_contacts:
            try:
                contact_email = contact.get("email", "")
                contact_name = contact.get("name", "보호자")
                
                if not contact_email:
                    print(f"경고: 연락처 '{contact_name}'의 이메일 주소가 없습니다.")
                    continue
                
                print(f"[긴급 알림] {contact_name} ({contact_email})에게 이메일 발송 시도...")
                
                # 긴급 알림 이메일 생성
                if is_manual_emergency:
                    subject = f"긴급 알림: {user_id}님의 응급 상황"
                else:
                    subject = f"긴급 알림: {user_id}님의 건강 이상 징후 감지"
                body = self._create_emergency_email_content(
                    user_id, anomaly_result, contact_name, user_data, is_manual_emergency
                )
                
                msg = MIMEMultipart()
                msg['From'] = self.sender_email
                msg['To'] = contact_email
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'html', 'utf-8'))
                
                # 포트에 따라 TLS 또는 SSL 사용
                if self.smtp_port == 465:
                    # SSL 사용 (네이버 메일 465 포트)
                    # 타임아웃 설정 (10초) - Railway 네트워크 지연 대응
                    import ssl
                    context = ssl.create_default_context()
                    print(f"[긴급 알림] SSL 연결 시도: {self.smtp_server}:{self.smtp_port}")
                    with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context, timeout=10) as server:
                        print(f"[긴급 알림] SMTP 서버 로그인 시도...")
                        server.login(self.sender_email, self.sender_password)
                        print(f"[긴급 알림] 이메일 전송 시도...")
                        server.send_message(msg)
                else:
                    # TLS 사용 (587 포트, 네이버 메일 기본)
                    # 타임아웃 설정 (10초) - Railway 네트워크 지연 대응
                    print(f"[긴급 알림] TLS 연결 시도: {self.smtp_server}:{self.smtp_port}")
                    with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                        print(f"[긴급 알림] TLS 시작...")
                        server.starttls()
                        print(f"[긴급 알림] SMTP 서버 로그인 시도...")
                        server.login(self.sender_email, self.sender_password)
                        print(f"[긴급 알림] 이메일 전송 시도...")
                        server.send_message(msg)
                
                success_count += 1
                # Windows 인코딩 오류 방지를 위해 이모지 제거
                print(f"[성공] 긴급 알림 발송 완료: {contact_name} ({contact_email})")
                
            except smtplib.SMTPAuthenticationError as e:
                error_msg = f"SMTP 인증 실패: {str(e)}"
                print(f"[실패] 긴급 알림 발송 실패 ({contact_name}): {error_msg}")
                print(f"   발신자 이메일: {self.sender_email}")
                print(f"   SMTP 서버: {self.smtp_server}:{self.smtp_port}")
                print(f"   확인 사항: 이메일 주소와 비밀번호(또는 앱 비밀번호)가 올바른지 확인하세요.")
            except smtplib.SMTPException as e:
                error_msg = f"SMTP 오류: {str(e)}"
                print(f"[실패] 긴급 알림 발송 실패 ({contact_name}): {error_msg}")
                print(f"   SMTP 서버: {self.smtp_server}:{self.smtp_port}")
            except (TimeoutError, socket.timeout, OSError) as e:
                error_msg = f"SMTP 연결 타임아웃 또는 네트워크 오류: {str(e)}"
                print(f"[실패] 긴급 알림 발송 실패 ({contact_name}): {error_msg}")
                print(f"   원인: Railway에서 SMTP 서버({self.smtp_server})로의 연결이 차단되거나 지연되고 있습니다.")
                print(f"   해결 방법:")
                print(f"   1. Gmail SMTP 사용 권장 (smtp.gmail.com:587)")
                print(f"   2. 네이버 메일의 경우 네트워크 방화벽 설정 확인")
                print(f"   3. Railway의 네트워크 정책 확인")
            except Exception as e:
                import traceback
                error_msg = f"예상치 못한 오류: {str(e)}"
                print(f"[실패] 긴급 알림 발송 실패 ({contact_name}): {error_msg}")
                print(f"   상세 오류:")
                try:
                    traceback.print_exc()
                except UnicodeEncodeError:
                    # 인코딩 오류 발생 시 간단한 메시지만 출력
                    print(f"   (상세 오류 정보는 인코딩 문제로 출력할 수 없습니다)")
        
        if success_count > 0:
            print(f"[완료] 총 {success_count}개의 긴급 알림이 성공적으로 발송되었습니다.")
        else:
            print(f"[실패] 모든 긴급 알림 발송이 실패했습니다.")
        
        return success_count > 0
    
    def send_alert(self, user_id: str, anomaly_result: Dict,
                   user_data: Dict = None) -> Dict:
        """
        이상 탐지 시 알림 발송 (자동 레벨 결정)
        
        Args:
            user_id: 사용자 ID
            anomaly_result: 이상 탐지 결과
            user_data: 사용자 데이터 (선택)
            
        Returns:
            알림 발송 결과
        """
        if not anomaly_result.get("is_anomaly", False):
            return {"sent": False, "reason": "정상 범위"}
        
        alert_level = self._determine_alert_level(anomaly_result["anomaly_score"])
        result = {
            "sent": False,
            "alert_level": alert_level,
            "email_sent": False,
            "emergency_sent": False
        }
        
        # 일반 알림 (중간 이상)
        if alert_level in ["medium", "high", "critical"]:
            result["email_sent"] = self.send_email_alert(
                user_id, anomaly_result, user_data
            )
            result["sent"] = result["email_sent"]
        
        # 긴급 알림 (높은 이상 점수)
        if alert_level in ["high", "critical"]:
            result["emergency_sent"] = self.send_emergency_alert(
                user_id, anomaly_result, user_data
            )
            if result["emergency_sent"]:
                result["sent"] = True
        
        return result
    
    def _determine_alert_level(self, anomaly_score: float) -> str:
        """
        이상 점수에 따른 알림 레벨 결정
        
        Args:
            anomaly_score: 이상 점수
            
        Returns:
            알림 레벨: "low", "medium", "high", "critical"
        """
        if anomaly_score >= self.alert_levels["critical"]:
            return "critical"
        elif anomaly_score >= self.alert_levels["high"]:
            return "high"
        elif anomaly_score >= self.alert_levels["medium"]:
            return "medium"
        else:
            return "low"
    
    def _create_email_content(self, user_id: str, anomaly_result: Dict,
                              alert_level: str, user_data: Dict = None) -> tuple:
        """
        이메일 내용 생성 (HTML 형식)
        
        Returns:
            (subject, body) 튜플
        """
        anomaly_score = anomaly_result.get("anomaly_score", 0)
        is_anomaly = anomaly_result.get("is_anomaly", False)
        reconstruction_error = anomaly_result.get("reconstruction_error", 0)
        detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 제목
        level_emoji = {
            "low": "⚠️",
            "medium": "🔶",
            "high": "🔴",
            "critical": "🚨"
        }
        emoji = level_emoji.get(alert_level, "⚠️")
        subject = f"{emoji} 건강 이상 징후 감지 알림 - {user_id}"
        
        # 알림 레벨 한글 변환
        level_korean = {
            "low": "낮음",
            "medium": "중간",
            "high": "높음",
            "critical": "심각"
        }
        alert_level_korean = level_korean.get(alert_level, alert_level)
        
        # 알림 레벨에 따른 색상 및 스타일
        level_colors = {
            "low": {"bg": "#fef3c7", "border": "#f59e0b", "text": "#92400e", "header": "#fbbf24"},
            "medium": {"bg": "#fed7aa", "border": "#ea580c", "text": "#9a3412", "header": "#fb923c"},
            "high": {"bg": "#fee2e2", "border": "#ef4444", "text": "#991b1b", "header": "#f87171"},
            "critical": {"bg": "#fecaca", "border": "#dc2626", "text": "#7f1d1d", "header": "#ef4444"}
        }
        colors = level_colors.get(alert_level, level_colors["medium"])
        
        # 권장 조치 내용 (AI 기반 개인화된 권장 조치 생성)
        actions = []
        if self.chatbot and user_data:
            try:
                # 챗봇을 사용하여 사용자 데이터 기반 개인화된 피드백 생성
                feedback = self.chatbot.generate_feedback(anomaly_result, user_data)
                # 피드백을 권장 조치 리스트로 변환
                feedback_lines = feedback.split('\n')
                for line in feedback_lines:
                    line = line.strip()
                    if line and not line.startswith('✅') and not line.startswith('⚠️') and not line.startswith('🚨') and not line.startswith('💡'):
                        # 이모지 제거 및 정리
                        clean_line = line
                        for emoji in ['🚨', '⚠️', '💡', '✅', '🏥', '🏠', '📊', '❤️', '👣', '😴', '🌡️']:
                            clean_line = clean_line.replace(emoji, '').strip()
                        if clean_line and len(clean_line) > 5:
                            # 번호나 불릿 제거
                            clean_line = clean_line.lstrip('0123456789.-) ').strip()
                            if clean_line:
                                actions.append(clean_line)
            except Exception as e:
                print(f"챗봇 피드백 생성 실패, 기본 권장 조치 사용: {e}")
        
        # 챗봇 피드백이 없거나 실패한 경우 기본 권장 조치 사용
        if not actions:
            if alert_level == "critical":
                actions = [
                    "즉시 건강 상태를 확인하세요",
                    "필요시 의료진과 상담하거나 응급실을 방문하세요",
                    "보호자나 가족에게 연락하세요"
                ]
            elif alert_level == "high":
                actions = [
                    "건강 상태를 주의 깊게 관찰하세요",
                    "정기적인 건강검진을 받으시기 바랍니다",
                    "가벼운 활동을 권장합니다"
                ]
            elif alert_level == "medium":
                actions = [
                    "건강 상태를 모니터링하세요",
                    "평소와 다른 증상이 있으면 의료진과 상담하세요"
                ]
            else:
                actions = [
                    "가벼운 활동 변화를 권장합니다",
                    "건강 상태를 계속 모니터링하세요"
                ]
        
        # 최대 5개까지만 표시
        actions = actions[:5]
        
        # 최근 건강 데이터 HTML
        health_data_html = ""
        if user_data and user_data.get("sensor_data"):
            sensor_data = user_data["sensor_data"]
            if isinstance(sensor_data, list) and len(sensor_data) > 0:
                latest = sensor_data[-1]
                health_data_html = """
        <div style="padding: 30px 20px; background-color: #ffffff;">
            <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-left: 5px solid #0ea5e9; padding: 20px; border-radius: 8px;">
                <h2 style="color: #0c4a6e; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">
                    📈 최근 건강 데이터
                </h2>
                <table style="width: 100%; border-collapse: collapse;">
"""
                if "heart_rate" in latest:
                    health_data_html += f"""
                    <tr>
                        <td style="padding: 8px 0; color: #666666; font-size: 14px; width: 120px;">❤️ 심박수:</td>
                        <td style="padding: 8px 0; color: #333333; font-size: 16px; font-weight: 600;">{latest.get('heart_rate', 'N/A')} bpm</td>
                    </tr>
"""
                if "steps" in latest:
                    health_data_html += f"""
                    <tr>
                        <td style="padding: 8px 0; color: #666666; font-size: 14px;">👣 걸음수:</td>
                        <td style="padding: 8px 0; color: #333333; font-size: 16px; font-weight: 600;">{latest.get('steps', 'N/A')} 걸음</td>
                    </tr>
"""
                if "sleep" in latest:
                    health_data_html += f"""
                    <tr>
                        <td style="padding: 8px 0; color: #666666; font-size: 14px;">😴 수면 시간:</td>
                        <td style="padding: 8px 0; color: #333333; font-size: 16px; font-weight: 600;">{latest.get('sleep', 'N/A')} 시간</td>
                    </tr>
"""
                if "temperature" in latest:
                    health_data_html += f"""
                    <tr>
                        <td style="padding: 8px 0; color: #666666; font-size: 14px;">🌡️ 체온:</td>
                        <td style="padding: 8px 0; color: #333333; font-size: 16px; font-weight: 600;">{latest.get('temperature', 'N/A')} °C</td>
                    </tr>
"""
                health_data_html += """
                </table>
            </div>
        </div>
"""
        
        # HTML 본문
        body = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', '맑은 고딕', Arial, sans-serif; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        <!-- 헤더 -->
        <div style="background: linear-gradient(135deg, {colors['header']} 0%, {colors['border']} 100%); padding: 30px 20px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">
                {emoji} 건강 이상 징후 감지 알림
            </h1>
        </div>
        
        <!-- 이상 탐지 결과 -->
        <div style="padding: 30px 20px; background-color: #ffffff;">
            <div style="background: linear-gradient(135deg, {colors['bg']} 0%, {colors['bg']} 100%); border-left: 5px solid {colors['border']}; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: {colors['text']}; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">
                    📊 이상 탐지 결과
                </h2>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px; width: 120px;">사용자 ID:</td>
                        <td style="padding: 10px 0; color: #333333; font-size: 16px; font-weight: 600;">{user_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">감지 시간:</td>
                        <td style="padding: 10px 0; color: #333333; font-size: 16px;">{detection_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">알림 레벨:</td>
                        <td style="padding: 10px 0;">
                            <span style="color: {colors['border']}; font-size: 16px; font-weight: 700;">{alert_level_korean}</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">이상 점수:</td>
                        <td style="padding: 10px 0;">
                            <span style="color: {colors['border']}; font-size: 20px; font-weight: 700;">{anomaly_score:.3f}</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">재구성 오차:</td>
                        <td style="padding: 10px 0; color: #333333; font-size: 16px;">{reconstruction_error:.4f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">이상 여부:</td>
                        <td style="padding: 10px 0;">
                            <span style="color: {'#dc2626' if is_anomaly else '#10b981'}; font-size: 16px; font-weight: 600;">
                                {'⚠️ 감지됨' if is_anomaly else '✅ 정상'}
                            </span>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        
        {health_data_html}
        
        <!-- 권장 조치 -->
        <div style="padding: 30px 20px; background-color: #ffffff;">
            <div style="background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-left: 5px solid #10b981; padding: 20px; border-radius: 8px;">
                <h2 style="color: #166534; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">
                    💡 권장 조치
                </h2>
"""
        
        for i, action in enumerate(actions, 1):
            body += f"""
                <div style="background-color: #ffffff; padding: 15px; border-radius: 6px; margin-bottom: 10px;">
                    <p style="color: #333333; margin: 0; font-size: 15px; line-height: 1.8;">
                        <span style="color: #10b981; font-weight: 700; font-size: 18px;">{i}.</span> {action}
                    </p>
                </div>
"""
        
        body += """
            </div>
        </div>
        
        <!-- 푸터 -->
        <div style="padding: 20px; background-color: #f9fafb; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="color: #6b7280; margin: 0; font-size: 12px; line-height: 1.6;">
                본 알림은 AI 기반 건강 이상 탐지 시스템에서 자동으로 발송되었습니다.<br>
                더 자세한 정보는 웹 대시보드에서 확인하실 수 있습니다.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return subject, body
    
    def _create_emergency_email_content(self, user_id: str, anomaly_result: Dict,
                                       contact_name: str, user_data: Dict = None, 
                                       is_manual_emergency: bool = False) -> str:
        """
        긴급 알림 이메일 내용 생성 (HTML 형식)
        
        Args:
            is_manual_emergency: 수동 응급 연락 여부 (True면 이상 탐지 결과 섹션 제외)
        """
        detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_body = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Malgun Gothic', '맑은 고딕', Arial, sans-serif; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        <!-- 헤더 -->
        <div style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); padding: 30px 20px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">
                긴급 상황 알림
            </h1>
        </div>
        
        <!-- 인사말 -->
        <div style="padding: 30px 20px; background-color: #ffffff; border-bottom: 2px solid #f0f0f0;">
            <p style="font-size: 18px; color: #333333; margin: 0; line-height: 1.6;">
                <strong>{contact_name}님</strong>께 알려드립니다.
            </p>
        </div>
"""
        
        # 수동 응급 연락이 아닌 경우에만 이상 탐지 결과 표시
        if not is_manual_emergency:
            anomaly_score = anomaly_result.get("anomaly_score", 0)
            reconstruction_error = anomaly_result.get('reconstruction_error', 0)
            
            # 이상 점수에 따른 색상 결정
            if anomaly_score >= 10.0:
                score_color = "#dc2626"  # 빨강
                severity_text = "매우 심각"
            elif anomaly_score >= 5.0:
                score_color = "#ea580c"  # 주황
                severity_text = "심각"
            else:
                score_color = "#f59e0b"  # 노랑
                severity_text = "주의"
            
            html_body += f"""
        <!-- 이상 탐지 결과 -->
        <div style="padding: 30px 20px; background-color: #ffffff;">
            <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border-left: 5px solid #ef4444; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #991b1b; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">
                    이상 탐지 결과
                </h2>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px; width: 120px;">사용자:</td>
                        <td style="padding: 10px 0; color: #333333; font-size: 16px; font-weight: 600;">{user_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">감지 시간:</td>
                        <td style="padding: 10px 0; color: #333333; font-size: 16px;">{detection_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">이상 점수:</td>
                        <td style="padding: 10px 0;">
                            <span style="color: {score_color}; font-size: 20px; font-weight: 700;">{anomaly_score:.3f}</span>
                            <span style="color: #666666; font-size: 14px; margin-left: 8px;">({severity_text} 수준)</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #666666; font-size: 14px;">재구성 오차:</td>
                        <td style="padding: 10px 0; color: #333333; font-size: 16px;">{reconstruction_error:.4f}</td>
                    </tr>
                </table>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #ffffff; border-radius: 6px; border: 2px solid #fca5a5;">
                    <p style="color: #991b1b; margin: 0; font-size: 16px; font-weight: 600; text-align: center;">
                        심각한 건강 이상 징후가 감지되었습니다.
                    </p>
                </div>
            </div>
        </div>
"""
        else:
            # 수동 응급 연락인 경우 간단한 응급 상황 알림만 표시
            html_body += f"""
        <!-- 응급 상황 알림 -->
        <div style="padding: 30px 20px; background-color: #ffffff;">
            <div style="background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); border-left: 5px solid #ef4444; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                <h2 style="color: #991b1b; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">
                    응급 상황
                </h2>
                
                <div style="padding: 20px; background-color: #ffffff; border-radius: 6px; border: 2px solid #fca5a5;">
                    <p style="color: #991b1b; margin: 0 0 15px 0; font-size: 18px; font-weight: 700; text-align: center;">
                        {user_id}님이 응급 상황을 신고하셨습니다.
                    </p>
                    <p style="color: #666666; margin: 15px 0 0 0; font-size: 14px; text-align: center;">
                        신고 시간: {detection_time}
                    </p>
                </div>
            </div>
        </div>
"""
        
        html_body += """
        <!-- 즉시 조치 필요 (AI 기반 개인화된 권장 조치) -->
        <div style="padding: 30px 20px; background-color: #ffffff;">
            <div style="background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%); border-left: 5px solid #f59e0b; padding: 20px; border-radius: 8px;">
                <h2 style="color: #92400e; margin: 0 0 20px 0; font-size: 20px; font-weight: 600;">
                    즉시 조치 필요
                </h2>
"""
        
        # 응급 조치 생성
        if is_manual_emergency:
            # 수동 응급 연락인 경우 간단한 응급 조치만 표시
            emergency_actions = [
                "사용자의 현재 상태를 즉시 확인하세요",
                "필요시 즉시 119(응급실)에 연락하거나 응급실을 방문하세요",
                "사용자와 직접 연락하여 안전을 확인하세요",
                "주변 사람에게 도움을 요청하세요"
            ]
        else:
            # AI 기반 개인화된 권장 조치 생성 (자동 이상 탐지인 경우)
            emergency_actions = []
            if self.chatbot and user_data:
                try:
                    # 챗봇을 사용하여 사용자 데이터 기반 개인화된 피드백 생성
                    feedback = self.chatbot.generate_feedback(anomaly_result, user_data)
                    # 피드백을 권장 조치 리스트로 변환
                    feedback_lines = feedback.split('\n')
                    for line in feedback_lines:
                        line = line.strip()
                        if line and ('조치' in line or '권장' in line or '제안' in line or '상담' in line or '의료' in line or '응급' in line or '확인' in line):
                            # 이모지 제거 및 정리
                            clean_line = line
                            for emoji in ['🚨', '⚠️', '💡', '✅', '🏥', '🏠', '📊', '❤️', '👣', '😴', '🌡️']:
                                clean_line = clean_line.replace(emoji, '').strip()
                            if clean_line and len(clean_line) > 5:
                                # 번호나 불릿 제거
                                clean_line = clean_line.lstrip('0123456789.-) ').strip()
                                if clean_line:
                                    emergency_actions.append(clean_line)
                except Exception as e:
                    print(f"챗봇 피드백 생성 실패, 기본 권장 조치 사용: {e}")
            
            # 기본 권장 조치 (챗봇 피드백이 없거나 실패한 경우)
            if not emergency_actions:
                emergency_actions = [
                    "사용자의 현재 상태를 확인하세요",
                    "필요시 즉시 의료진과 상담하거나 응급실을 방문하세요",
                    "사용자와 직접 연락하여 안전을 확인하세요"
                ]
        
        # 최대 5개까지만 표시
        emergency_actions = emergency_actions[:5]
        
        for i, action in enumerate(emergency_actions, 1):
            html_body += f"""
                <div style="background-color: #ffffff; padding: 15px; border-radius: 6px; margin-bottom: 10px;">
                    <p style="color: #333333; margin: 0; font-size: 15px; line-height: 1.8;">
                        <span style="color: #f59e0b; font-weight: 700; font-size: 18px;">{i}.</span> {action}
                    </p>
                </div>
"""
        
        html_body += """
            </div>
        </div>
        
        <!-- 푸터 -->
        <div style="padding: 20px; background-color: #f9fafb; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="color: #6b7280; margin: 0; font-size: 12px; line-height: 1.6;">
                본 알림은 AI 기반 건강 이상 탐지 시스템에서 자동으로 발송되었습니다.<br>
                더 자세한 정보는 웹 대시보드에서 확인하실 수 있습니다.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return html_body
    
    def _get_user_email(self, user_id: str) -> Optional[str]:
        """
        사용자 이메일 주소 가져오기 (MongoDB 우선, 없으면 config에서)
        """
        # MongoDB에서 먼저 조회
        if self.db_manager:
            try:
                settings = self.db_manager.get_user_settings(user_id)
                email = settings.get("email", "")
                if email:
                    return email
            except Exception as e:
                print(f"MongoDB에서 이메일 조회 실패: {e}")
        
        # MongoDB에 없으면 config에서 가져오기
        user_emails = config.NOTIFICATION_CONFIG.get("user_emails", {})
        return user_emails.get(user_id, os.getenv(f"USER_{user_id}_EMAIL", ""))
    
    def _get_emergency_contacts(self, user_id: str) -> List[Dict]:
        """
        긴급 연락망 가져오기 (MongoDB 우선, 없으면 config에서)
        """
        # MongoDB에서 먼저 조회
        if self.db_manager:
            try:
                settings = self.db_manager.get_user_settings(user_id)
                contacts = settings.get("emergency_contacts", [])
                if contacts:
                    return contacts
            except Exception as e:
                print(f"MongoDB에서 긴급 연락망 조회 실패: {e}")
        
        # MongoDB에 없으면 config에서 가져오기
        all_contacts = config.NOTIFICATION_CONFIG.get("emergency_contacts", {})
        return all_contacts.get(user_id, [])

