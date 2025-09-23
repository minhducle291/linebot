import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
import textwrap

def df_to_image(df, outfile="static/table.png", title="Kết quả"):
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
            colWidths=[0.22, 0.1, 0.1, 0.1, 0.1, 0.12, 0.12],
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
            # elif r % 2 == 0:
            #     cell.set_facecolor("#f5f5f5")
            #     cell.set_height(0.35 / fig_h)
            # elif r % 2 == 1:
            #     cell.set_facecolor("#ffffff")
            #     cell.set_height(0.35 / fig_h)
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