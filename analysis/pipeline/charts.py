"""Grafik: Plotly (interaktif, JSON untuk Laravel) + Matplotlib/Seaborn (PNG statis untuk laporan)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns

# Palet kategorikal tervalidasi (dataviz skill) + ink netral
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e7e6e2", "#fcfcfb"
RP = lambda x: f"Rp {x/1e6:,.1f} jt".replace(",", ".")


def _style():
    sns.set_theme(style="white", rc={
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK, "xtick.color": INK2,
        "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": .8, "font.size": 10.5,
        "axes.titleweight": "semibold", "axes.titlesize": 12.5, "axes.titlelocation": "left",
        "legend.frameon": False})


def _pl(fig, h=340):
    fig.update_layout(
        height=h, margin=dict(l=48, r=16, t=16, b=40), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK2),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False), yaxis=dict(gridcolor=GRID, linecolor=GRID, zeroline=False),
        legend=dict(orientation="h", y=1.12, x=0), hoverlabel=dict(bgcolor="#fff", font_color=INK, bordercolor=GRID))
    return fig


def _j(fig) -> dict:
    return json.loads(fig.to_json())


# ------------------------------------------------------------------ PLOTLY
def plotly_charts(R: dict, S: dict) -> list[dict]:
    d = pd.DataFrame(R["daily"])
    ch = []

    # 1. tren harian + anomali + area tersensor
    f = go.Figure()
    comp = d[d["complete"]]
    cens = d[~d["complete"]]
    f.add_bar(x=d["date"].tolist(), y=d["orders"].tolist(), name="Pesanan/hari", marker_color=[
        ORANGE if a else (BLUE if c else "#c9c8c3") for a, c in zip(d["is_anomaly"], d["complete"])],
        hovertemplate="%{x}<br>%{y} pesanan<extra></extra>")
    f.add_scatter(x=comp["date"].tolist(), y=comp["orders_ma3"].round(1).tolist(), name="Rata-rata 3 hari",
                  mode="lines", line=dict(color=INK, width=2), hovertemplate="MA3: %{y}<extra></extra>")
    if len(cens):
        f.add_vrect(x0=cens["date"].iloc[0], x1=cens["date"].iloc[-1], fillcolor="#e7e6e2", opacity=.5, line_width=0,
                    annotation_text="Data tersensor", annotation_position="top left", annotation_font_color=INK2)
    f.update_layout(bargap=.25)
    ch.append({"slug": "daily-orders", "title": "Pesanan harian",
               "subtitle": "Oranye = anomali (robust-z > 3,5). Abu-abu = periode tersensor, jangan dibaca sebagai penurunan.",
               "figure": _j(_pl(f))})

    # 2. pola jam
    f = go.Figure(go.Bar(x=[f"{h:02d}:00" for h in R["hourly"]["hour"]], y=R["hourly"]["share_pct"],
                         marker_color=[ORANGE if h in R["peak_hours"] else BLUE for h in R["hourly"]["hour"]],
                         hovertemplate="%{x}<br>%{y:.1f}% pesanan<extra></extra>"))
    f.update_layout(yaxis_title="% pesanan", bargap=.2)
    ch.append({"slug": "hourly", "title": "Pola pesanan per jam (hari baseline)",
               "subtitle": "Oranye = tiga jam tersibuk.", "figure": _j(_pl(f))})

    # 3. produk teratas
    t = R["products"]["top_families"][:10][::-1]
    f = go.Figure(go.Bar(y=[x["family"] for x in t], x=[x["revenue"] / 1e6 for x in t], orientation="h", marker_color=BLUE,
                         hovertemplate="%{y}<br>Rp %{x:.1f} jt<extra></extra>"))
    f.update_layout(xaxis_title="Omzet (Rp juta)", margin=dict(l=110, r=16, t=16, b=40))
    ch.append({"slug": "top-products", "title": "10 aroma teratas menurut omzet",
               "subtitle": f"{R['products']['n_families_for_80pct']} dari {R['products']['n_families']} aroma = 80% omzet.",
               "figure": _j(_pl(f, 380))})

    # 4. kategori
    c = R["category"][::-1]
    f = go.Figure(go.Bar(y=[x["category"] for x in c], x=[x["share_pct"] for x in c], orientation="h", marker_color=AQUA,
                         hovertemplate="%{y}<br>%{x:.1f}% omzet<extra></extra>"))
    f.update_layout(xaxis_title="% omzet", margin=dict(l=150, r=16, t=16, b=40))
    ch.append({"slug": "category", "title": "Bauran omzet per kategori", "subtitle": "Menurut jenis & ukuran produk.",
               "figure": _j(_pl(f, 320))})

    # 5. pembayaran
    p = R["payment"][::-1]
    f = go.Figure(go.Bar(y=[x["method"] for x in p], x=[x["share_pct"] for x in p], orientation="h",
                         marker_color=[ORANGE if "COD" in x["method"] else BLUE for x in p],
                         hovertemplate="%{y}<br>%{x:.1f}% pesanan<extra></extra>"))
    f.update_layout(xaxis_title="% pesanan", margin=dict(l=150, r=16, t=16, b=40))
    ch.append({"slug": "payment", "title": "Metode pembayaran", "subtitle": "COD disorot (risiko retur & arus kas).",
               "figure": _j(_pl(f, 320))})

    # 6. provinsi
    pr = R["province"][:10][::-1]
    f = go.Figure(go.Bar(y=[x["province"] for x in pr], x=[x["share_pct"] for x in pr], orientation="h", marker_color=BLUE,
                         customdata=[x["cod_pct"] for x in pr],
                         hovertemplate="%{y}<br>%{x:.1f}% pesanan<br>COD %{customdata:.0f}%<extra></extra>"))
    f.update_layout(xaxis_title="% pesanan", margin=dict(l=130, r=16, t=16, b=40))
    ch.append({"slug": "province", "title": "10 provinsi teratas", "subtitle": "Arahkan kursor untuk porsi COD.",
               "figure": _j(_pl(f, 360))})

    # 7. simulasi: omzet harian skenario
    f = go.Figure()
    for key, color, name in (("baseline", BLUE, "Baseline"), ("promo", ORANGE, "Ada kampanye 11.11")):
        sc = S["scenarios"][key]
        f.add_scatter(x=S["dates"], y=[v / 1e6 for v in sc["daily_revenue_p95"]], mode="lines", line=dict(width=0),
                      showlegend=False, hoverinfo="skip")
        f.add_scatter(x=S["dates"], y=[v / 1e6 for v in sc["daily_revenue_p5"]], mode="lines", line=dict(width=0),
                      fill="tonexty", fillcolor="rgba(42,120,214,.15)" if key == "baseline" else "rgba(235,104,52,.15)",
                      showlegend=False, hoverinfo="skip")
        f.add_scatter(x=S["dates"], y=[v / 1e6 for v in sc["daily_revenue_mean"]], mode="lines", name=name,
                      line=dict(color=color, width=2), hovertemplate="%{x}<br>Rp %{y:.1f} jt (rata-rata)<extra></extra>")
    f.update_layout(yaxis_title="Omzet harian (Rp juta)")
    ch.append({"slug": "sim-daily", "title": "Simulasi omzet harian, 21 hari ke depan",
               "subtitle": f"Garis = rata-rata {S['n_rep']:,} replikasi; pita = persentil 5-95.".replace(",", "."),
               "figure": _j(_pl(f))})

    # 8. simulasi: distribusi omzet total
    f = go.Figure()
    for key, color, name in (("baseline", BLUE, "Baseline"), ("promo", ORANGE, "Ada kampanye 11.11")):
        f.add_histogram(x=S["scenarios"][key]["rev_samples"], name=name, marker_color=color, opacity=.7, nbinsx=30,
                        hovertemplate="Rp %{x} jt<br>%{y} replikasi<extra></extra>")
    f.update_layout(barmode="overlay", xaxis_title="Total omzet 21 hari (Rp juta)", yaxis_title="Replikasi (sampel)")
    ch.append({"slug": "sim-dist", "title": "Distribusi total omzet 21 hari",
               "subtitle": "Sebaran hasil Monte Carlo untuk dua skenario.", "figure": _j(_pl(f))})
    return ch


# ------------------------------------------------------------- MATPLOTLIB / SEABORN
def static_charts(lines: pd.DataFrame, orders: pd.DataFrame, R: dict, S: dict, out: Path) -> list[dict]:
    _style()
    out.mkdir(parents=True, exist_ok=True)
    made = []

    def save(fig, name, title, note):
        fig.savefig(out / f"{name}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        made.append({"file": f"{name}.png", "title": title, "note": note})

    d = pd.DataFrame(R["daily"]); d["date"] = pd.to_datetime(d["date"])

    # 1 tren + anotasi (matplotlib)
    fig, ax = plt.subplots(figsize=(9, 3.8))
    cols = [ORANGE if a else (BLUE if c else "#c9c8c3") for a, c in zip(d["is_anomaly"], d["complete"])]
    ax.bar(d["date"], d["orders"], color=cols, width=.72)
    ax.plot(d.loc[d["complete"], "date"], d.loc[d["complete"], "orders_ma3"], color=INK, lw=1.8, label="Rata-rata 3 hari")
    for _, r in d[d["is_anomaly"]].iterrows():
        ax.annotate(f"{int(r['orders'])} pesanan\n(promo 10.10)", (r["date"], r["orders"]), xytext=(8, -6), textcoords="offset points",
                    fontsize=9, color=INK2, va="top")
    ax.set_title("Pesanan harian dan anomali"); ax.set_ylabel("Pesanan"); ax.legend(loc="upper right")
    fig.autofmt_xdate()
    save(fig, "01_daily_trend", "Tren pesanan harian", "Oranye: anomali; abu-abu: data tersensor.")

    # 2 heatmap tanggal x jam (seaborn)
    o = orders.assign(date=orders["created_at"].dt.strftime("%d %b"), hour=orders["created_at"].dt.hour)
    hm = o.pivot_table(index="date", columns="hour", values="order_id", aggfunc="count", fill_value=0)
    order = sorted(hm.index, key=lambda s: pd.to_datetime(s + " 2026"))
    hm = hm.loc[order]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    sns.heatmap(hm, cmap=sns.light_palette(BLUE, as_cmap=True), ax=ax, linewidths=.6, linecolor=SURFACE,
                cbar_kws={"label": "Pesanan"}, annot=False)
    ax.set_title("Intensitas pesanan: tanggal x jam"); ax.set_xlabel("Jam"); ax.set_ylabel("")
    save(fig, "02_heatmap_date_hour", "Heatmap tanggal x jam", "Lonjakan 10 Okt tepat tengah malam (flash sale) tampak jelas.")

    # 3 boxplot nilai pesanan per kategori dominan (seaborn)
    pl = lines[~lines["is_gift"]]
    main = pl["category"].value_counts().head(6).index
    fig, ax = plt.subplots(figsize=(9, 4.2))
    sns.boxplot(data=pl[pl["category"].isin(main)], y="category", x="unit_price", ax=ax, color=BLUE, fliersize=2.5,
                linewidth=1, order=main, boxprops=dict(alpha=.75))
    ax.set_xscale("log"); ax.set_title("Sebaran harga jual satuan per kategori (skala log)")
    ax.set_xlabel("Harga satuan (Rp, skala log)"); ax.set_ylabel("")
    save(fig, "03_price_box", "Sebaran harga per kategori", "Titik di luar kotak = harga menyimpang / bundling.")

    # 4 lag pengiriman per kurir (seaborn violin)
    l = orders.dropna(subset=["lag_complete_h"]); l = l[l["courier"].isin(l["courier"].value_counts().head(4).index)]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    sns.violinplot(data=l, x="courier", y=l["lag_complete_h"] / 24, ax=ax, color=AQUA, inner="quartile", cut=0, linewidth=1)
    ax.set_title("Lama pesanan sampai (hari) menurut kurir"); ax.set_ylabel("Hari sejak dibuat"); ax.set_xlabel("")
    save(fig, "04_delivery_violin", "Waktu sampai per kurir", "Ekor panjang = pengiriman lambat (terutama luar Jawa).")

    # 5 korelasi (seaborn)
    num = orders[["items_revenue", "units", "discount_total", "shipping_fee_buyer", "shopee_voucher", "n_lines", "lag_complete_h"]].copy()
    num.columns = ["Omzet item", "Unit", "Diskon", "Ongkir pembeli", "Voucher Shopee", "Jumlah baris", "Lama sampai (jam)"]
    fig, ax = plt.subplots(figsize=(6.8, 5.4))
    sns.heatmap(num.corr(method="spearman"), annot=True, fmt=".2f", cmap=sns.diverging_palette(250, 25, as_cmap=True), center=0,
                vmin=-1, vmax=1, ax=ax, linewidths=.6, linecolor=SURFACE, cbar_kws={"label": "Korelasi Spearman"})
    ax.set_title("Korelasi antar-variabel pesanan")
    save(fig, "05_correlation", "Korelasi variabel pesanan", "Spearman dipilih karena distribusi miring.")

    # 6 Pareto (matplotlib; batang & kumulatif sama-sama %, satu sumbu)
    fam = R["products"]["top_families"]
    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(fam))
    ax.bar(x, [f["share_pct"] for f in fam], color=BLUE, width=.7, label="Porsi omzet (%)")
    ax.plot(x, [f["cum_pct"] for f in fam], color=ORANGE, marker="o", ms=4.5, lw=2, label="Kumulatif (%)")
    ax.set_xticks(x, [f["family"] for f in fam], rotation=40, ha="right"); ax.set_ylabel("%")
    ax.set_title("Pareto aroma (15 teratas)"); ax.legend(loc="center right")
    save(fig, "06_pareto", "Pareto produk", "Konsentrasi omzet pada aroma inti.")

    # 7 Monte Carlo (seaborn hist+kde)
    fig, ax = plt.subplots(figsize=(9, 3.9))
    for key, color, name in (("baseline", BLUE, "Baseline"), ("promo", ORANGE, "Ada kampanye 11.11")):
        sns.histplot(S["scenarios"][key]["rev_samples"], color=color, kde=True, stat="density", alpha=.45, ax=ax, label=name, bins=28,
                     line_kws={"linewidth": 2})
    ax.set_title("Distribusi total omzet 21 hari (Monte Carlo)"); ax.set_xlabel("Rp juta"); ax.legend()
    save(fig, "07_monte_carlo", "Distribusi omzet hasil simulasi", "Seed tetap; 5.000 replikasi.")
    return made
