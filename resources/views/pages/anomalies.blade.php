@extends('layouts.app')
@section('title', 'Anomali')
@section('content')
    <h1 class="text-2xl font-semibold tracking-tight">Anomali</h1>
    <p class="mt-1 text-sm text-ink-2">Dideteksi dengan skor-z robust (median/MAD), batas Tukey pada skala log, uji proporsi, dan pemeriksaan kualitas data.</p>

    <div class="mt-6 space-y-3">
        @forelse ($items as $a)
            <article class="card flex gap-4">
                <div class="mt-0.5 w-20 shrink-0">
                    <span class="inline-block rounded-md px-2 py-0.5 text-xs font-medium {{ $a->severity === 'warning' ? 'bg-warn/10 text-warn' : 'bg-accent/10 text-accent' }}">
                        {{ $a->severity === 'warning' ? '▲ Periksa' : 'ℹ Info' }}
                    </span>
                    <div class="mt-1 text-[11px] text-muted">{{ str_replace('_', ' ', $a->kind) }}</div>
                </div>
                <div>
                    <h3 class="font-medium">{{ $a->title }}</h3>
                    <p class="mt-1 text-sm text-ink-2">{{ $a->detail }}</p>
                </div>
            </article>
        @empty
            <p class="text-sm text-ink-2">Belum ada data. Jalankan <code>php artisan dobha:import</code>.</p>
        @endforelse
    </div>
@endsection
