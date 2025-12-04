"""
챗봇 모듈
OpenAI API 또는 Rule-based 응답 생성
"""
from openai import OpenAI
from typing import Dict, Optional
import config


class HealthChatbot:
    """건강관리 챗봇 클래스"""
    
    def __init__(self, use_openai: bool = True):
        """
        Args:
            use_openai: OpenAI API 사용 여부 (False면 Rule-based)
        """
        self.use_openai = use_openai
        self.client = None
        if use_openai and config.OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=config.OPENAI_API_KEY)
                print("OpenAI API 클라이언트 초기화 완료")
            except Exception as e:
                print(f"OpenAI API 클라이언트 초기화 실패: {e}")
                self.use_openai = False
        else:
            self.use_openai = False
            print("OpenAI API 키가 없거나 사용하지 않음. Rule-based 모드로 전환합니다.")
    
    def generate_feedback(self, anomaly_result: Dict,
                          user_data: Optional[Dict] = None) -> str:
        """
        이상 탐지 결과에 따른 피드백 생성
        
        Args:
            anomaly_result: 이상 탐지 결과 딕셔너리
            user_data: 사용자 데이터 (선택)
            
        Returns:
            피드백 메시지
        """
        if self.use_openai:
            return self._generate_openai_feedback(anomaly_result, user_data)
        else:
            return self._generate_rule_based_feedback(anomaly_result, user_data)
    
    def _generate_openai_feedback(self, anomaly_result: Dict,
                                  user_data: Optional[Dict] = None) -> str:
        """
        OpenAI API를 사용한 피드백 생성
        """
        if not self.client:
            return self._generate_rule_based_feedback(anomaly_result, user_data)
        
        try:
            prompt = self._create_prompt(anomaly_result, user_data)
            
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 건강관리 전문 챗봇입니다. 아이폰 건강앱(HealthKit)과 연동하여 수집한 웨어러블 센서 데이터를 분석하여 사용자에게 친절하고 실용적인 건강 조언을 제공합니다. 특히 홀로 사는 분들의 건강 상태를 모니터링하여 고독사 예방을 지원합니다. 응답은 간결하고 명확하게 작성하되, 완전한 문장으로 끝내세요. 절대로 마크다운 형식(**굵게**, - 목록)을 사용하지 말고 순수한 일반 텍스트로만 작성해주세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            feedback = response.choices[0].message.content.strip()
            # 마크다운 형식 제거 (**굵게** -> 굵게)
            feedback = feedback.replace('**', '')
            feedback = feedback.replace('*', '')
            return feedback
            
        except Exception as e:
            print(f"OpenAI API 호출 실패: {e}")
            return self._generate_rule_based_feedback(anomaly_result, user_data)
    
    def _generate_rule_based_feedback(self, anomaly_result: Dict,
                                     user_data: Optional[Dict] = None) -> str:
        """
        Rule-based 피드백 생성
        """
        is_anomaly = anomaly_result.get("is_anomaly", False)
        anomaly_score = anomaly_result.get("anomaly_score", 0)
        reconstruction_error = anomaly_result.get("reconstruction_error", 0)
        
        # 사용자 데이터 추출
        heart_rate = None
        steps = None
        sleep = None
        temperature = None
        all_zero = False
        
        if user_data:
            sensor_data = user_data.get("sensor_data", [])
            if sensor_data:
                latest_data = sensor_data[-1]
                heart_rate = latest_data.get("heart_rate", 0)
                steps = latest_data.get("steps", 0)
                sleep = latest_data.get("sleep", 0)
                temperature = latest_data.get("temperature", 0)
                
                # 모든 값이 0인지 확인
                all_zero = (heart_rate == 0 and steps == 0 and sleep == 0 and temperature == 0)
        
        # 심각한 상황 체크 (모든 값이 0이거나 심박수가 0)
        if all_zero or (heart_rate is not None and heart_rate == 0):
            feedback_parts = []
            feedback_parts.append("🚨 긴급: 매우 심각한 건강 상태가 감지되었습니다!")
            feedback_parts.append("")
            
            if heart_rate == 0:
                feedback_parts.append("⚠️ 심박수가 0으로 측정되었습니다. 이는 매우 비정상적인 상태입니다.")
                feedback_parts.append("")
                feedback_parts.append("즉시 조치가 필요합니다:")
                feedback_parts.append("1. 즉시 119(응급실)에 연락하거나 가까운 응급실로 이동하세요")
                feedback_parts.append("2. 주변 사람에게 도움을 요청하세요")
                feedback_parts.append("3. 의식이 있다면 편안한 자세로 누워 호흡을 천천히 하세요")
                feedback_parts.append("")
                feedback_parts.append("💡 가능한 원인:")
                feedback_parts.append("- 센서 오작동 또는 착용 문제")
                feedback_parts.append("- 심각한 건강 이상 징후")
                feedback_parts.append("- 데이터 입력 오류")
                feedback_parts.append("")
                feedback_parts.append("중요: 만약 실제로 불편함을 느끼고 계시다면 즉시 의료진의 도움을 받으시기 바랍니다.")
            
            elif all_zero:
                feedback_parts.append("⚠️ 모든 건강 지표가 0으로 측정되었습니다.")
                feedback_parts.append("")
                feedback_parts.append("가능한 원인:")
                feedback_parts.append("1. 센서가 제대로 작동하지 않거나 착용되지 않았을 수 있습니다")
                feedback_parts.append("2. 데이터 입력이 누락되었을 수 있습니다")
                feedback_parts.append("3. 실제로 활동이 전혀 없었을 수 있습니다")
                feedback_parts.append("")
                feedback_parts.append("권장 조치:")
                feedback_parts.append("- 센서나 기기를 확인하고 다시 측정해보세요")
                feedback_parts.append("- 실제 건강 상태에 이상이 있다고 느끼시면 즉시 의료진에게 상담하세요")
                feedback_parts.append("- 24시간 이상 활동이 없다면 주변 사람에게 연락하거나 도움을 요청하세요")
            
            feedback_parts.append("")
            feedback_parts.append("🏥 긴급 연락처:")
            feedback_parts.append("- 응급실: 119")
            feedback_parts.append("- 건강상담: 1339 (보건복지상담센터)")
            feedback_parts.append("")
            feedback_parts.append("본 시스템은 자동으로 이상 징후를 감지하여 지정된 보호자나 긴급 연락망에 알림을 전송합니다.")
            
            return "\n".join(feedback_parts)
        
        if not is_anomaly:
            # 정상 상태이지만 데이터가 비정상적으로 낮은 경우
            if heart_rate is not None and heart_rate < 40:
                return "⚠️ 심박수가 {heart_rate}로 정상 범위보다 낮게 측정되었습니다. 만약 불편함을 느끼신다면 의료진에게 상담하시기 바랍니다. 평소보다 휴식을 취하시고 스트레스를 줄여보세요."
            
            if steps is not None and steps == 0:
                return "💡 오늘 활동량이 매우 적네요. 가벼운 산책이나 스트레칭을 권장합니다. 장시간 움직이지 않으면 건강에 좋지 않으니, 1-2시간마다 일어나서 몸을 움직여보세요."
            
            messages = [
                "✅ 좋은 소식입니다! 현재 건강 상태가 정상 범위 내에 있습니다. 지금처럼 규칙적인 생활 패턴을 유지해주세요.",
                "✅ 오늘도 건강한 하루 보내고 계시네요! 현재 모든 지표가 정상 범위입니다. 계속 이렇게 유지해주세요!",
                "✅ 훌륭합니다! 활동 패턴이 안정적으로 유지되고 있습니다. 건강 관리를 잘 하고 계시네요."
            ]
            import random
            return random.choice(messages)
        
        # 이상 탐지된 경우 - 더 친절하고 실용적인 피드백
        feedback_parts = []
        
        # 이상 점수에 따른 친절한 피드백
        if anomaly_score > 10.0:
            feedback_parts.append("🚨 중요: 건강 상태에 심각한 이상 징후가 감지되었습니다.")
            feedback_parts.append("")
            feedback_parts.append("센서 데이터를 분석한 결과, 평소와 매우 다른 패턴이 관찰되었습니다.")
            feedback_parts.append("이런 변화는 일시적일 수 있지만, 지속된다면 즉시 의료진의 상담이 필요합니다.")
            feedback_parts.append("")
            feedback_parts.append("즉시 확인해야 할 사항:")
            feedback_parts.append("1. 현재 몸 상태에 불편함이나 통증이 있으신가요?")
            feedback_parts.append("2. 평소와 다른 증상이 있으신가요? (어지러움, 호흡곤란, 가슴 통증 등)")
            feedback_parts.append("3. 최근 약물 복용이나 생활 패턴에 변화가 있었나요?")
            feedback_parts.append("")
            feedback_parts.append("권장 조치:")
            feedback_parts.append("- 증상이 심각하다면 즉시 119에 연락하거나 응급실로 이동하세요")
            feedback_parts.append("- 증상이 경미하다면 가까운 병원이나 보건소를 방문하여 상담받으세요")
            feedback_parts.append("- 주변 사람에게 상황을 알리고 도움을 요청하세요")
            feedback_parts.append("")
            if heart_rate:
                if 60 <= heart_rate <= 100:
                    feedback_parts.append(f"다행히 심박수({heart_rate} bpm)는 정상 범위입니다.")
                elif heart_rate < 40:
                    feedback_parts.append(f"⚠️ 심박수가 {heart_rate} bpm로 매우 낮습니다. 즉시 의료진의 상담이 필요합니다.")
                elif heart_rate > 120:
                    feedback_parts.append(f"⚠️ 심박수가 {heart_rate} bpm로 높게 나타났습니다. 휴식을 취하시고, 지속되면 의료진에게 상담하세요.")
                else:
                    feedback_parts.append(f"심박수가 {heart_rate} bpm로 나타났습니다. 휴식을 취하시고 스트레스를 줄여보세요.")
        elif anomaly_score > 5.0:
            feedback_parts.append("오늘 활동 패턴을 분석한 결과, 평소와 약간 다른 패턴이 보입니다.")
            feedback_parts.append("이는 특별히 걱정할 만한 수준은 아니지만, 건강 관리를 위해 몇 가지 권장사항을 드립니다.")
            feedback_parts.append("💡 제안: 오늘은 가벼운 스트레칭이나 10-15분 정도의 산책을 해보세요. 충분한 수면도 중요합니다.")
            if heart_rate and 60 <= heart_rate <= 100:
                feedback_parts.append(f"심박수({heart_rate})는 정상 범위를 유지하고 있어 좋습니다.")
            if steps and steps < 5000:
                feedback_parts.append(f"오늘 걸음수가 {steps}걸음으로 조금 적네요. 점심시간이나 저녁에 가벼운 산책을 추가해보세요.")
            elif steps and steps >= 5000:
                feedback_parts.append(f"오늘 {steps}걸음이나 걸으셨네요! 활동량이 좋습니다.")
        elif anomaly_score > 2.0:
            feedback_parts.append("오늘의 활동 패턴을 확인해보니 평소와 조금 다른 모습이 보입니다.")
            feedback_parts.append("이는 일시적인 변화일 수 있으니, 규칙적인 생활 리듬을 유지하시면 도움이 됩니다.")
            feedback_parts.append("💡 제안: 오늘은 가벼운 운동이나 스트레칭을 추가해보시거나, 일정한 시간에 식사와 수면을 취해보세요.")
            if heart_rate and 60 <= heart_rate <= 100:
                feedback_parts.append(f"심박수({heart_rate})는 안정적입니다.")
            if steps:
                feedback_parts.append(f"오늘 {steps}걸음을 걸으셨네요. 꾸준한 활동이 건강에 도움이 됩니다.")
        elif anomaly_score > 1.5:
            feedback_parts.append("센서 데이터를 확인한 결과, 오늘 활동 패턴이 평소와 약간 다릅니다.")
            feedback_parts.append("큰 걱정은 없지만, 건강한 생활 습관을 유지하시는 것이 좋겠습니다.")
            feedback_parts.append("💡 제안: 규칙적인 생활 리듬을 유지하시고, 충분한 수면과 적절한 활동량을 지켜주세요.")
            if heart_rate:
                feedback_parts.append(f"심박수({heart_rate})는 정상 범위입니다.")
            if steps:
                feedback_parts.append(f"오늘 {steps}걸음이나 걸으셨네요. 좋습니다!")
        else:
            feedback_parts.append("오늘 활동 패턴을 살펴보니 평소보다 조금 다릅니다.")
            feedback_parts.append("이는 특별한 문제가 아닙니다. 현재 상태를 유지하시면 됩니다.")
            feedback_parts.append("💡 제안: 규칙적인 생활 패턴을 지속하시면 건강 관리에 도움이 됩니다.")
            if heart_rate:
                feedback_parts.append(f"심박수({heart_rate})는 정상입니다.")
            if steps:
                feedback_parts.append(f"오늘도 {steps}걸음이나 걸으셨네요. 훌륭합니다!")
        
        # 고독사 예방 관련 메시지 추가
        if anomaly_score > 5.0:
            feedback_parts.append("")
            feedback_parts.append("🏠 홀로 사는 분들을 위한 건강 관리:")
            feedback_parts.append("본 시스템은 24시간 건강 상태를 모니터링하여 이상 징후를 조기 발견합니다.")
            feedback_parts.append("이상 패턴이 지속되면 지정된 보호자나 긴급 연락망에 자동으로 알림이 전송됩니다.")
            feedback_parts.append("혼자 계시더라도 걱정하지 마세요. 시스템이 지속적으로 모니터링하고 있습니다.")
        
        # 긍정적인 마무리 (심각한 경우가 아닐 때만)
        if anomaly_score <= 10.0:
            feedback_parts.append("")
            feedback_parts.append("정기적으로 건강 상태를 확인하시는 것만으로도 건강 관리에 큰 도움이 됩니다.")
            feedback_parts.append("건강한 생활 습관을 유지하시고, 궁금한 점이 있으시면 언제든지 물어보세요!")
        
        return "\n".join(feedback_parts)
    
    def _create_prompt(self, anomaly_result: Dict,
                      user_data: Optional[Dict] = None) -> str:
        """
        OpenAI API용 프롬프트 생성
        """
        is_anomaly = anomaly_result.get('is_anomaly', False)
        anomaly_score = anomaly_result.get('anomaly_score', 0)
        
        prompt = f"""
웨어러블 센서 데이터를 분석한 결과를 바탕으로 사용자에게 친절하고 실용적인 건강 조언을 제공해주세요.

[시스템 목적]
본 시스템은 아이폰 건강앱(HealthKit)과 연동하여 사용자의 건강 데이터를 실시간으로 수집하고, 
LSTM Autoencoder 모델 기반 실시간 건강 이상 감지를 제공합니다. 
특히 홀로 사는 분들의 건강 상태를 지속적으로 모니터링하여 이상 징후를 조기 발견하고, 
고독사 예방을 위한 자동 알림 시스템을 제공하는 것을 목적으로 합니다.

[분석 결과]
- 이상 탐지: {'감지됨' if is_anomaly else '정상'}
- 이상 점수: {anomaly_score:.2f}
"""
        
        # 심각한 상황 체크
        critical_situation = False
        critical_reasons = []
        
        if user_data:
            sensor_data = user_data.get("sensor_data", [])
            if sensor_data:
                latest_data = sensor_data[-1]
                heart_rate = latest_data.get('heart_rate', 0)
                steps = latest_data.get('steps', 0)
                sleep = latest_data.get('sleep', 0)
                temperature = latest_data.get('temperature', 0)
                
                prompt += f"""
최근 센서 데이터:
- 심박수: {heart_rate} bpm
- 걸음수: {steps} 걸음
- 수면 시간: {sleep} 시간
- 체온: {temperature} ℃
"""
                
                # 심각한 상황 체크
                if heart_rate == 0:
                    critical_situation = True
                    critical_reasons.append("심박수가 0으로 측정됨 - 매우 심각한 상황, 즉시 의료진 상담 필요")
                elif heart_rate < 40:
                    critical_situation = True
                    critical_reasons.append(f"심박수가 {heart_rate} bpm로 매우 낮음 - 의료진 상담 권장")
                elif heart_rate > 150:
                    critical_situation = True
                    critical_reasons.append(f"심박수가 {heart_rate} bpm로 매우 높음 - 휴식 및 의료진 상담 권장")
                
                if heart_rate == 0 and steps == 0 and sleep == 0 and temperature == 0:
                    critical_situation = True
                    critical_reasons.append("모든 건강 지표가 0으로 측정됨 - 센서 오작동 가능성 또는 심각한 건강 이상")
        
        if critical_situation:
            prompt += f"""
[⚠️ 심각한 상황 감지]
다음과 같은 심각한 건강 이상 징후가 감지되었습니다:
{chr(10).join('- ' + reason for reason in critical_reasons)}

이런 경우에는:
1. 즉시 의료진의 도움을 받아야 합니다 (119 또는 응급실)
2. 주변 사람에게 도움을 요청해야 합니다
3. 센서 오작동일 수도 있으니 기기를 확인해야 합니다
4. 실제로 불편함을 느끼고 있다면 절대 방심하지 마세요

위 상황을 고려하여 적절한 경고와 조치 방법을 포함한 피드백을 제공해주세요.
"""
        else:
            prompt += """
위 데이터를 바탕으로:
1. 걱정을 주지 않으면서도 도움이 되는 친절한 톤으로 작성해주세요
2. 구체적이고 실용적인 건강 조언을 제공해주세요
3. 긍정적이고 격려하는 메시지로 마무리해주세요
"""
        
        prompt += """
4. 한국어로 자연스럽게 작성해주세요
5. 반드시 완전한 문장으로 끝내세요 (절대 중간에 끊기지 않도록)
6. 적절한 길이로 작성하되 (200-400자 정도), 모든 내용을 포함해주세요
7. 마크다운 형식(**굵게**, - 목록)을 사용하지 말고 일반 텍스트로 작성해주세요
8. 이모지(🚨, ⚠️, 💡 등)는 사용해도 되지만 마크다운 굵게 표시는 사용하지 마세요
"""
        
        return prompt
    
    def chat(self, user_message: str, context: Optional[Dict] = None) -> str:
        """
        일반 대화 응답 생성
        
        Args:
            user_message: 사용자 메시지
            context: 대화 컨텍스트 (선택)
            
        Returns:
            챗봇 응답
        """
        if self.use_openai:
            return self._chat_with_openai(user_message, context)
        else:
            return self._chat_rule_based(user_message, context)
    
    def _chat_with_openai(self, user_message: str,
                         context: Optional[Dict] = None) -> str:
        """OpenAI API를 사용한 대화"""
        if not self.client:
            return self._chat_rule_based(user_message, context)
        
        try:
            messages = [
                {"role": "system", "content": "당신은 건강관리 전문 챗봇입니다. 사용자에게 친절하고 도움이 되는 건강 조언을 제공합니다."}
            ]
            
            if context:
                messages.append({
                    "role": "system",
                    "content": f"사용자 컨텍스트: {context}"
                })
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API 호출 실패: {e}")
            return self._chat_rule_based(user_message, context)
    
    def _chat_rule_based(self, user_message: str,
                        context: Optional[Dict] = None) -> str:
        """Rule-based 대화"""
        user_message_lower = user_message.lower()
        
        # 인사
        if any(word in user_message_lower for word in ["안녕", "hello", "hi"]):
            return "안녕하세요! 건강관리 챗봇입니다. 오늘 건강 상태는 어떠신가요?"
        
        # 건강 상태 질문
        if any(word in user_message_lower for word in ["건강", "상태", "어떻게"]):
            return "웨어러블 센서 데이터를 분석하여 건강 상태를 모니터링하고 있습니다. 이상 패턴이 감지되면 알려드리겠습니다."
        
        # 활동량 질문
        if any(word in user_message_lower for word in ["활동", "걸음", "운동"]):
            return "규칙적인 활동은 건강 유지에 중요합니다. 하루에 최소 30분 이상 걷기나 가벼운 운동을 권장합니다."
        
        # 수면 질문
        if any(word in user_message_lower for word in ["수면", "잠", "sleep"]):
            return "충분한 수면은 건강에 필수적입니다. 하루 7-9시간의 수면을 권장합니다."
        
        # 기본 응답
        return "건강 관리에 대해 더 구체적으로 물어보시면 도움을 드리겠습니다. 센서 데이터를 분석하여 개인 맞춤형 조언을 제공합니다."

