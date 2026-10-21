@extends('layouts.app')
@section('title', 'Pesanan')
@php use App\Support\Fmt; @endphp
@section('content')
    <h1 class="text-2xl font-semibold tracking-tight">Data pesanan</h1>
    <p class="mt-1 text-sm text-ink-2">Satu baris per pesanan. Identitas pembeli sudah dihapus.</p>

    <form method="get" class="mt-4 flex flex-wrap gap-2 text-sm">
        <input name="q" value="{{ request('q') }}" placeholder="No. pesanan" class="rounded-md border border-line bg-white px-3 py-1.5">
        <select name="province" class="rounded-md border border-line bg-white px-3 py-1.5">
            <option value="">Semua provinsi</option>
            @foreach ($provinces as $p) <option @selected(request('province') === $p)>{{ $p }}</option> @endforeach
        </select>
        <select name="payment" class="rounded-md border border-line bg-white px-3 py-1.5">
            <option value="">Semua pembayaran</option>
            @foreach ($payments as $p) <option @selected(request('payment') === $p)>{{ $p }}</option> @endforeach
        </select>
        <button class="rounded-md bg-ink px-4 py-1.5 text-white">Terapkan</button>
    </form>

    <div class="card mt-4 overflow-x-auto p-0">
        <table class="w-full">
            <thead class="border-b border-line"><tr>
                <th class="th">Dibuat</th><th class="th">No. pesanan</th><th class="th">Provinsi</th><th class="th">Pembayaran</th>
                <th class="th">Kurir</th><th class="th text-right">Unit</th><th class="th text-right">Omzet</th>
            </tr></thead>
            <tbody class="divide-y divide-line">
            @foreach ($orders as $o)
                <tr>
                    <td class="td whitespace-nowrap">{{ $o->ordered_at->format('d M H:i') }}</td>
                    <td class="td font-mono text-xs">{{ $o->order_id }}</td>
                    <td class="td">{{ $o->province }}</td>
                    <td class="td">{{ $o->payment_method }}</td>
                    <td class="td">{{ $o->courier }} · {{ $o->ship_tier }}</td>
                    <td class="td text-right">{{ $o->units }}</td>
                    <td class="td text-right">{{ Fmt::rp($o->items_revenue) }}</td>
                </tr>
            @endforeach
            </tbody>
        </table>
    </div>
    <div class="mt-4">{{ $orders->links() }}</div>
@endsection
