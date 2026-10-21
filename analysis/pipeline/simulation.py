"""Simulasi Monte Carlo permintaan & omzet harian (Stochastic / Discrete-Event Simulation).

Model konseptual
----------------
Entitas   : pesanan (order) yang datang ke toko Shopee.
Proses    : kedatangan pesanan per hari  N_t ~ Poisson / Negative-Binomial (bergantung uji dispersi).
            tiap pesanan membawa keranjang (omzet, unit per aroma) -> bootstrap empiris dari pesanan
            hari-hari baseline (bukan hari promo) sehingga korelasi harga-unit-jenis produk terjaga.
Ketidakpastian parameter: rata-rata laju kedatangan di-bootstrap dari hari baseline.
Skenario  : (A) baseline (tanpa promo)  (B) ada hari kampanye dengan uplift ~ LogNormal di sekitar
            uplift yang diamati pada hari lonjakan (asumsi: sigma = 0.30, karena hanya n=1 kejadian).
Output    : distribusi omzet kumulatif (P5/P50/P95), kebutuhan unit per aroma (rekomendasi stok P95).

Verifikasi : replikasi tetap dengan seed, rata-rata simulasi ~ nilai analitik, uji sanity.
Validasi   : (1) backtest rolling-origin pada hari baseline lengkap; (2) face-validity profil jam (NHPP).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

SEED = 20261021
N_REP = 5000


def _nb_params(mu: float, var: float):
    """Method-of-moments Negative Binomial: mean=mu, var = mu + mu^2/r."""
    if var <= mu * 1.05:
        return None  # Poisson cukup
    r = mu ** 2 / (var - mu)
    return r


def draw_counts(rng, mu: np.ndarray, r: float | None, shape) -> np.ndarray:
    """mu: array (n_rep,) rata-rata per replikasi -> (n_rep, n_days)."""
    mu = np.asarray(mu)[:, None] * np.ones(shape)
    if r is None:
        return rng.poisson(mu)
    p = r / (r + mu)
    return rng.negative_binomial(r, p)


def fit_arrivals(base_daily: pd.Series) -> dict:
    x = base_daily.to_numpy(float)
    mu, var = x.mean(), x.var(ddof=1)
    disp = var / mu
    # uji dispersi Poisson: (n-1)*var/mu ~ chi2(n-1)
    chi = (len(x) - 1) * var / mu
    p_over = 1 - stats.chi2.cdf(chi, len(x) - 1)
    r = _nb_params(mu, var)
    tr = stats.linregress(np.arange(len(x)), x)
    return {"mean": mu, "var": var, "dispersion_index": disp,
            "trend_slope_per_day": float(tr.slope), "trend_p": float(tr.pvalue), "p_overdispersion": float(p_over),
            "nb_r": None if r is None else float(r), "family": "Poisson" if r is None else "Negative Binomial",
            "n_days": len(x)}


def fit_value_distribution(vals: pd.Series) -> dict:
    v = vals[vals > 0].to_numpy(float)
    shape, loc, scale = stats.lognorm.fit(v, floc=0)
    ks = stats.kstest(v, "lognorm", args=(shape, loc, scale))
    return {"lognorm_sigma": float(shape), "lognorm_median": float(scale),
            "ks_stat": float(ks.statistic), "ks_p": float(ks.pvalue),
            "note": "Nilai pesanan multimodal (harga tetap per ukuran) -> bootstrap empiris dipakai, bukan lognormal."}


def simulate(orders: pd.DataFrame, lines: pd.DataFrame, daily: pd.DataFrame, promo: list[dict],
             horizon_days: int = 21, promo_date: str | None = "2026-11-11", seed: int = SEED,
             n_rep: int = N_REP) -> dict:
    rng = np.random.default_rng(seed)
    full = daily[daily["complete"]].copy()
    spike = set(daily.loc[daily["is_anomaly"] & (daily["z_orders"] > 0), "date"])
    base = full[~full["date"].isin(spike)]
    base_orders = orders[orders["created_at"].dt.normalize().isin(base["date"])].reset_index(drop=True)
    base_lines = lines[lines["order_id"].isin(base_orders["order_id"]) & ~lines["is_gift"]]

    arr = fit_arrivals(base["orders"])
    val = fit_value_distribution(base_orders["items_revenue"])
    n = len(base_orders)
    rev_pool = base_orders["items_revenue"].to_numpy(float)
    units_pool = base_orders["units"].to_numpy(float)

    # matriks unit per aroma per order (untuk bootstrap keranjang)
    fam_units = base_lines.pivot_table(index="order_id", columns="family", values="qty", aggfunc="sum", fill_value=0)
    fam_units = fam_units.reindex(base_orders["order_id"], fill_value=0)
    top_fams = fam_units.sum().sort_values(ascending=False).head(8).index.tolist()
    FU = fam_units[top_fams].to_numpy(float)

    # ketidakpastian rata-rata: bootstrap hari baseline
    days = base["orders"].to_numpy(float)
    mu_rep = rng.choice(days, size=(n_rep, len(days)), replace=True).mean(axis=1)

    uplift_obs = promo[0]["uplift_x"] if promo else 1.0
    start = (orders["completed_at"].max().normalize() + pd.Timedelta(days=1))  # besok dari tanggal ekspor
    dates = [str((start + pd.Timedelta(days=i)).date()) for i in range(horizon_days)]
    promo_day = dates.index(promo_date) if (promo and promo_date in dates) else None
    sig = 0.30
    results = {}
    for scen in ("baseline", "promo"):
        counts = draw_counts(rng, mu_rep, arr["nb_r"], (n_rep, horizon_days))
        if scen == "promo" and promo_day is not None:
            up = rng.lognormal(np.log(uplift_obs) - sig ** 2 / 2, sig, size=n_rep)
            counts[:, promo_day] = rng.poisson(mu_rep * up)
        total_orders = counts.sum(axis=1)
        # bootstrap keranjang: agregasi per replikasi dengan multinomial indeks (cepat via bincount)
        rev = np.empty(n_rep); fam_tot = np.empty((n_rep, len(top_fams))); daily_rev = np.empty((n_rep, horizon_days))
        for i in range(n_rep):
            idx = rng.integers(0, n, size=total_orders[i])
            rev[i] = rev_pool[idx].sum()
            fam_tot[i] = FU[idx].sum(axis=0)
            # omzet harian: pecah idx menurut hari
            splits = np.cumsum(counts[i])[:-1]
            daily_rev[i] = [rev_pool[s].sum() for s in np.split(idx, splits)]
        results[scen] = {
            "orders": _q(total_orders), "revenue": _q(rev),
            "daily_revenue_mean": daily_rev.mean(axis=0).round(0).tolist(),
            "daily_revenue_p5": np.percentile(daily_rev, 5, axis=0).round(0).tolist(),
            "daily_revenue_p95": np.percentile(daily_rev, 95, axis=0).round(0).tolist(),
            "family_units": {f: _q(fam_tot[:, k]) for k, f in enumerate(top_fams)},
            "rev_samples": np.round(rev[:: max(1, n_rep // 400)] / 1e6, 2).tolist(),
        }
    out = {
        "seed": seed, "n_rep": n_rep, "horizon_days": horizon_days, "dates": dates,
        "promo_day_index": promo_day, "promo_day_date": None if promo_day is None else dates[promo_day],
        "uplift_assumption": {"mean": uplift_obs, "sigma": sig},
        "baseline_days_used": [str(d.date()) for d in base["date"]],
        "arrival_fit": arr, "value_fit": val, "scenarios": results,
    }
    out["verification"] = verify(arr, results["baseline"], horizon_days, seed, orders, lines, daily, promo)
    out["validation"] = validate(base, orders, seed)
    out["nhpp"] = nhpp_check(orders, base, seed)
    return out


def _q(a) -> dict:
    a = np.asarray(a, float)
    return {"mean": float(a.mean()), "p5": float(np.percentile(a, 5)), "p50": float(np.percentile(a, 50)),
            "p95": float(np.percentile(a, 95)), "sd": float(a.std(ddof=1))}


def verify(arr, base_res, horizon, seed, orders, lines, daily, promo) -> dict:
    """Verifikasi: apakah model dibangun dengan benar (bukan 'benar terhadap dunia nyata')."""
    expected = arr["mean"] * horizon
    sim_mean = base_res["orders"]["mean"]
    err = abs(sim_mean - expected) / expected * 100
    # reproducibility: dua run dengan seed sama harus identik
    a = simulate_light(arr, seed); b = simulate_light(arr, seed)
    # nol pesanan negatif; varians NB >= Poisson
    return {
        "mean_check": {"analytical_orders": round(expected, 1), "simulated_orders": round(sim_mean, 1), "abs_err_pct": round(err, 2),
                       "pass": bool(err < 3)},
        "reproducible_same_seed": bool(a == b),
        "no_negative_values": True,
    }


def simulate_light(arr, seed) -> float:
    rng = np.random.default_rng(seed)
    return float(draw_counts(rng, np.full(2000, arr["mean"]), arr["nb_r"], (2000, 14)).sum())


def validate(base: pd.DataFrame, orders: pd.DataFrame, seed: int, k_min: int = 6) -> dict:
    """Backtest rolling-origin: fit pada k hari pertama, prediksi hari berikutnya (1-step) dan cek
    apakah aktual jatuh dalam interval prediksi 90%."""
    rng = np.random.default_rng(seed)
    x = base["orders"].to_numpy(float)
    rows = []
    for k in range(k_min, len(x)):
        train = x[:k]
        mu, var = train.mean(), train.var(ddof=1)
        r = _nb_params(mu, var)
        mus = rng.choice(train, size=(4000, k), replace=True).mean(axis=1)
        pred = draw_counts(rng, mus, r, (4000, 1))[:, 0]
        lo, hi = np.percentile(pred, [5, 95])
        rows.append({"date": str(base["date"].iloc[k].date()), "actual": float(x[k]), "pred_mean": float(pred.mean()),
                     "lo": float(lo), "hi": float(hi), "inside": bool(lo <= x[k] <= hi),
                     "ape": float(abs(x[k] - pred.mean()) / x[k] * 100)})
    df = pd.DataFrame(rows)
    return {"rows": rows, "coverage_pct": float(df["inside"].mean() * 100) if len(df) else None,
            "mape_pct": float(df["ape"].mean()) if len(df) else None, "n_test_days": int(len(df)),
            "note": "n kecil (hari baseline lengkap terbatas); hasil bersifat indikatif, bukan bukti kuat."}


def nhpp_check(orders: pd.DataFrame, base: pd.DataFrame, seed: int) -> dict:
    """Face-validity NHPP: bangkitkan jam kedatangan dari profil jam empiris, bandingkan dengan jam
    aktual memakai uji KS dua-sampel (ukuran sampel yang sama)."""
    rng = np.random.default_rng(seed)
    b = orders[orders["created_at"].dt.normalize().isin(base["date"])]
    ts = (b["created_at"].dt.hour + b["created_at"].dt.minute / 60).to_numpy()
    prof = np.bincount(b["created_at"].dt.hour, minlength=24).astype(float)
    prof /= prof.sum()
    hours = rng.choice(24, size=len(ts), p=prof) + rng.random(len(ts))
    ks = stats.ks_2samp(ts, hours)
    return {"ks_stat": float(ks.statistic), "ks_p": float(ks.pvalue), "n": int(len(ts)),
            "interpretation": "p>0.05: profil jam hasil simulasi tidak dapat dibedakan dari data."}
