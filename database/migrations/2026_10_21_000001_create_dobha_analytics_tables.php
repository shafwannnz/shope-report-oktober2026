<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Satu baris per No. Pesanan (data sudah dianonimkan oleh pipeline Python).
        Schema::create('orders', function (Blueprint $t) {
            $t->id();
            $t->string('order_id', 32)->unique();
            $t->dateTime('ordered_at')->index();
            $t->dateTime('paid_at')->nullable();
            $t->dateTime('completed_at')->nullable();
            $t->string('status', 60);
            $t->string('payment_method', 40)->index();
            $t->boolean('is_cod')->default(false);
            $t->string('courier', 30);
            $t->string('ship_tier', 20);
            $t->string('province', 60)->nullable()->index();
            $t->string('city', 80)->nullable();
            $t->string('buyer_id', 16)->index();      // hash SHA-256 terpotong, bukan username asli
            $t->boolean('has_buyer_note')->default(false);
            $t->boolean('has_gift')->default(false);
            $t->unsignedInteger('n_lines');
            $t->unsignedInteger('units');
            $t->unsignedBigInteger('items_revenue');
            $t->unsignedBigInteger('list_value');
            $t->unsignedBigInteger('discount_total');
            $t->unsignedBigInteger('total_paid');
            $t->unsignedBigInteger('seller_voucher')->default(0);
            $t->unsignedBigInteger('shopee_voucher')->default(0);
            $t->unsignedBigInteger('coin_discount')->default(0);
            $t->unsignedBigInteger('shipping_fee_buyer')->default(0);
            $t->double('lag_pay_min')->nullable();
            $t->double('lag_complete_h')->nullable();
        });

        // Satu baris per produk dalam pesanan.
        Schema::create('order_items', function (Blueprint $t) {
            $t->id();
            $t->string('order_id', 32)->index();
            $t->string('sku', 120)->index();
            $t->string('family', 120)->index();
            $t->string('category', 40)->index();
            $t->string('product_name', 255);
            $t->unsignedBigInteger('unit_list_price');
            $t->unsignedBigInteger('unit_price');
            $t->unsignedInteger('qty');
            $t->unsignedBigInteger('line_subtotal');
            $t->unsignedBigInteger('line_discount');
            $t->boolean('is_gift')->default(false);
        });

        // Hasil analisis Python (insight, anomali, grafik Plotly, snapshot simulasi).
        Schema::create('insights', function (Blueprint $t) {
            $t->id();
            $t->string('area', 40);
            $t->string('title');
            $t->text('body');
            $t->text('action');
            $t->unsignedSmallInteger('sort')->default(0);
        });

        Schema::create('anomalies', function (Blueprint $t) {
            $t->id();
            $t->string('kind', 40)->index();
            $t->string('severity', 12)->index();
            $t->string('title');
            $t->text('detail');
            $t->json('meta')->nullable();
        });

        Schema::create('charts', function (Blueprint $t) {
            $t->id();
            $t->string('slug', 40)->unique();
            $t->string('title');
            $t->string('subtitle')->nullable();
            $t->longText('figure');                    // JSON Plotly (data + layout)
        });

        Schema::create('analysis_snapshots', function (Blueprint $t) {
            $t->string('key', 40)->primary();
            $t->longText('payload');                   // JSON
            $t->timestamp('imported_at')->nullable();
        });
    }

    public function down(): void
    {
        foreach (['analysis_snapshots', 'charts', 'anomalies', 'insights', 'order_items', 'orders'] as $tbl) {
            Schema::dropIfExists($tbl);
        }
    }
};
