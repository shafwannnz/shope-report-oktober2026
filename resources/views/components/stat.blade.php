@props(['label', 'value', 'hint' => null])
<div class="card">
    <div class="label">{{ $label }}</div>
    <div class="mt-1 text-2xl font-semibold tracking-tight">{{ $value }}</div>
    @if ($hint)
        <div class="mt-1 text-xs text-ink-2">{{ $hint }}</div>
    @endif
</div>
