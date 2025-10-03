import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

def build_flex_categories(
    store_id: int,
    categories: list[dict],
    include_display_text: bool = False,
) -> dict:
    """
    Trả về 1 bubble chứa 4 nút (ngành hàng).
    - categories: [{ "id": "fresh", "title": "Tươi sống" }, ...] (4 mục)
    """
    buttons = []
    for c in categories:
        action = {
            "type": "postback",
            "label": c.get("title", c["id"]),
            "data": f"a=category.select&store={store_id}&cat={c['id']}",
        }
        if include_display_text:
            action["displayText"] = f"Ngành: {c.get('title', c['id'])}"

        buttons.append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": action
        })

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "Chọn ngành hàng", "weight": "bold", "size": "md"},
                {"type": "text", "text": f"Siêu thị: {store_id}", "size": "xs", "color": "#666666"},
                {"type": "separator", "margin": "sm"},
                {"type": "box", "layout": "vertical", "spacing": "sm", "contents": buttons}
            ]
        },
        "footer": {
            "type": "box", "layout": "horizontal", "contents": [
                {"type": "text", "text": "Trang 1/1", "size": "xs", "color": "#999999", "align": "center"}
            ]
        }
    }
    return {"type": "carousel", "contents": [bubble]}

def build_flex_report_group(
    store_id,
    reports,
    groups_by_report,
    groups_per_bubble=6,
    include_display_text=False,
    cat_id=None
):
    """
    Tạo Flex carousel gồm nhiều bubble — mỗi bubble = 1 báo cáo, chia thành nhiều trang nhóm hàng.
    store_id: mã siêu thị
    reports: danh sách báo cáo (REPORTS_DISPLAY)
    groups_by_report: dict {report_id: [group list]}
    groups_per_bubble: số nhóm mỗi bubble
    include_display_text: có hiển thị displayText khi bấm hay không
    cat_id: mã ngành hàng (được giữ để truyền qua postback)
    """
    bubbles = []

    for report in reports:
        report_id = report["id"]
        report_title = report["title"]

        groups = groups_by_report.get(report_id, [])
        if not groups:
            continue

        # Chia groups thành nhiều trang (bubble)
        for page_idx in range(0, len(groups), groups_per_bubble):
            page_groups = groups[page_idx:page_idx + groups_per_bubble]

            contents = []
            for group in page_groups:
                group_label = str(group)

                action_data = (
                    f"a=report_group.select"
                    f"&store={store_id}"
                    f"&report={report_id}"
                    f"&group={group}"
                    f"&cat={cat_id or ''}"
                )

                action_obj = {
                    "type": "postback",
                    "label": group_label,
                    "data": action_data,
                }

                if include_display_text:
                    action_obj["displayText"] = f"{report_title} • Nhóm {group_label}"

                contents.append({
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": action_obj
                })

            bubble = {
                "type": "bubble",
                "size": "kilo",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                        {"type": "text", "text": report_title, "weight": "bold", "size": "md", "wrap": True},
                        {"type": "text", "text": f"Siêu thị: {store_id}", "size": "xs", "color": "#666666"},
                        {"type": "separator", "margin": "sm"},
                        {"type": "box", "layout": "vertical", "spacing": "sm", "contents": contents},
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"Trang {page_idx//groups_per_bubble + 1}/{-(-len(groups)//groups_per_bubble)}",
                            "size": "xs",
                            "color": "#999999",
                            "align": "center",
                        }
                    ]
                }
            }

            bubbles.append(bubble)

    if not bubbles:
        return {}

    return {
        "type": "carousel",
        "contents": bubbles
    }


def df_nhucau_to_image(df, outfile="static/table.png", title="Kết quả"):
    fig_h = len(df) * 0.2 + 1
    fig, ax = plt.subplots(figsize=(9, fig_h))
    ax.axis("off")

    ax.text(0.5, 1.02, title, ha="center", va="bottom", fontsize=13, weight="bold", transform=ax.transAxes)

    tbl = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        colLoc="center",
        cellLoc="left",
        colWidths=[0.45, 0.15, 0.15, 0.25],
        loc="upper center"
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.05, 1.15)

    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#4CAF50")
            cell.set_text_props(color="white", weight="bold")
            cell.set_height(0.5 / fig_h)
        elif r % 2 == 0:
            cell.set_facecolor("#f5f5f5")
            cell.set_height(0.35 / fig_h)
        elif r % 2 == 1:
            cell.set_facecolor("#ffffff")
            cell.set_height(0.35 / fig_h)

    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    plt.savefig(outfile, dpi=200, bbox_inches="tight", pad_inches=0.2)
    plt.close()
    return outfile

def df_nhapban_to_image(df, outfile="static/table.png", title="Kết quả"):
    if len(df) > 0:
        fig_h = len(df) * 0.2 + 1
        fig, ax = plt.subplots(figsize=(11, fig_h))
        ax.axis("off")

        ax.text(0.5, 1.02, title, ha="center", va="bottom", fontsize=13, weight="bold", transform=ax.transAxes)

        tbl = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            colLoc="center",
            cellLoc="left",
            colWidths=[0.22, 0.1, 0.1, 0.1, 0.1, 0.12, 0.12, 0.15],
            loc="upper center"
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(10)
        tbl.scale(1.05, 1.15)

        for (r, c), cell in tbl.get_celld().items():
            if r == 0:
                cell.set_facecolor("#4CAF50")
                cell.set_text_props(color="white", weight="bold")
                cell.set_height(0.5 / fig_h)
            else:
                cell.set_facecolor("#f5f5f5" if r % 2 == 0 else "#ffffff")
                cell.set_height(0.35 / fig_h)

                col_name = df.columns[c]
                if col_name == "% Bán/Nhập":
                    raw_val = str(df.iloc[r-1, c])
                    try:
                        num_val = float(raw_val.strip().replace("%", "")) / 100
                        if num_val < 0.8:
                            cell.set_facecolor("#ffb2b2")  # nền đỏ nhạt
                    except Exception:
                        pass

        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        plt.savefig(outfile, dpi=200, bbox_inches="tight", pad_inches=0.2)
        plt.close()
        return outfile
    else:
        return print("DataFrame is empty, cannot create image.")


# region Location / Nearest Store
_R_EARTH_KM = 6371.0088

def _haversine_km(lat1, lon1, lats2, lons2):
    lat1 = np.radians(lat1); lon1 = np.radians(lon1)
    lat2 = np.radians(lats2); lon2 = np.radians(lons2)
    dlat = lat2 - lat1; dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2.0)**2
    return 2*_R_EARTH_KM*np.arcsin(np.sqrt(a))

class StoreLocator:
    def __init__(self, path="data/location.parquet"):
        df = pd.read_parquet(path)
        df = df.rename(columns={'Mã siêu thị':'store_id', 'Vĩ độ':'lat', 'Kinh độ':'lon'})
        df = df[['store_id','lat','lon']].dropna()
        self.df = df
        self._lats = df['lat'].to_numpy()
        self._lons = df['lon'].to_numpy()

    def nearest(self, lat, lon, k=3, max_km=None):
        d = _haversine_km(lat, lon, self._lats, self._lons)
        k = min(k, len(d))
        idx = np.argpartition(d, kth=k-1)[:k]
        idx = idx[np.argsort(d[idx])]
        out = self.df.iloc[idx].copy()
        out['distance_km'] = d[idx]
        if max_km is not None:
            out = out[out['distance_km'] <= max_km]
        return out.reset_index(drop=True)

# lazy singleton
_LOCATOR = None
def init_store_locator(path="data/location.parquet"):
    global _LOCATOR
    _LOCATOR = StoreLocator(path)

def nearest_stores(lat, lon, k=3, max_km=30):
    global _LOCATOR
    if _LOCATOR is None:
        try:
            _LOCATOR = StoreLocator()  # mặc định đọc bhx_stores.parquet
        except Exception:
            return None
    return _LOCATOR.nearest(lat, lon, k=k, max_km=max_km)
# endregion