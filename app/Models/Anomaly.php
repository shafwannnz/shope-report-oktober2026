<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Anomaly extends Model
{
    public $timestamps = false;
    protected $guarded = [];
    protected $casts = ['meta' => 'array'];
}
