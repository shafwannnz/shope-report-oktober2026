<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'Ringkasan') · Dobha Analytics</title>
    <link rel="preconnect" href="https://fonts.bunny.net">
    <link href="https://fonts.bunny.net/css?family=inter:400,500,600" rel="stylesheet">
    @vite(['resources/css/app.css', 'resources/js/app.js'])
</head>
<body class="min-h-screen font-sans">
@php
    $nav = ['overview' => 'Ringkasan', 'patterns' => 'Pola', 'anomalies' => 'Anomali', 'simulation' => 'Simulasi', 'orders' => 'Pesanan', 'about' => 'Metodologi'];
@endphp
<header class="border-b border-line bg-white/80 backdrop-blur">
    <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <a href="{{ route('overview') }}" class="text-sm font-semibold tracking-tight">Dobha<span class="text-accent"> Analytics</span></a>
        <nav class="flex flex-wrap gap-1 text-sm">
            @foreach ($nav as $route => $label)
                <a href="{{ route($route) }}"
                   class="rounded-md px-3 py-1.5 {{ request()->routeIs($route) ? 'bg-ink text-white' : 'text-ink-2 hover:bg-line/60' }}">{{ $label }}</a>
            @endforeach
        </nav>
    </div>
</header>
<main class="mx-auto max-w-6xl px-4 py-8">
    @yield('content')
</main>
<footer class="mx-auto max-w-6xl px-4 pb-10 text-xs text-muted">
    Sumber data: ekspor Shopee Seller Centre (Order.all), Dobha Perfumes, 1–19 Okt 2026. Data pembeli telah dianonimkan.
</footer>
</body>
</html>
