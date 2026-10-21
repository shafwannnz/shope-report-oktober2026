<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/** Penyimpan hasil analisis Python (JSON) per kunci: analysis, simulation, static_charts. */
class Snapshot extends Model
{
    protected $table = 'analysis_snapshots';
    protected $primaryKey = 'key';
    public $incrementing = false;
    protected $keyType = 'string';
    public $timestamps = false;
    protected $guarded = [];
    protected $casts = ['payload' => 'array', 'imported_at' => 'datetime'];

    public static function get(string $key): array
    {
        return static::find($key)?->payload ?? [];
    }
}
