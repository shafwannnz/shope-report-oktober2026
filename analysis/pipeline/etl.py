"""ETL: Shopee Order.all export  ->  tabel bersih (line-level & order-level).

Temuan kualitas data yang ditangani di sini:
1. Seluruh kolom uang di Excel tersimpan sebagai TEKS berformat Indonesia
   ("60.999" = Rp 60.999). Jika dibaca langsung, pandas/Excel menganggapnya
   desimal (60,999) sehingga omzet salah 1000x. -> parse eksplisit.
2. Kolom level-pesanan (Total Pembayaran, voucher, ongkir) DIULANG pada setiap
   baris produk dalam satu pesanan. Menjumlahkannya per baris = double counting.
   -> dibuat tabel order-level (satu baris per No. Pesanan).
3. Data pribadi pembeli (nama, telepon, alamat, username) dihapus / di-hash
   sebelum disimpan, agar aman diunggah ke GitHub & database.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

MONEY_COLS = [
    "Harga Awal", "Harga Setelah Diskon", "Subtotal Pesanan", "Total Diskon",
    "Diskon Dari Penjual", "Diskon Dari Shopee", "Voucher Ditanggung Penjual",
    "Cashback Koin", "Voucher Ditanggung Shopee",
    "Paket Diskon (Diskon dari Shopee)", "Paket Diskon (Diskon dari Penjual)",
    "Potongan Koin Shopee", "Diskon Kartu Kredit",
    "Ongkos Kirim Dibayar oleh Pembeli", "Estimasi Potongan Biaya Pengiriman",
    "Ongkos Kirim Pengembalian Barang", "Total Pembayaran", "Perkiraan Ongkos Kirim",
]
TIME_COLS = {
    "Waktu Pesanan Dibuat": "created_at",
    "Waktu Pembayaran Dilakukan": "paid_at",
    "Waktu Pengiriman Diatur": "ship_arranged_at",
    "Waktu Pesanan Selesai": "completed_at",
}
SALT = "dobha-analytics-v1"  # hash buyer id; bukan rahasia kuat, hanya pseudonimisasi


def _parse_idr(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.fillna("0").astype(str).str.replace(".", "", regex=False).str.strip().replace("", "0"),
        errors="coerce",
    ).fillna(0)


def _status(s: str) -> str:
    if s.startswith("Pesanan diterima"):
        return "Diterima (masa retur)"
    return s


def _courier(opt: str) -> tuple[str, str]:
    o = opt.lower()
    carrier = next((c for c in ["SPX", "Anteraja", "JNE", "Pos", "J&T", "SiCepat"]
                    if c.lower() in o), "Lainnya")
    if "instant" in o:
        tier = "Instant"
    elif "same day" in o or "sameday" in o:
        tier = "Same Day"
    elif "hemat" in o or "economy" in o:
        tier = "Hemat"
    else:
        tier = "Reguler"
    return carrier, tier


def _category(sku: str, name: str) -> str:
    n = f"{sku} {name}".lower()
    if "not for sale" in n or sku == "NFS":
        return "Gift (NFS)"
    if "custom order" in n:
        return "Custom Order (Live)"
    if "roll on" in n or "6ml" in n:
        return "Roll On 6ml"
    if "pocket spray" in n or "pen spray" in n or re.search(r"\b(8|18)\s*ml", n):
        return "Pocket/Pen Spray 8-18ml"
    if re.search(r"\b(50|100|25|12)\s*ml", n) and "+" not in sku:
        return "Seri Premium 25-100ml"
    if "bundling" in n or "+" in sku:
        return "Bundling"
    if "70ml" in n or "70 ml" in n:
        return "EDP Premium 70ml"
    if "55ml" in n or "55 ml" in n:
        return "EDP 55ml"
    if "35ml" in n or "35 ml" in n:
        return "EDP 35ml"
    return "Lainnya"


def _family(sku: str) -> str:
    """Nama aroma tanpa ukuran, mis. 'Sabaya 55ml' -> 'Sabaya'."""
    f = re.sub(r"\b\d+\s*ml\b.*$", "", sku, flags=re.I).strip()
    return f or sku


def load_raw(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, dtype=str)


def build_lines(raw: pd.DataFrame) -> pd.DataFrame:
    d = raw.copy()
    for c in MONEY_COLS:
        d[c] = _parse_idr(d[c])
    for c in ["Jumlah", "Returned quantity", "Jumlah Produk di Pesan"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int)
    for src, dst in TIME_COLS.items():
        d[dst] = pd.to_datetime(d[src], errors="coerce")

    car = d["Opsi Pengiriman"].fillna("").map(_courier)
    out = pd.DataFrame({
        "order_id": d["No. Pesanan"],
        "status": d["Status Pesanan"].fillna("").map(_status),
        "created_at": d["created_at"], "paid_at": d["paid_at"],
        "ship_arranged_at": d["ship_arranged_at"], "completed_at": d["completed_at"],
        "payment_method": d["Metode Pembayaran"],
        "courier": car.map(lambda x: x[0]), "ship_tier": car.map(lambda x: x[1]),
        "sku": d["Nomor Referensi SKU"].fillna(d["Nama Produk"]).str.strip(),
        "product_name": d["Nama Produk"].str.replace("DOBHA PERFUMES ", "", regex=False).str.strip(),
        "unit_list_price": d["Harga Awal"], "unit_price": d["Harga Setelah Diskon"],
        "qty": d["Jumlah"], "returned_qty": d["Returned quantity"],
        "line_subtotal": d["Subtotal Pesanan"], "line_discount": d["Total Diskon"],
        # kolom level-pesanan (diulang per baris)
        "order_total_paid": d["Total Pembayaran"],
        "order_seller_voucher": d["Voucher Ditanggung Penjual"],
        "order_shopee_voucher": d["Voucher Ditanggung Shopee"],
        "order_coin_discount": d["Potongan Koin Shopee"],
        "order_shipping_fee_buyer": d["Ongkos Kirim Dibayar oleh Pembeli"],
        "order_shipping_deduction": d["Estimasi Potongan Biaya Pengiriman"],
        "city": d["Kota/Kabupaten"].str.title(), "province": d["Provinsi"].str.title(),
        "has_buyer_note": d["Catatan dari Pembeli"].fillna("").str.strip().ne(""),
        "buyer_id": d["Username (Pembeli)"].fillna("unknown").map(
            lambda u: hashlib.sha256((SALT + u).encode()).hexdigest()[:12]),
    })
    out["category"] = [_category(s, n) for s, n in zip(out["sku"], out["product_name"])]
    out["family"] = out["sku"].map(_family)
    out["is_gift"] = out["unit_price"].eq(0) | out["category"].eq("Gift (NFS)")
    out["is_cod"] = out["payment_method"].str.contains("COD", na=False)
    return out


def build_orders(lines: pd.DataFrame) -> pd.DataFrame:
    paid = lines[~lines["is_gift"]]
    g = lines.groupby("order_id")
    first = g.first()
    o = pd.DataFrame({
        "created_at": first["created_at"], "paid_at": first["paid_at"],
        "completed_at": first["completed_at"], "status": first["status"],
        "payment_method": first["payment_method"], "is_cod": first["is_cod"],
        "courier": first["courier"], "ship_tier": first["ship_tier"],
        "province": first["province"], "city": first["city"],
        "buyer_id": first["buyer_id"], "has_buyer_note": g["has_buyer_note"].max(),
        "total_paid": first["order_total_paid"],
        "seller_voucher": first["order_seller_voucher"],
        "shopee_voucher": first["order_shopee_voucher"],
        "coin_discount": first["order_coin_discount"],
        "shipping_fee_buyer": first["order_shipping_fee_buyer"],
        "n_lines": g.size(),
        "has_gift": g["is_gift"].max(),
    })
    o["items_revenue"] = paid.groupby("order_id")["line_subtotal"].sum()
    o["units"] = paid.groupby("order_id")["qty"].sum()
    o["discount_total"] = paid.groupby("order_id")["line_discount"].sum()
    o["list_value"] = (paid["unit_list_price"] * paid["qty"]).groupby(paid["order_id"]).sum()
    o[["items_revenue", "units", "discount_total", "list_value"]] = \
        o[["items_revenue", "units", "discount_total", "list_value"]].fillna(0)
    o["lag_pay_min"] = (o["paid_at"] - o["created_at"]).dt.total_seconds() / 60
    o["lag_complete_h"] = (o["completed_at"] - o["created_at"]).dt.total_seconds() / 3600
    return o.reset_index()


def run(raw_path: Path, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = build_lines(load_raw(raw_path))
    orders = build_orders(lines)
    lines.to_csv(out_dir / "lines.csv", index=False)
    orders.to_csv(out_dir / "orders.csv", index=False)
    return lines, orders
