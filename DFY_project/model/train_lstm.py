# model/train_lstm.py
import os
from pathlib import Path

import torch
from torch import nn, optim

from model.dataset import create_dataloader
from model.lstm_model import LoadLSTM

def train(
    daily_dir: str = "data/daily",
    seq_len: int = 30,
    batch_size: int = 64,
    num_epochs: int = 10,
    lr: float = 1e-3,
    device: str | None = None,
    # 🔽 절대 경로 → 프로젝트 내부 상대 경로로 변경
    save_path: str = "internal/model_load_lstm.pth",
):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    dataloader = create_dataloader(daily_dir, seq_len, batch_size)
    if dataloader is None:
        print("[DFY][LSTM][WARN] Dataset is empty. Check data/daily or dataset.py.")
        return
    
    model = LoadLSTM(input_dim=8).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    print(f"[DFY] Training on {device} | samples={len(dataloader.dataset)}")

    for epoch in range(1, num_epochs + 1):
        model.train()
        running_loss = 0.0

        for x_batch, y_batch in dataloader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad()
            preds = model(x_batch)
            loss = criterion(preds, y_batch)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * x_batch.size(0)

        epoch_loss = running_loss / len(dataloader.dataset)
        print(f"[Epoch {epoch}/{num_epochs}] MSE: {epoch_loss:.4f}")

    root_dir = Path(__file__).resolve().parents[1]  # new_dfy 루트
    save_path = Path(save_path)
    if not save_path.is_absolute():
        save_path = root_dir / save_path

    save_dir = save_path.parent
    os.makedirs(save_dir, exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"[DFY] Model saved at {save_path}")


if __name__ == "__main__":
    train()
