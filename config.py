import os
from report import report_thongtinchiahang, report_ketquabanhang

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://finer-mantis-allowed.ngrok-free.app")
NHU_CAU_PATH = os.getenv("NHU_CAU_PATH", f"data/data_nhucau.parquet")
NHAP_BAN_PATH = os.getenv("NHAP_BAN_PATH", f"data/data_nhapban.parquet")

# ===== CẤU HÌNH HIỂN THỊ BÁO CÁO =====
REPORTS_DISPLAY = [
    {"id": "thongtinchiahang", "title": "Thông tin chia hàng", "decription": "Số lượng chia mỗi ngày theo sản phẩm."},
    {"id": "ketquabanhang",    "title": "Kết quả bán hàng", "decription": "Chỉ số Nhu cầu - PO - Nhập - Bán trong 7 ngày gần nhất."}
]

DATA_PATH_FOR_REPORT = {
    "thongtinchiahang": NHU_CAU_PATH,
    "ketquabanhang":    NHAP_BAN_PATH
}

REPORT_HANDLERS = {
    "thongtinchiahang": report_thongtinchiahang,
    "ketquabanhang":    report_ketquabanhang
}

CATEGORIES = [
    {"id": 1234,  "title": "Rau Củ Các Loại"},
    {"id": 1235,  "title": "Trái Cây Các Loại"},
    {"id": 1236,  "title": "Thịt Gia Cầm Gia Súc Các Loại"},
    {"id": 1254,  "title": "Thủy Hải Sản Các Loại"},
]