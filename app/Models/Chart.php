<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Chart extends Model
{
    public $timestamps = false;
    protected $guarded = [];
    protected $casts = ['figure' => 'array'];
}
