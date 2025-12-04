"""
데이터 처리 및 전처리 모듈
CSV 데이터 로드, 결측치 처리, 정규화, 시계열 윈도우 생성
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import pickle
import os
from typing import Tuple, List, Optional
import config


class DataProcessor:
    """웨어러블 센서 데이터 처리 클래스"""
    
    def __init__(self, missing_value_strategy: str = "mean"):
        """
        Args:
            missing_value_strategy: 결측치 처리 방법 ("zero", "mean", "median")
        """
        self.scaler = MinMaxScaler()
        self.missing_value_strategy = missing_value_strategy
        self.feature_names = []
        
    def load_csv(self, file_path: str) -> pd.DataFrame:
        """
        CSV 파일 로드
        
        Args:
            file_path: CSV 파일 경로
            
        Returns:
            로드된 DataFrame
        """
        df = pd.read_csv(file_path)
        print(f"데이터 로드 완료: {len(df)} 행, {len(df.columns)} 열")
        return df
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        결측치 처리
        
        Args:
            df: 원본 DataFrame
            
        Returns:
            결측치 처리된 DataFrame
        """
        df_processed = df.copy()
        
        # 숫자형 컬럼만 선택
        numeric_cols = df_processed.select_dtypes(include=[np.number]).columns.tolist()
        
        if self.missing_value_strategy == "zero":
            df_processed[numeric_cols] = df_processed[numeric_cols].fillna(0)
        elif self.missing_value_strategy == "mean":
            df_processed[numeric_cols] = df_processed[numeric_cols].fillna(
                df_processed[numeric_cols].mean()
            )
        elif self.missing_value_strategy == "median":
            df_processed[numeric_cols] = df_processed[numeric_cols].fillna(
                df_processed[numeric_cols].median()
            )
        
        print(f"결측치 처리 완료 (전략: {self.missing_value_strategy})")
        return df_processed
    
    def select_features(self, df: pd.DataFrame, 
                       feature_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        특징 선택
        
        Args:
            df: 원본 DataFrame
            feature_columns: 사용할 특징 열 이름 리스트 (None이면 자동 선택)
            
        Returns:
            특징만 선택된 DataFrame
        """
        if feature_columns is None:
            # 기본적으로 숫자형 컬럼 중 시간 관련 컬럼 제외
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            exclude_keywords = ["time", "date", "timestamp", "id", "user_id"]
            feature_columns = [
                col for col in numeric_cols 
                if not any(keyword in col.lower() for keyword in exclude_keywords)
            ]
        
        self.feature_names = feature_columns
        df_features = df[feature_columns].copy()
        print(f"특징 선택 완료: {len(feature_columns)}개 특징")
        return df_features
    
    def normalize(self, data: np.ndarray, fit: bool = True) -> np.ndarray:
        """
        MinMaxScaler로 정규화
        
        Args:
            data: 정규화할 데이터 (2D array)
            fit: Scaler를 fit할지 여부
            
        Returns:
            정규화된 데이터
        """
        if fit:
            data_normalized = self.scaler.fit_transform(data)
        else:
            data_normalized = self.scaler.transform(data)
        
        return data_normalized
    
    def create_sequences(self, data: np.ndarray, 
                        sequence_length: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """
        시계열 윈도우 생성
        
        Args:
            data: 정규화된 데이터 (2D array: [samples, features])
            sequence_length: 시퀀스 길이 (분 단위)
            
        Returns:
            X: 입력 시퀀스 (3D array: [samples, sequence_length, features])
            y: 타겟 시퀀스 (동일)
        """
        X, y = [], []
        
        for i in range(len(data) - sequence_length):
            X.append(data[i:i + sequence_length])
            y.append(data[i:i + sequence_length])
        
        X = np.array(X)
        y = np.array(y)
        
        print(f"시퀀스 생성 완료: {len(X)}개 시퀀스, 길이: {sequence_length}")
        return X, y
    
    def prepare_data(self, file_path: str, 
                    sequence_length: int = 60,
                    feature_columns: Optional[List[str]] = None,
                    test_size: float = 0.2,
                    validation_size: float = 0.1) -> dict:
        """
        전체 데이터 준비 파이프라인
        
        Args:
            file_path: CSV 파일 경로
            sequence_length: 시퀀스 길이
            feature_columns: 사용할 특징 열
            test_size: 테스트 데이터 비율
            validation_size: 검증 데이터 비율
            
        Returns:
            {
                "X_train", "X_val", "X_test",
                "y_train", "y_val", "y_test",
                "scaler": scaler 객체
            }
        """
        # 1. 데이터 로드
        df = self.load_csv(file_path)
        
        # 2. 결측치 처리
        df = self.handle_missing_values(df)
        
        # 3. 특징 선택
        df_features = self.select_features(df, feature_columns)
        
        # 4. 정규화 (fit)
        data_normalized = self.normalize(df_features.values, fit=True)
        
        # 5. 시계열 시퀀스 생성
        X, y = self.create_sequences(data_normalized, sequence_length)
        
        # 6. Train/Val/Test 분할
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        val_size_adjusted = validation_size / (1 - test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_size_adjusted, random_state=42
        )
        
        print(f"\n데이터 분할 완료:")
        print(f"  Train: {len(X_train)} 샘플")
        print(f"  Val: {len(X_val)} 샘플")
        print(f"  Test: {len(X_test)} 샘플")
        
        return {
            "X_train": X_train,
            "X_val": X_val,
            "X_test": X_test,
            "y_train": y_train,
            "y_val": y_val,
            "y_test": y_test,
            "scaler": self.scaler,
            "feature_names": self.feature_names
        }
    
    def save_scaler(self, file_path: str):
        """Scaler 저장"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        print(f"Scaler 저장 완료: {file_path}")
    
    def load_scaler(self, file_path: str):
        """Scaler 로드"""
        with open(file_path, 'rb') as f:
            self.scaler = pickle.load(f)
        print(f"Scaler 로드 완료: {file_path}")
    
    def preprocess_single_window(self, raw_data: dict) -> np.ndarray:
        """
        단일 윈도우 데이터 전처리 (실시간 예측용)
        
        Args:
            raw_data: {"heart_rate": 72, "steps": 120, ...} 형태의 딕셔너리
            
        Returns:
            전처리된 데이터 (1D array)
        """
        # 딕셔너리를 DataFrame으로 변환
        df = pd.DataFrame([raw_data])
        
        # 특징 선택
        df_features = df[self.feature_names]
        
        # 결측치 처리
        df_features = df_features.fillna(df_features.mean())
        
        # 정규화
        data_normalized = self.normalize(df_features.values, fit=False)
        
        return data_normalized[0]

