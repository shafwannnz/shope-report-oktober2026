@extends('layouts.app')
@section('title', 'Metodologi')
@section('content')
    <h1 class="text-2xl font-semibold tracking-tight">Metodologi</h1>
    <div class="mt-6 grid gap-4 md:grid-cols-2">
        <section class="card">
            <h2 class="font-medium">Alur data</h2>
            <ol class="mt-2 list-decimal space-y-1 pl-5 text-sm text-ink-2">
                <li>Ekspor Order.all Shopee (.xlsx) dibaca Python (pandas).</li>
                <li>Pembersihan: kolom uang berformat teks "60.999" diparse ke Rp 60.999; data pembeli dianonimkan; tabel dipisah level-pesanan dan level-item agar tidak terjadi double counting.</li>
                <li>Analisis pola & anomali (NumPy, SciPy) dan grafik (Matplotlib, Seaborn, Plotly).</li>
                <li>Simulasi Monte Carlo kedatangan pesanan dan omzet.</li>
                <li><code>php artisan dobha:import</code> memuat hasil ke MySQL; Laravel menyajikannya dengan Tailwind CSS.</li>
            </ol>
        </section>
        <section class="card">
            <h2 class="font-medium">Batasan yang perlu diketahui</h2>
            <ul class="mt-2 list-disc space-y-1 pl-5 text-sm text-ink-2">
                <li>Ekspor hanya memuat pesanan yang sudah diterima/selesai (tidak ada pesanan batal atau masih dikirim), sehingga pesanan terbaru tersensor.</li>
                <li>Hanya ±19 hari data dan satu hari promo (10.10): efek hari dalam seminggu dan musiman tidak dapat diestimasi.</li>
                <li>Omzet = subtotal produk setelah diskon penjual; biaya platform, HPP, dan retur tidak tersedia.</li>
                <li>Uplift kampanye 11.11 adalah asumsi berdasarkan satu kejadian.</li>
            </ul>
        </section>
    </div>
@endsection
