# model/lstm_model.py
import torch
import torch.nn as nn


class LoadLSTM(nn.Module):
    """
    시스템 부하(cpu 중심) 예측용 LSTM 모델.
    입력: (batch, seq_len, input_dim)
    출력: (batch, 1)  -> 다음 시점의 CPU 사용률 예측
    """

    def __init__(
        self,
        input_dim: int = 8,   # [cpu, ram, gpu, gpu_temp, disk_read, disk_write, net_up, net_down]
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout,
        )
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (batch, seq_len, input_dim)
        return: (batch, 1)  # 예측한 다음 시점 CPU 사용률
        """
        out, _ = self.lstm(x)          # (batch, seq_len, hidden_dim)
        last_hidden = out[:, -1, :]    # (batch, hidden_dim)
        cpu_pred = self.fc(last_hidden)  # (batch, 1)
        return cpu_pred
