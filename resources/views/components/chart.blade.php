@props(['chart'])
@if ($chart)
    <section class="card">
        <h3 class="text-sm font-semibold text-ink">{{ $chart->title }}</h3>
        @if ($chart->subtitle)
            <p class="mt-0.5 text-xs text-ink-2">{{ $chart->subtitle }}</p>
        @endif
        <div class="mt-3" data-plotly="fig-{{ $chart->slug }}"></div>
        <script type="application/json" id="fig-{{ $chart->slug }}">{!! json_encode($chart->figure, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP) !!}</script>
    </section>
@endif
