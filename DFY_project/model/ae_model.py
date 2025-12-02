# model/ae_model.py
from typing import Optional

import torch
from torch import nn

from model.dataset import FEATURE_KEYS


class LoadAutoencoder(nn.Module):
    """
    HWiNFO CSV로 학습한 Autoencoder와 동일한 구조.

    - 입력: 한 시점의 피처 벡터 (len(FEATURE_KEYS) 차원)
    - encoder: Linear(input -> hidden) -> ReLU -> Linear(hidden -> code) -> ReLU
    - decoder: Linear(code -> hidden) -> ReLU -> Linear(hidden -> input)

    기존 코드와의 호환을 위해 seq_len 인자를 받아두지만,
    현재 구조에서는 사용하지 않는다.
    """

    def __init__(
        self,
        input_dim: Optional[int] = None,
        hidden_dim: int = 32,
        code_dim: int = 8,
        seq_len: Optional[int] = None,  # 🔹 호환용 인자 추가
        **kwargs,                       # 🔹 혹시 모를 추가 인자도 무시
    ) -> None:
        super().__init__()

        if input_dim is None:
            input_dim = len(FEATURE_KEYS)

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.code_dim = code_dim
        self.seq_len = seq_len  # 혹시 밖에서 참고하면 쓰라고 그냥 저장만

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, code_dim),
            nn.ReLU(),
        )

        self.decoder = nn.Sequential(
            nn.Linear(code_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        out = self.decoder(z)
        return out