"""Analisis deskriptif: pola, anomali, dan insight (semua angka dihitung, bukan ditulis tangan)."""
from __future__ import annotations

import itertools
from collections import Counter

import numpy as np
import pandas as pd

MIN_EXPORT_LAG_Q = 0.95  # kuantil lag kirim->selesai untuk menentukan jendela data lengkap


def _r(x, n=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def robust_z(s: pd.Series) -> pd.Series:
    """Skor-z robust (median & MAD) - tidak 'tertipu' oleh outlier yang sedang dicari."""
    med = s.median()
    mad = (s - med).abs().median() * 1.4826
    return (s - med) / (mad if mad else s.std(ddof=0) or 1)


def complete_window(orders: pd.DataFrame) -> dict:
    """Ekspor hanya memuat pesanan yang SUDAH diterima/selesai (tidak ada batal / dalam perjalanan).
    Akibatnya pesanan terbaru tersensor (right-censored): tampak 'turun' padahal belum terkirim.
    Batas jendela lengkap = waktu selesai terakhir - kuantil-95 lag pembuatan->selesai."""
    lag = orders["lag_complete_h"].dropna()
    q = float(lag.quantile(MIN_EXPORT_LAG_Q))
    cutoff = orders["completed_at"].max() - pd.Timedelta(hours=q)
    last_full_day = (cutoff.normalize() - pd.Timedelta(days=1)).date()
    return {
        "lag_median_h": _r(lag.median()), "lag_q95_h": _r(q),
        "export_last_completed": str(orders["completed_at"].max()),
        "censor_cutoff": str(cutoff), "last_full_day": str(last_full_day),
        "first_day": str(orders["created_at"].min().date()),
        "last_order_day": str(orders["created_at"].max().date()),
    }


def daily_table(orders: pd.DataFrame, last_full_day) -> pd.DataFrame:
    o = orders.assign(date=orders["created_at"].dt.normalize())
    days = pd.date_range(o["date"].min(), o["date"].max(), freq="D")
    d = o.groupby("date").agg(orders=("order_id", "nunique"), revenue=("items_revenue", "sum"),
                              units=("units", "sum"), buyers=("buyer_id", "nunique"))
    d = d.reindex(days, fill_value=0)
    d.index.name = "date"
    d["complete"] = d.index <= pd.Timestamp(last_full_day)
    d["aov"] = (d["revenue"] / d["orders"].replace(0, np.nan))
    d["orders_ma3"] = d["orders"].where(d["complete"]).rolling(3, min_periods=1).mean()
    d["z_orders"] = np.nan
    d.loc[d["complete"], "z_orders"] = robust_z(d.loc[d["complete"], "orders"])
    d["is_anomaly"] = d["z_orders"].abs() > 3.5
    d["weekday"] = d.index.day_name()
    return d.reset_index()


def analyse(lines: pd.DataFrame, orders: pd.DataFrame) -> dict:
    out: dict = {}
    win = complete_window(orders)
    out["window"] = win
    daily = daily_table(orders, win["last_full_day"])
    full = daily[daily["complete"]]
    spike_days = daily[daily["is_anomaly"] & (daily["z_orders"] > 0)]["date"]
    base_days = full[~full["date"].isin(spike_days)]
    paid_lines = lines[~lines["is_gift"]]

    # ---------- KPI ----------
    buyers = orders.groupby("buyer_id")["order_id"].nunique()
    out["kpi"] = {
        "orders": int(orders.shape[0]), "line_items": int(lines.shape[0]),
        "units": int(orders["units"].sum()),
        "revenue": float(orders["items_revenue"].sum()),
        "buyer_paid": float(orders["total_paid"].sum()),
        "aov": _r(orders["items_revenue"].mean(), 0),
        "aov_median": _r(orders["items_revenue"].median(), 0),
        "units_per_order": _r(orders["units"].mean(), 2),
        "discount_rate_pct": _r(orders["discount_total"].sum() / orders["list_value"].sum() * 100, 1),
        "unique_buyers": int(buyers.size),
        "repeat_buyer_pct": _r((buyers > 1).mean() * 100, 1),
        "cod_pct": _r(orders["is_cod"].mean() * 100, 1),
        "multi_item_pct": _r((orders["n_lines"] > 1).mean() * 100, 1),
        "skus": int(paid_lines["sku"].nunique()), "families": int(paid_lines["family"].nunique()),
        "provinces": int(orders["province"].nunique()), "cities": int(orders["city"].nunique()),
        "baseline_orders_per_day": _r(base_days["orders"].mean(), 1),
        "baseline_revenue_per_day": _r(base_days["revenue"].mean(), 0),
    }

    # ---------- pola waktu ----------
    out["daily"] = [{**r, "date": str(r["date"].date())} for r in
                    daily.replace({np.nan: None}).to_dict("records")]
    b = orders[orders["created_at"].dt.normalize().isin(pd.to_datetime(base_days["date"]))]
    hourly = b.groupby(b["created_at"].dt.hour)["order_id"].count().reindex(range(24), fill_value=0)
    out["hourly"] = {"hour": list(range(24)), "orders": [int(x) for x in hourly],
                     "share_pct": [_r(x / hourly.sum() * 100, 2) for x in hourly]}
    wd_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wd = base_days.groupby("weekday")["orders"].agg(["mean", "count"]).reindex(wd_order)
    out["weekday"] = [{"weekday": k, "avg_orders": _r(v["mean"]), "n_days": None if pd.isna(v["count"]) else int(v["count"])}
                      for k, v in wd.iterrows()]
    peak = hourly.rank(ascending=False).sort_values().index[:3]
    out["peak_hours"] = sorted(int(h) for h in peak)

    # ---------- produk ----------
    fam = paid_lines.groupby("family").agg(units=("qty", "sum"), revenue=("line_subtotal", "sum"),
                                           orders=("order_id", "nunique")).sort_values("revenue", ascending=False)
    fam["share_pct"] = fam["revenue"] / fam["revenue"].sum() * 100
    fam["cum_pct"] = fam["share_pct"].cumsum()
    n80 = int((fam["cum_pct"] < 80).sum() + 1)
    out["products"] = {
        "top_families": [{"family": i, **{k: _r(v, 1) for k, v in r.items()}} for i, r in fam.head(15).iterrows()],
        "n_families_for_80pct": n80, "n_families": int(len(fam)),
        "top3_share_pct": _r(fam["share_pct"].head(3).sum(), 1),
    }
    cat = paid_lines.groupby("category").agg(units=("qty", "sum"), revenue=("line_subtotal", "sum"),
                                             avg_price=("unit_price", "mean"))
    cat["share_pct"] = cat["revenue"] / cat["revenue"].sum() * 100
    out["category"] = [{"category": i, **{k: _r(v, 1) for k, v in r.items()}}
                       for i, r in cat.sort_values("revenue", ascending=False).iterrows()]
    sku = paid_lines.groupby("sku").agg(units=("qty", "sum"), revenue=("line_subtotal", "sum")) \
        .sort_values("units", ascending=False)
    out["top_skus"] = [{"sku": i, "units": int(r["units"]), "revenue": float(r["revenue"])} for i, r in sku.head(15).iterrows()]

    # ---------- pembayaran, kurir, geografi ----------
    pm = orders.groupby("payment_method").agg(orders=("order_id", "count"), aov=("items_revenue", "mean"),
                                              pay_lag_min=("lag_pay_min", "median"))
    pm["share_pct"] = pm["orders"] / pm["orders"].sum() * 100
    out["payment"] = [{"method": i, **{k: _r(v, 1) for k, v in r.items()}}
                      for i, r in pm.sort_values("orders", ascending=False).iterrows()]
    cr = orders.groupby(["courier", "ship_tier"]).agg(orders=("order_id", "count"),
                                                      lag_h=("lag_complete_h", "median")).reset_index()
    cr["share_pct"] = cr["orders"] / cr["orders"].sum() * 100
    out["courier"] = [{k: (_r(v, 1) if isinstance(v, float) else v) for k, v in r.items()}
                      for r in cr.sort_values("orders", ascending=False).to_dict("records")]
    prov = orders.groupby("province").agg(orders=("order_id", "count"), revenue=("items_revenue", "sum"),
                                          cod_pct=("is_cod", lambda s: s.mean() * 100),
                                          lag_h=("lag_complete_h", "median")).sort_values("orders", ascending=False)
    prov["share_pct"] = prov["orders"] / prov["orders"].sum() * 100
    out["province"] = [{"province": i, **{k: _r(v, 1) for k, v in r.items()}} for i, r in prov.head(12).iterrows()]
    city = orders.groupby("city")["order_id"].count().sort_values(ascending=False)
    out["city"] = [{"city": i, "orders": int(v), "share_pct": _r(v / city.sum() * 100, 1)} for i, v in city.head(10).items()]
    java = ["Jawa Barat", "Jawa Tengah", "Jawa Timur", "Banten", "Dki Jakarta", "Di Yogyakarta"]
    out["geo_summary"] = {"java_share_pct": _r(orders["province"].isin(java).mean() * 100, 1),
                          "hhi_province": _r(((prov["share_pct"] / 100) ** 2).sum(), 3)}

    # ---------- keranjang ----------
    multi = paid_lines.groupby("order_id")["family"].apply(lambda s: sorted(set(s)))
    pair_c, item_c = Counter(), Counter()
    for fams in multi:
        item_c.update(fams)
        pair_c.update(itertools.combinations(fams, 2))
    n_orders = len(multi)
    pairs = []
    for (a, c), n in pair_c.most_common(40):
        if n < 3:
            continue
        pairs.append({"a": a, "b": c, "orders": n, "support_pct": _r(n / n_orders * 100, 2),
                      "lift": _r((n / n_orders) / ((item_c[a] / n_orders) * (item_c[c] / n_orders)), 1)})
    out["basket"] = {"pairs": sorted(pairs, key=lambda x: -x["orders"])[:10],
                     "units_dist": {str(k): int(v) for k, v in orders["units"].clip(upper=6).value_counts().sort_index().items()},
                     "gift_attach_pct": _r(orders["has_gift"].mean() * 100, 1)}

    # ---------- diskon & kupon ----------
    out["discount"] = {
        "avg_depth_pct": _r((1 - paid_lines["unit_price"].sum() / paid_lines["unit_list_price"].sum()) * 100, 1),
        "seller_voucher_orders_pct": _r((orders["seller_voucher"] > 0).mean() * 100, 1),
        "shopee_voucher_orders_pct": _r((orders["shopee_voucher"] > 0).mean() * 100, 1),
        "coin_orders_pct": _r((orders["coin_discount"] > 0).mean() * 100, 1),
        "free_shipping_orders_pct": _r((orders["shipping_fee_buyer"] == 0).mean() * 100, 1),
    }

    # ---------- dampak promo (hari lonjakan vs baseline) ----------
    promo = []
    for dday in spike_days:
        s = orders[orders["created_at"].dt.normalize() == dday]
        prior = set(orders[orders["created_at"] < dday]["buyer_id"])
        sdl = paid_lines[paid_lines["order_id"].isin(s["order_id"])]
        top = sdl.groupby("family")["qty"].sum().sort_values(ascending=False).head(3)
        bf = paid_lines[paid_lines["order_id"].isin(b["order_id"])].groupby("family")["qty"].sum()
        bshare = bf / bf.sum()
        promo.append({
            "date": str(dday.date()), "orders": int(len(s)),
            "uplift_x": _r(len(s) / base_days["orders"].mean(), 2),
            "revenue": float(s["items_revenue"].sum()),
            "revenue_uplift_x": _r(s["items_revenue"].sum() / base_days["revenue"].mean(), 2),
            "aov": _r(s["items_revenue"].mean(), 0), "baseline_aov": _r(b["items_revenue"].mean(), 0),
            "cod_pct": _r(s["is_cod"].mean() * 100, 1), "baseline_cod_pct": _r(b["is_cod"].mean() * 100, 1),
            "new_buyer_pct": _r((~s["buyer_id"].isin(prior)).mean() * 100, 1),
            "top_families": [{"family": f, "units": int(u), "share_pct": _r(u / sdl["qty"].sum() * 100, 1),
                              "baseline_share_pct": _r(bshare.get(f, 0) * 100, 1)} for f, u in top.items()],
            "peak_hour": int(s["created_at"].dt.hour.value_counts().idxmax()),
        })
    out["promo_days"] = promo

    # ---------- pembeli ----------
    out["buyers"] = {
        "dist": {str(k): int(v) for k, v in buyers.clip(upper=4).value_counts().sort_index().items()},
        "top": [{"buyer_id": i, "orders": int(r["orders"]), "units": int(r["units"]), "revenue": float(r["rev"])}
                for i, r in orders.groupby("buyer_id").agg(orders=("order_id", "nunique"), units=("units", "sum"),
                                                           rev=("items_revenue", "sum")).sort_values("rev", ascending=False).head(10).iterrows()],
    }

    out["anomalies"] = detect_anomalies(lines, orders, daily, win)
    out["insights"] = build_insights(out)
    return out


def detect_anomalies(lines, orders, daily, win) -> list[dict]:
    A: list[dict] = []

    def add(kind, severity, title, detail, **extra):
        A.append({"kind": kind, "severity": severity, "title": title, "detail": detail, **extra})

    # 1. Lonjakan harian (robust z)
    for _, r in daily[daily["is_anomaly"]].iterrows():
        add("traffic", "info" if r["z_orders"] > 0 else "warning",
            f"{'Lonjakan' if r['z_orders'] > 0 else 'Penurunan'} pesanan {r['date'].date()}",
            f"{int(r['orders'])} pesanan (robust-z = {r['z_orders']:.1f}) vs median harian "
            f"{daily.loc[daily['complete'], 'orders'].median():.0f}.",
            date=str(r["date"].date()), score=_r(r["z_orders"], 2))

    # 2. Sensor data: hari terakhir tampak 'turun'
    cens = daily[~daily["complete"] & (daily["orders"] < daily.loc[daily["complete"], "orders"].median() * 0.6)]
    if len(cens):
        add("data_censoring", "warning", "Penurunan semu di akhir periode (data tersensor)",
            f"{len(cens)} hari terakhir ({cens['date'].min().date()} s.d. {cens['date'].max().date()}) hanya "
            f"{int(cens['orders'].sum())} pesanan. Ekspor hanya memuat pesanan berstatus diterima/selesai "
            f"(median {win['lag_median_h']:.0f} jam setelah dibuat), sehingga pesanan terbaru belum masuk. "
            f"Jangan tafsirkan sebagai penurunan permintaan.", score=None)

    # 3. Nilai pesanan outlier (Tukey)
    # nilai pesanan sangat miring ke kanan -> Tukey pada skala log
    v = orders[orders["items_revenue"] > 0]
    lv = np.log(v["items_revenue"])
    q1, q3 = lv.quantile([.25, .75]); iqr = q3 - q1
    hi = float(np.exp(q3 + 1.5 * iqr))
    big = v[v["items_revenue"] > hi].sort_values("items_revenue", ascending=False)
    if len(big):
        top = big.iloc[0]
        add("order_value", "info", f"{len(big)} pesanan bernilai ekstrem (> Rp {hi:,.0f})".replace(",", "."),
            f"Tukey 1,5xIQR pada skala log. Terbesar Rp {top['items_revenue']:,.0f} ({int(top['units'])} unit) di "
            f"{top['province']}; rata-rata nilai pesanan ekstrem {big['units'].mean():.1f} unit "
            f"- indikasi reseller/dropship atau bundling premium.".replace(",", "."),
            threshold=_r(hi, 0), n=int(len(big)))

    # 4. Pembeli dengan unit sangat banyak / pesan berulang di hari yang sama
    o = orders.assign(date=orders["created_at"].dt.date)
    rep = o.groupby(["buyer_id", "date"])["order_id"].nunique()
    rep = rep[rep >= 2]
    if len(rep):
        add("repeat_same_day", "warning", f"{len(rep)} pembeli membuat >=2 pesanan di hari yang sama",
            "Kemungkinan pesanan terpisah demi voucher/gratis ongkir, atau ongkir ganda. "
            f"Maksimum {int(rep.max())} pesanan dalam satu hari.", n=int(len(rep)))

    # 5. Harga satuan menyimpang dari harga normal SKU
    pl = lines[~lines["is_gift"]].copy()
    pl["ratio"] = pl["unit_price"] / pl["unit_list_price"]
    deep = pl[pl["ratio"] < 0.6]
    if len(deep):
        add("price_deep_discount", "warning", f"{len(deep)} baris dijual < 60% harga awal",
            "Diskon sangat dalam; periksa kesalahan harga / flash sale. Contoh: "
            + "; ".join(f"{r.sku} Rp {r.unit_price:,.0f} (awal Rp {r.unit_list_price:,.0f})".replace(",", ".")
                        for r in deep.head(3).itertuples()), n=int(len(deep)))
    mult = pl.groupby("sku")["unit_price"].nunique()
    n_mult = int((mult > 2).sum())
    if n_mult:
        add("price_dispersion", "info", f"{n_mult} SKU memiliki >2 level harga jual",
            "Harga satu SKU berbeda-beda antar pesanan (promo bertingkat/ perubahan harga). "
            "Pastikan marjin per level harga masih sehat.", n=n_mult)

    # 6. Kebersihan SKU: tanpa ukuran + nama aroma hampir kembar (typo)
    import difflib, re
    no_size = sorted(s_ for s_ in lines["sku"].unique() if not re.search(r"\d+\s*ml", s_, flags=re.I))
    fams = sorted(lines["family"].unique(), key=str.lower)
    near = []
    for a_, b_ in itertools.combinations(fams, 2):
        if re.sub(r"\d", "", a_.lower()) == re.sub(r"\d", "", b_.lower()) and a_.lower() != b_.lower():
            continue  # beda nomor seri saja (Bundling 001/002) bukan typo
        if difflib.SequenceMatcher(None, a_.lower(), b_.lower()).ratio() >= 0.85:
            near.append(f"{a_} ~ {b_}")
    if no_size or near:
        add("sku_hygiene", "warning", f"{len(no_size)} SKU tanpa ukuran & {len(near)} pasangan nama aroma mirip",
            "SKU tanpa ukuran: " + (", ".join(no_size[:5]) or "-") + ". Nama mirip (kemungkinan typo): "
            + ("; ".join(near[:5]) or "-") + ". Ini memecah agregasi per produk.",
            skus=no_size, near_duplicates=near)

    # 7. Lag pembayaran ekstrem (non-COD)
    nc = orders[~orders["is_cod"]]
    slow = nc[nc["lag_pay_min"] > 180]
    if len(slow):
        add("payment_lag", "info", f"{len(slow)} pesanan non-COD dibayar > 3 jam setelah dibuat",
            f"Median seluruh non-COD hanya {nc['lag_pay_min'].median():.0f} menit; maksimum {slow['lag_pay_min'].max()/60:.1f} jam. "
            "Berpotensi pembayaran tertunda / checkout ditinggalkan lalu diselesaikan.", n=int(len(slow)))

    # 8. Waktu kirim ekstrem per pesanan (robust z di dalam kurir)
    l = orders.dropna(subset=["lag_complete_h"]).copy()
    l["z"] = l.groupby("courier")["lag_complete_h"].transform(robust_z)
    late = l[l["z"] > 3.5]
    if len(late):
        add("delivery_lag", "warning", f"{len(late)} pesanan sangat lambat sampai",
            f"Lebih dari 3,5 MAD di atas median kurirnya; terlama {late['lag_complete_h'].max()/24:.1f} hari. "
            f"Provinsi tersering: {late['province'].value_counts().index[0]}.", n=int(len(late)))

    # 9. Lonjakan COD per provinsi
    p = orders.groupby("province").agg(n=("order_id", "count"), cod=("is_cod", "mean"))
    p = p[p["n"] >= 15]
    ov = orders["is_cod"].mean()
    for prov, r in p.iterrows():
        se = (ov * (1 - ov) / r["n"]) ** .5
        if (r["cod"] - ov) / se > 3:
            add("cod_concentration", "warning", f"COD tinggi di {prov}",
                f"{r['cod']*100:.0f}% pesanan COD (rata-rata {ov*100:.0f}%, n={int(r['n'])}). Risiko retur/ gagal antar lebih besar.",
                province=prov)

    # 10. Kualitas data: baris produk gratis (NFS) & pesanan Rp 0
    free = orders[orders["items_revenue"] == 0]
    if len(free):
        add("zero_revenue", "info", f"{len(free)} pesanan bernilai produk Rp 0", "Hanya berisi gift/NFS.", n=int(len(free)))
    return A


def build_insights(R: dict) -> list[dict]:
    k, I = R["kpi"], []
    pr = R["products"]["top_families"]
    I.append({"area": "Produk", "title": "Pendapatan terkonsentrasi pada sedikit aroma",
              "body": f"{R['products']['n_families_for_80pct']} dari {R['products']['n_families']} aroma menghasilkan 80% omzet; "
                      f"tiga teratas ({', '.join(x['family'] for x in pr[:3])}) = {R['products']['top3_share_pct']}%.",
              "action": "Jaga stok dan iklan pada aroma inti; evaluasi ekor panjang yang jarang laku."})
    cat = R["category"][0]
    I.append({"area": "Produk", "title": f"Kategori {cat['category']} mendominasi",
              "body": f"{cat['share_pct']}% omzet dengan harga rata-rata Rp {cat['avg_price']:,.0f}.".replace(",", "."),
              "action": "Uji bundling lintas ukuran (35ml + roll-on) untuk menaikkan nilai pesanan."})
    for pdy in R["promo_days"]:
        I.append({"area": "Promo", "title": f"Kampanye {pdy['date']} melipatgandakan pesanan {pdy['uplift_x']}x",
                  "body": f"{pdy['orders']} pesanan (omzet {pdy['revenue_uplift_x']}x baseline) dengan AOV Rp {pdy['aov']:,.0f} "
                          f"vs Rp {pdy['baseline_aov']:,.0f} normal; {pdy['new_buyer_pct']}% pembeli baru; puncak jam {pdy['peak_hour']}:00.".replace(",", "."),
                  "action": "Siapkan stok & kapasitas packing sebelum tanggal kembar (11.11, 12.12) berdasar uplift ini."})
    hrs = R["peak_hours"]
    I.append({"area": "Waktu", "title": "Jam puncak pesanan",
              "body": f"Jam {', '.join(str(h)+':00' for h in hrs)} memuat "
                      f"{sum(R['hourly']['share_pct'][h] for h in hrs):.0f}% pesanan hari biasa.",
              "action": "Jadwalkan voucher toko, live, dan balasan chat tepat sebelum jam tersebut."})
    top = R["payment"][0]
    I.append({"area": "Pembayaran", "title": f"{k['cod_pct']}% pesanan memakai COD",
              "body": f"Metode terbanyak: {top['method']} ({top['share_pct']}%). COD memengaruhi arus kas dan risiko retur.",
              "action": "Beri insentif pembayaran digital (voucher kecil) untuk menurunkan porsi COD."})
    I.append({"area": "Geografi", "title": f"{R['geo_summary']['java_share_pct']}% pesanan berasal dari Pulau Jawa",
              "body": f"{R['province'][0]['province']} sendiri {R['province'][0]['share_pct']}%.",
              "action": "Kirim dari gudang/kurir tercepat ke Jabar-Banten-Jakarta; uji iklan area luar Jawa."})
    I.append({"area": "Pelanggan", "title": f"Repeat buyer baru {k['repeat_buyer_pct']}%",
              "body": f"{k['unique_buyers']} pembeli unik untuk {k['orders']} pesanan; {k['multi_item_pct']}% pesanan berisi >1 produk.",
              "action": "Kirim voucher follow-up (chat/koin) untuk pembelian ulang 30 hari."})
    I.append({"area": "Data", "title": "Ekspor tersensor di ujung periode",
              "body": f"Gunakan data s.d. {R['window']['last_full_day']} untuk tren & prediksi; hari sesudahnya belum lengkap.",
              "action": "Unduh ulang laporan 7-9 hari setelah tanggal akhir, atau sertakan pesanan 'sedang dikirim'."})
    return I
