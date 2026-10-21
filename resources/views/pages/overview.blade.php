@extends('layouts.app')
@section('title', 'Ringkasan')
@php use App\Support\Fmt; @endphp
@section('content')
    <div class="mb-6">
        <h1 class="text-2xl font-semibold tracking-tight">Dobha Perfumes · Analisis Penjualan Shopee</h1>
        <p class="mt-1 text-sm text-ink-2">
            Periode {{ \Illuminate\Support\Carbon::parse($k->first_at)->translatedFormat('d M') }}–{{ \Illuminate\Support\Carbon::parse($k->last_at)->translatedFormat('d M Y') }}.
            Tren & prediksi memakai data lengkap sampai <strong>{{ $window['last_full_day'] ?? '-' }}</strong>
            (pesanan sesudahnya belum seluruhnya masuk ekspor).
        </p>
    </div>

    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <x-stat label="Pesanan" :value="Fmt::n($k->orders)" :hint="Fmt::n($k->units).' unit terjual'" />
        <x-stat label="Omzet produk" :value="Fmt::rp($k->revenue, true)" :hint="'≈ '.Fmt::rp(($pyKpi['baseline_revenue_per_day'] ?? 0), true).' / hari baseline'" />
        <x-stat label="Nilai pesanan rata-rata" :value="Fmt::rp($k->aov)" :hint="'Median '.Fmt::rp($pyKpi['aov_median'] ?? 0)" />
        <x-stat label="Porsi COD" :value="Fmt::pct($k->cod_pct)" :hint="Fmt::pct($pyKpi['repeat_buyer_pct'] ?? 0).' pembeli berulang'" />
    </div>

    <div class="mt-6"><x-chart :chart="$chart" /></div>

    <section class="mt-10">
        <h2 class="text-lg font-semibold">Insight utama</h2>
        <div class="mt-3 grid gap-3 md:grid-cols-2">
            @foreach ($insights as $i)
                <article class="card">
                    <div class="label">{{ $i->area }}</div>
                    <h3 class="mt-1 font-medium">{{ $i->title }}</h3>
                    <p class="mt-1 text-sm text-ink-2">{{ $i->body }}</p>
                    <p class="mt-2 text-sm"><span class="font-medium text-accent">Saran:</span> <span class="text-ink-2">{{ $i->action }}</span></p>
                </article>
            @endforeach
        </div>
    </section>

    @if ($anomalies->isNotEmpty())
        <section class="mt-10">
            <div class="flex items-end justify-between">
                <h2 class="text-lg font-semibold">Perlu perhatian</h2>
                <a href="{{ route('anomalies') }}" class="text-sm text-accent hover:underline">Semua anomali →</a>
            </div>
            <ul class="mt-3 divide-y divide-line rounded-xl border border-line bg-white">
                @foreach ($anomalies as $a)
                    <li class="px-5 py-3">
                        <div class="text-sm font-medium"><span class="mr-1 text-warn">▲</span>{{ $a->title }}</div>
                        <div class="text-sm text-ink-2">{{ $a->detail }}</div>
                    </li>
                @endforeach
            </ul>
        </section>
    @endif
@endsection
