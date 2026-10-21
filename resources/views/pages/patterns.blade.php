@extends('layouts.app')
@section('title', 'Pola')
@php use App\Support\Fmt; @endphp
@section('content')
    <h1 class="text-2xl font-semibold tracking-tight">Pola penjualan</h1>
    <p class="mt-1 text-sm text-ink-2">Grafik interaktif (Plotly) dihasilkan pipeline Python; galeri statis memakai Matplotlib & Seaborn.</p>

    <div class="mt-6 grid gap-4 lg:grid-cols-2">
        @foreach ($charts as $c)
            <x-chart :chart="$c" />
        @endforeach

        <section class="card">
            <h3 class="text-sm font-semibold">10 SKU terlaris (unit)</h3>
            <p class="mt-0.5 text-xs text-ink-2">Dihitung langsung dari tabel order_items di MySQL.</p>
            <table class="mt-3 w-full">
                <thead><tr><th class="th">SKU</th><th class="th text-right">Unit</th><th class="th text-right">Omzet</th></tr></thead>
                <tbody class="divide-y divide-line">
                @foreach ($topSkus as $s)
                    <tr><td class="td">{{ $s->sku }}</td><td class="td text-right">{{ Fmt::n($s->units) }}</td><td class="td text-right">{{ Fmt::rp($s->revenue, true) }}</td></tr>
                @endforeach
                </tbody>
            </table>
        </section>
    </div>

    @if (!empty($a['basket']['pairs']))
        <section class="card mt-4">
            <h3 class="text-sm font-semibold">Pasangan aroma yang dibeli bersama</h3>
            <p class="mt-0.5 text-xs text-ink-2">Lift &lt; 1 berarti kombinasi tidak lebih sering dari kebetulan; dukungan data masih kecil.</p>
            <table class="mt-3 w-full">
                <thead><tr><th class="th">Aroma A</th><th class="th">Aroma B</th><th class="th text-right">Pesanan</th><th class="th text-right">Lift</th></tr></thead>
                <tbody class="divide-y divide-line">
                @foreach ($a['basket']['pairs'] as $p)
                    <tr><td class="td">{{ $p['a'] }}</td><td class="td">{{ $p['b'] }}</td><td class="td text-right">{{ $p['orders'] }}</td><td class="td text-right">{{ $p['lift'] }}</td></tr>
                @endforeach
                </tbody>
            </table>
        </section>
    @endif

    <h2 class="mt-10 text-lg font-semibold">Galeri statis (Matplotlib & Seaborn)</h2>
    <div class="mt-3 grid gap-4 lg:grid-cols-2">
        @foreach ($static as $g)
            <figure class="card">
                <img src="{{ asset('charts/'.$g['file']) }}" alt="{{ $g['title'] }}" class="w-full" loading="lazy">
                <figcaption class="mt-2 text-xs text-ink-2"><span class="font-medium text-ink">{{ $g['title'] }}.</span> {{ $g['note'] }}</figcaption>
            </figure>
        @endforeach
    </div>
@endsection
