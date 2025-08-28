import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

def df_to_image(df, outfile="static/table.png", title="Kết quả"):
    fig_h = 0.2 * len(df)
    fig, ax = plt.subplots(figsize=(9, fig_h))
    ax.axis("off")

    ax.text(0.5, 1.02, title, ha="center", va="bottom", fontsize=13, weight="bold", transform=ax.transAxes)

    tbl = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        colLoc="center",
        cellLoc="left",
        colWidths=[0.15, 0.4, 0.1, 0.1, 0.25],
        loc="upper center"
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1.05, 1.15)

    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#4CAF50")
            cell.set_text_props(color="white", weight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#f7f7f7")

    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    plt.savefig(outfile, dpi=200, bbox_inches="tight", pad_inches=0.2)
    plt.close()
    return outfile
