"""
LSTM Autoencoder 모델 정의
PyTorch 기반
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class LSTMAutoencoder(nn.Module):
    """
    LSTM Autoencoder 모델
    Encoder: 입력 시퀀스를 잠재 표현으로 압축
    Decoder: 잠재 표현을 원본 시퀀스로 복원
    """
    
    def __init__(self, input_size: int, hidden_size: int = 64, 
                 num_layers: int = 2, dropout: float = 0.2):
        """
        Args:
            input_size: 입력 특징 수 (센서 데이터 차원)
            hidden_size: LSTM hidden state 크기
            num_layers: LSTM 층 수
            dropout: Dropout 비율
        """
        super(LSTMAutoencoder, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # Encoder
        self.encoder = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # Decoder
        self.decoder = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # 출력 레이어
        self.output = nn.Linear(hidden_size, input_size)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: 입력 시퀀스 [batch_size, sequence_length, input_size]
            
        Returns:
            reconstructed: 복원된 시퀀스 [batch_size, sequence_length, input_size]
            encoded: 인코딩된 잠재 표현 [batch_size, sequence_length, hidden_size]
        """
        batch_size, seq_len, _ = x.size()
        
        # Encoder
        encoded, (hidden, cell) = self.encoder(x)
        encoded = self.dropout(encoded)
        
        # Decoder
        decoded, _ = self.decoder(encoded, (hidden, cell))
        decoded = self.dropout(decoded)
        
        # 출력 레이어
        reconstructed = self.output(decoded)
        
        return reconstructed, encoded
    
    def encode(self, x):
        """
        인코딩만 수행 (특징 추출용)
        
        Args:
            x: 입력 시퀀스
            
        Returns:
            encoded: 인코딩된 잠재 표현
        """
        encoded, _ = self.encoder(x)
        return encoded
    
    def predict_anomaly_score(self, x):
        """
        이상 점수 계산
        
        Args:
            x: 입력 시퀀스
            
        Returns:
            anomaly_score: 평균 재구성 오차
        """
        self.eval()
        with torch.no_grad():
            reconstructed, _ = self.forward(x)
            # MSE 계산
            mse = F.mse_loss(reconstructed, x, reduction='none')
            # 시퀀스와 특징 차원에 대해 평균
            anomaly_score = mse.mean(dim=(1, 2)).item()
        return anomaly_score


class VariationalLSTMAutoencoder(nn.Module):
    """
    Variational LSTM Autoencoder (선택 사항)
    더 나은 잠재 공간 표현을 위한 확장 모델
    """
    
    def __init__(self, input_size: int, hidden_size: int = 64,
                 num_layers: int = 2, latent_dim: int = 32, dropout: float = 0.2):
        super(VariationalLSTMAutoencoder, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.latent_dim = latent_dim
        
        # Encoder
        self.encoder = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        # Latent space projection
        self.fc_mu = nn.Linear(hidden_size, latent_dim)
        self.fc_logvar = nn.Linear(hidden_size, latent_dim)
        
        # Decoder
        self.decoder_input = nn.Linear(latent_dim, hidden_size)
        self.decoder = nn.LSTM(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        
        self.output_layer = nn.Linear(hidden_size, input_size)
        self.dropout = nn.Dropout(dropout)
    
    def reparameterize(self, mu, logvar):
        """Reparameterization trick"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def forward(self, x):
        batch_size, seq_len, _ = x.size()
        
        # Encoder
        encoded, (hidden, cell) = self.encoder(x)
        
        # Latent space
        mu = self.fc_mu(encoded[:, -1, :])  # 마지막 시퀀스 사용
        logvar = self.fc_logvar(encoded[:, -1, :])
        z = self.reparameterize(mu, logvar)
        
        # Decoder
        z_expanded = self.decoder_input(z).unsqueeze(1).repeat(1, seq_len, 1)
        decoded, _ = self.decoder(z_expanded, (hidden, cell))
        decoded = self.dropout(decoded)
        reconstructed = self.output_layer(decoded)
        
        return reconstructed, mu, logvar

