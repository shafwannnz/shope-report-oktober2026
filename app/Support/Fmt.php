<?php

namespace App\Support;

/** Format angka gaya Indonesia. */
class Fmt
{
    public static function rp(float|int|null $v, bool $short = false): string
    {
        $v = (float) ($v ?? 0);
        if ($short) {
            return match (true) {
                abs($v) >= 1e9 => 'Rp ' . number_format($v / 1e9, 2, ',', '.') . ' M',
                abs($v) >= 1e6 => 'Rp ' . number_format($v / 1e6, 1, ',', '.') . ' jt',
                abs($v) >= 1e3 => 'Rp ' . number_format($v / 1e3, 0, ',', '.') . ' rb',
                default => 'Rp ' . number_format($v, 0, ',', '.'),
            };
        }
        return 'Rp ' . number_format($v, 0, ',', '.');
    }

    public static function n(float|int|null $v, int $d = 0): string
    {
        return number_format((float) ($v ?? 0), $d, ',', '.');
    }

    public static function pct(float|int|null $v, int $d = 1): string
    {
        return number_format((float) ($v ?? 0), $d, ',', '.') . '%';
    }
}
