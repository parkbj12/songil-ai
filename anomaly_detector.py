"""
이상 탐지 로직 모듈
Reconstruction Error 기반 이상 탐지
"""
import torch
import numpy as np
from typing import Tuple, List, Dict
import config
from model import LSTMAutoencoder


class AnomalyDetector:
    """이상 탐지 클래스"""
    
    def __init__(self, model: LSTMAutoencoder, threshold: float = None):
        """
        Args:
            model: 학습된 LSTM Autoencoder 모델
            threshold: 이상 탐지 임계값 (None이면 자동 계산)
        """
        self.model = model
        self.threshold = threshold
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
    
    def calculate_reconstruction_error(self, X: np.ndarray) -> np.ndarray:
        """
        재구성 오차 계산
        
        Args:
            X: 입력 데이터 [batch_size, sequence_length, features]
            
        Returns:
            각 샘플의 재구성 오차 [batch_size]
        """
        X_tensor = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            reconstructed, _ = self.model(X_tensor)
            # MSE 계산
            mse = torch.nn.functional.mse_loss(
                reconstructed, X_tensor, reduction='none'
            )
            # 시퀀스와 특징 차원에 대해 평균
            reconstruction_errors = mse.mean(dim=(1, 2)).cpu().numpy()
        
        return reconstruction_errors
    
    def compute_threshold(self, X_val: np.ndarray, 
                         multiplier: float = 1.0,
                         use_percentile: bool = False,
                         percentile: float = 95,
                         min_threshold: float = 0.01) -> float:
        """
        Validation 데이터로부터 임계값 계산
        threshold = mean + (multiplier * std) 또는 percentile 사용
        
        Args:
            X_val: 검증 데이터
            multiplier: 표준편차 배수
            use_percentile: True면 percentile 사용, False면 mean+std 사용
            percentile: percentile 사용 시 몇 퍼센트 사용
            min_threshold: 최소 임계값 (너무 낮은 임계값 방지)
            
        Returns:
            계산된 임계값
        """
        reconstruction_errors = self.calculate_reconstruction_error(X_val)
        mean_error = np.mean(reconstruction_errors)
        std_error = np.std(reconstruction_errors)
        
        if use_percentile:
            threshold = np.percentile(reconstruction_errors, percentile)
            print(f"임계값 계산 완료 (Percentile 방식):")
            print(f"  평균 오차: {mean_error:.4f}")
            print(f"  표준편차: {std_error:.4f}")
            print(f"  {percentile}th percentile: {threshold:.4f}")
        else:
            threshold = mean_error + (multiplier * std_error)
            print(f"임계값 계산 완료 (Mean+Std 방식):")
            print(f"  평균 오차: {mean_error:.4f}")
            print(f"  표준편차: {std_error:.4f}")
            print(f"  임계값: {threshold:.4f} (평균 + {multiplier} * 표준편차)")
        
        # 최소 임계값 보장
        if threshold < min_threshold:
            print(f"  경고: 계산된 임계값({threshold:.4f})이 최소 임계값({min_threshold:.4f})보다 낮습니다.")
            print(f"  최소 임계값({min_threshold:.4f})을 사용합니다.")
            threshold = min_threshold
        
        self.threshold = threshold
        return threshold
    
    def detect_anomaly(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[bool]]:
        """
        이상 탐지 수행
        
        Args:
            X: 입력 데이터 [batch_size, sequence_length, features]
            
        Returns:
            anomaly_scores: 이상 점수 배열
            reconstruction_errors: 재구성 오차 배열
            is_anomaly: 이상 여부 리스트
        """
        if self.threshold is None:
            raise ValueError("임계값이 설정되지 않았습니다. compute_threshold()를 먼저 호출하세요.")
        
        reconstruction_errors = self.calculate_reconstruction_error(X)
        # 이상 점수 계산: 재구성 오차 / 임계값
        # 최대값 제한 (너무 높은 점수 방지)
        anomaly_scores = reconstruction_errors / self.threshold
        # 이상 점수가 100을 넘으면 로그 스케일로 변환
        # log1p에 음수 값이 들어가지 않도록 보장
        anomaly_scores = np.where(
            anomaly_scores > 100,
            100 + np.log1p(np.maximum(anomaly_scores - 100, 0)),
            anomaly_scores
        )
        is_anomaly = (reconstruction_errors > self.threshold).tolist()
        
        return anomaly_scores, reconstruction_errors, is_anomaly
    
    def detect_single(self, X: np.ndarray) -> Dict:
        """
        단일 샘플 이상 탐지
        
        Args:
            X: 단일 샘플 [1, sequence_length, features]
            
        Returns:
            {
                "anomaly_score": float,
                "reconstruction_error": float,
                "is_anomaly": bool,
                "threshold": float
            }
        """
        if X.ndim == 2:
            X = X.reshape(1, *X.shape)
        
        anomaly_scores, reconstruction_errors, is_anomaly = self.detect_anomaly(X)
        
        return {
            "anomaly_score": float(anomaly_scores[0]),
            "reconstruction_error": float(reconstruction_errors[0]),
            "is_anomaly": is_anomaly[0],
            "threshold": float(self.threshold) if self.threshold is not None else 0.1
        }
    
    def analyze_anomaly_pattern(self, X: np.ndarray, 
                               feature_names: List[str]) -> Dict:
        """
        이상 패턴 분석 (어떤 특징이 이상한지 분석)
        
        Args:
            X: 입력 데이터 [1, sequence_length, features]
            feature_names: 특징 이름 리스트
            
        Returns:
            특징별 이상 점수 딕셔너리
        """
        X_tensor = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            reconstructed, _ = self.model(X_tensor)
            # 특징별 MSE 계산
            mse = torch.nn.functional.mse_loss(
                reconstructed, X_tensor, reduction='none'
            )
            # 시퀀스 차원에 대해 평균하여 특징별 오차 계산
            feature_errors = mse.mean(dim=1).cpu().numpy()[0]
        
        feature_anomaly_scores = {}
        for i, feature_name in enumerate(feature_names):
            feature_anomaly_scores[feature_name] = float(feature_errors[i])
        
        # 가장 이상한 특징 정렬
        sorted_features = sorted(
            feature_anomaly_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 튜플의 값도 float로 변환 (JSON 직렬화를 위해)
        top_features = [(name, float(score)) for name, score in sorted_features[:3]]
        
        return {
            "feature_scores": feature_anomaly_scores,
            "top_anomalous_features": top_features  # 상위 3개
        }
    
    def get_anomaly_feedback_message(self, anomaly_result: Dict,
                                    feature_analysis: Dict = None) -> str:
        """
        이상 탐지 결과에 따른 피드백 메시지 생성
        
        Args:
            anomaly_result: detect_single() 결과
            feature_analysis: analyze_anomaly_pattern() 결과 (선택)
            
        Returns:
            피드백 메시지
        """
        if not anomaly_result["is_anomaly"]:
            return "현재 데이터가 정상 범위 내에 있습니다."
        
        message_parts = []
        anomaly_score = anomaly_result["anomaly_score"]
        
        if anomaly_score > 2.0:
            severity = "높은"
            action = "즉시 건강 상태를 확인하고 필요시 의료진과 상담하시기 바랍니다."
        elif anomaly_score > 1.5:
            severity = "중간"
            action = "건강 상태를 주의 깊게 관찰하시기 바랍니다."
        else:
            severity = "낮은"
            action = "가벼운 활동 변화를 권장합니다."
        
        message_parts.append(f"⚠️ 이상 패턴이 감지되었습니다 (심각도: {severity}).")
        
        if feature_analysis:
            top_features = feature_analysis["top_anomalous_features"]
            if top_features:
                top_feature_name = top_features[0][0]
                message_parts.append(f"특히 '{top_feature_name}' 관련 데이터가 평소와 다릅니다.")
        
        message_parts.append(action)
        
        return " ".join(message_parts)

