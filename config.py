import os

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://finer-mantis-allowed.ngrok-free.app")
NHU_CAU_PATH = os.getenv("NHU_CAU_PATH", f"data/data_nhucau.parquet")
NHAP_BAN_PATH = os.getenv("NHAP_BAN_PATH", f"data/data_nhapban.parquet")