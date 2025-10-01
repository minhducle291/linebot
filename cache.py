# cache.py
"""
Module quản lý cache cho DataFrame parquet.
Chỉ đọc file 1 lần/instance, sau đó trả copy từ cache.
"""

import threading
import pandas as pd

# Lưu cache theo path
_PARQUET_CACHE: dict[str, pd.DataFrame] = {}
# Khóa để tránh race condition khi nhiều request song song
_PARQUET_LOCK = threading.RLock()

def load_df_once(path: str, columns: list[str] | None = None) -> pd.DataFrame:
    """
    Đọc parquet lần đầu tiên, các lần sau trả bản copy từ cache.
    Args:
        path: đường dẫn file parquet
        columns: danh sách cột cần đọc (tuỳ chọn)
    Returns:
        DataFrame (copy, không đụng cache gốc)
    """
    with _PARQUET_LOCK:
        if path not in _PARQUET_CACHE:
            print(f"[CACHE] Đang đọc file {path} lần đầu...")
            df = pd.read_parquet(path, columns=columns) if columns else pd.read_parquet(path)
            _PARQUET_CACHE[path] = df
        # Luôn trả bản copy để tránh modify nhầm cache gốc
        return _PARQUET_CACHE[path].copy()

def clear_cache(path: str | None = None) -> None:
    """
    Xoá cache. Nếu path=None thì xoá toàn bộ.
    """
    with _PARQUET_LOCK:
        if path:
            _PARQUET_CACHE.pop(path, None)
            print(f"[CACHE] Đã xoá cache cho {path}")
        else:
            _PARQUET_CACHE.clear()
            print("[CACHE] Đã xoá toàn bộ cache")
