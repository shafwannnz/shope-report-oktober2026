<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Order extends Model
{
    public $timestamps = false;
    protected $guarded = [];
    protected $casts = ['ordered_at' => 'datetime', 'paid_at' => 'datetime', 'completed_at' => 'datetime', 'is_cod' => 'boolean', 'has_gift' => 'boolean'];

    public function items(): HasMany
    {
        return $this->hasMany(OrderItem::class, 'order_id', 'order_id');
    }
}
