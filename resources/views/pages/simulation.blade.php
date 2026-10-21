@extends('layouts.app')
@section('title', 'Simulasi')
@php
    use App\Support\Fmt;
    $b = $s['scenarios']['baseline'] ?? null; $p = $s['scenarios']['promo'] ?? null;
    $af = $s['arrival_fit'] ?? []; $v = $s['verification'] ?? []; $val = $s['validation'] ?? [];
@endphp
@section('content')
    <h1 class="text-2xl font-semibold tracking-tight">Simulasi Monte Carlo</h1>
    @if (! $b)
        <p class="mt-2 text-sm text-ink-2">Belum ada data. Jalankan <code>php artisan dobha:import</code>.</p>
    @else
    <p class="mt-1 text-sm text-ink-2">
        Proyeksi {{ $s['horizon_days'] }} hari ({{ $s['dates'][0] }} – {{ end($s['dates']) }}) dari {{ Fmt::n($s['n_rep']) }} replikasi, seed {{ $s['seed'] }}.
        Kedatangan pesanan ~ {{ $af['family'] }} (indeks dispersi {{ Fmt::n($af['dispersion_index'], 2) }}); keranjang diambil ulang (bootstrap) dari {{ count($s['baseline_days_used']) }} hari baseline.
    </p>

    <div class="mt-6 grid gap-3 md:grid-cols-2">
        <div class="card">
            <div class="label">Skenario baseline</div>
            <div class="mt-1 text-2xl font-semibold">{{ Fmt::rp($b['revenue']['p50'], true) }}</div>
            <div class="text-xs text-ink-2">Interval 90%: {{ Fmt::rp($b['revenue']['p5'], true) }} – {{ Fmt::rp($b['revenue']['p95'], true) }} · {{ Fmt::n($b['orders']['p50']) }} pesanan</div>
        </div>
        <div class="card">
            <div class="label">Dengan kampanye {{ $s['promo_day_date'] ?? '' }}</div>
            <div class="mt-1 text-2xl font-semibold">{{ Fmt::rp($p['revenue']['p50'], true) }}</div>
            <div class="text-xs text-ink-2">Interval 90%: {{ Fmt::rp($p['revenue']['p5'], true) }} – {{ Fmt::rp($p['revenue']['p95'], true) }} · {{ Fmt::n($p['orders']['p50']) }} pesanan</div>
        </div>
    </div>
    <p class="mt-2 text-xs text-muted">Asumsi uplift kampanye = {{ Fmt::n($s['uplift_assumption']['mean'], 2) }}× baseline (dari 10.10; n = 1 kejadian, σ = {{ $s['uplift_assumption']['sigma'] }} adalah asumsi).</p>

    <div class="mt-6 grid gap-4 lg:grid-cols-2">
        <x-chart :chart="$charts['sim-daily'] ?? null" />
        <x-chart :chart="$charts['sim-dist'] ?? null" />
    </div>

    <section class="card mt-6">
        <h3 class="text-sm font-semibold">Rekomendasi stok {{ $s['horizon_days'] }} hari (unit per aroma)</h3>
        <p class="mt-0.5 text-xs text-ink-2">P95 baseline = stok yang cukup di 95% replikasi tanpa kampanye. Kolom kampanye bila ada tanggal kembar.</p>
        <div class="overflow-x-auto">
        <table class="mt-3 w-full">
            <thead><tr><th class="th">Aroma</th><th class="th text-right">Baseline P50</th><th class="th text-right">Baseline P95</th><th class="th text-right">Kampanye P95</th></tr></thead>
            <tbody class="divide-y divide-line">
            @foreach ($b['family_units'] as $fam => $q)
                <tr><td class="td">{{ $fam }}</td><td class="td text-right">{{ Fmt::n($q['p50']) }}</td><td class="td text-right">{{ Fmt::n($q['p95']) }}</td><td class="td text-right">{{ Fmt::n($p['family_units'][$fam]['p95'] ?? 0) }}</td></tr>
            @endforeach
            </tbody>
        </table>
        </div>
    </section>

    <div class="mt-6 grid gap-4 lg:grid-cols-2">
        <section class="card">
            <h3 class="text-sm font-semibold">Verifikasi (model dibangun dengan benar?)</h3>
            <ul class="mt-2 space-y-1 text-sm text-ink-2">
                <li>{{ ($v['mean_check']['pass'] ?? false) ? '✓' : '✗' }} Rata-rata simulasi {{ Fmt::n($v['mean_check']['simulated_orders'] ?? 0, 1) }} vs analitik {{ Fmt::n($v['mean_check']['analytical_orders'] ?? 0, 1) }} (selisih {{ Fmt::n($v['mean_check']['abs_err_pct'] ?? 0, 2) }}%)</li>
                <li>{{ ($v['reproducible_same_seed'] ?? false) ? '✓' : '✗' }} Seed sama menghasilkan keluaran identik</li>
                <li>{{ ($v['no_negative_values'] ?? false) ? '✓' : '✗' }} Tidak ada nilai negatif</li>
            </ul>
        </section>
        <section class="card">
            <h3 class="text-sm font-semibold">Validasi (model cocok dengan data?)</h3>
            <p class="mt-2 text-sm text-ink-2">Backtest rolling-origin, {{ $val['n_test_days'] ?? 0 }} hari uji: cakupan interval 90% = {{ Fmt::n($val['coverage_pct'] ?? 0, 0) }}%, MAPE = {{ Fmt::n($val['mape_pct'] ?? 0, 1) }}%.</p>
            <p class="mt-2 text-sm text-ink-2">Profil jam (NHPP) vs data: uji KS p = {{ Fmt::n($s['nhpp']['ks_p'] ?? 0, 3) }}.</p>
            <p class="mt-2 text-xs text-muted">{{ $val['note'] ?? '' }}</p>
        </section>
    </div>
    @endif
@endsection
