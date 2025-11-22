import pandas as pd
import os

COLUMN_MAP = {
    "코어 사용량 (avg) [%]": "cpu_usage",
    "코어 온도 (avg) [°C]": "cpu_temp",
    "GPU 온도 [°C]": "gpu_temp",
    "GPU 활용률 [%]": "gpu_usage",
    "GPU 메모리 사용량 [%]": "gpu_mem",
    "디스크 온도 [°C]": "disk_temp",
    "디스크 남은 수명 [%]": "disk_life",
    "디스크 사용 가능한 스페어 [%]": "disk_spare",
}


def make_labels(df):
    df["label_cpu"] = (df["cpu_usage"] > 85).astype(int)
    df["label_gpu"] = (df["gpu_temp"] > 85).astype(int)
    df["label_disk"] = ((df["disk_temp"] > 60) | (df["disk_life"] < 20)).astype(int)

    danger = df[["label_cpu", "label_gpu", "label_disk"]].sum(axis=1)
    df["risk_class"] = 0
    df.loc[danger >= 1, "risk_class"] = 1
    df.loc[danger >= 2, "risk_class"] = 2

    return df


def build_dataset():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print("DATA DIR:", BASE_DIR)

    files = [
        os.path.join(BASE_DIR, f)
        for f in os.listdir(BASE_DIR)
        if f.lower().endswith(".csv")
    ]

    if not files:
        print("ERROR: CSV 파일 없음 — data 폴더 확인 필요:", BASE_DIR)
        return

    print("Found CSV files:")
    for f in files:
        print(" -", f)

    all_rows = []

    for file in files:
        try:
            df = pd.read_csv(file, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(file, encoding="cp949")

        cols = [k for k in COLUMN_MAP if k in df.columns]

        if not cols:
            print("WARN: 필요한 컬럼 없음 — 스킵:", os.path.basename(file))
            continue

        df = df[cols]
        df = df.rename(columns=COLUMN_MAP)
        df = make_labels(df)
        all_rows.append(df)


    if not all_rows:
        print("ERROR: CSV는 있었지만 내용이 유효하지 않음.")
        return

    final_df = pd.concat(all_rows, ignore_index=True)

    output_path = os.path.join(BASE_DIR, "snapshot_dataset.csv")
    final_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("SUCCESS: snapshot_dataset.csv 생성 완료")
    print("출력 위치:", output_path)
    print(final_df.head())


if __name__ == "__main__":
    build_dataset()
