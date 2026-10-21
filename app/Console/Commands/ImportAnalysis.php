<?php

namespace App\Console\Commands;

use App\Models\Snapshot;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

/**
 * Memuat keluaran pipeline Python ke MySQL.
 *   python analysis/run_all.py   ->  php artisan dobha:import
 */
class ImportAnalysis extends Command
{
    protected $signature = 'dobha:import {--fresh : kosongkan tabel sebelum impor}';
    protected $description = 'Impor orders.csv, lines.csv, results.json dan plotly_charts.json hasil pipeline Python';

    private const BOOL = ['is_cod', 'has_gift', 'has_buyer_note', 'is_gift'];

    public function handle(): int
    {
        $base = base_path('analysis');
        $files = [
            'orders' => "$base/data/processed/orders.csv",
            'lines'  => "$base/data/processed/lines.csv",
            'results' => "$base/output/results.json",
            'charts' => "$base/output/plotly_charts.json",
        ];
        foreach ($files as $name => $path) {
            if (! is_file($path)) {
                $this->error("File $name tidak ditemukan: $path  (jalankan: python analysis/run_all.py)");
                return self::FAILURE;
            }
        }

        DB::transaction(function () use ($files) {
            foreach (['order_items', 'orders', 'insights', 'anomalies', 'charts'] as $t) {
                DB::table($t)->delete();
            }
            $this->importOrders($files['orders']);
            $this->importItems($files['lines']);
            $this->importResults($files['results']);
            $this->importCharts($files['charts']);
        });

        $this->info(sprintf('Selesai: %d pesanan, %d item.', DB::table('orders')->count(), DB::table('order_items')->count()));
        return self::SUCCESS;
    }

    private function importOrders(string $path): void
    {
        $this->rows($path, function (array $r) {
            return [
                'order_id' => $r['order_id'], 'ordered_at' => $r['created_at'],
                'paid_at' => $r['paid_at'] ?: null, 'completed_at' => $r['completed_at'] ?: null,
                'status' => $r['status'], 'payment_method' => $r['payment_method'], 'is_cod' => $r['is_cod'],
                'courier' => $r['courier'], 'ship_tier' => $r['ship_tier'],
                'province' => $r['province'] ?: null, 'city' => $r['city'] ?: null,
                'buyer_id' => $r['buyer_id'], 'has_buyer_note' => $r['has_buyer_note'], 'has_gift' => $r['has_gift'],
                'n_lines' => (int) $r['n_lines'], 'units' => (int) $r['units'],
                'items_revenue' => (int) round((float) $r['items_revenue']), 'list_value' => (int) round((float) $r['list_value']),
                'discount_total' => (int) round((float) $r['discount_total']), 'total_paid' => (int) round((float) $r['total_paid']),
                'seller_voucher' => (int) round((float) $r['seller_voucher']), 'shopee_voucher' => (int) round((float) $r['shopee_voucher']),
                'coin_discount' => (int) round((float) $r['coin_discount']),
                'shipping_fee_buyer' => (int) round((float) $r['shipping_fee_buyer']),
                'lag_pay_min' => $r['lag_pay_min'] === '' ? null : (float) $r['lag_pay_min'],
                'lag_complete_h' => $r['lag_complete_h'] === '' ? null : (float) $r['lag_complete_h'],
            ];
        }, 'orders');
    }

    private function importItems(string $path): void
    {
        $this->rows($path, fn (array $r) => [
            'order_id' => $r['order_id'], 'sku' => $r['sku'], 'family' => $r['family'], 'category' => $r['category'],
            'product_name' => mb_substr($r['product_name'], 0, 255),
            'unit_list_price' => (int) round((float) $r['unit_list_price']), 'unit_price' => (int) round((float) $r['unit_price']),
            'qty' => (int) $r['qty'], 'line_subtotal' => (int) round((float) $r['line_subtotal']),
            'line_discount' => (int) round((float) $r['line_discount']), 'is_gift' => $r['is_gift'],
        ], 'order_items');
    }

    private function importResults(string $path): void
    {
        $res = json_decode(file_get_contents($path), true, 512, JSON_THROW_ON_ERROR);
        $a = $res['analysis'];
        foreach ($a['insights'] as $i => $x) {
            DB::table('insights')->insert($x + ['sort' => $i]);
        }
        foreach ($a['anomalies'] as $x) {
            $meta = array_diff_key($x, array_flip(['kind', 'severity', 'title', 'detail']));
            DB::table('anomalies')->insert([
                'kind' => $x['kind'], 'severity' => $x['severity'], 'title' => $x['title'], 'detail' => $x['detail'],
                'meta' => json_encode($meta, JSON_UNESCAPED_UNICODE),
            ]);
        }
        unset($a['insights'], $a['anomalies']);
        foreach (['analysis' => $a, 'simulation' => $res['simulation'], 'static_charts' => $res['static_charts']] as $key => $payload) {
            Snapshot::updateOrCreate(['key' => $key], [
                'payload' => $payload, 'imported_at' => now(),
            ]);
        }
    }

    private function importCharts(string $path): void
    {
        foreach (json_decode(file_get_contents($path), true, 512, JSON_THROW_ON_ERROR) as $c) {
            DB::table('charts')->insert([
                'slug' => $c['slug'], 'title' => $c['title'], 'subtitle' => $c['subtitle'] ?? null,
                'figure' => json_encode($c['figure'], JSON_UNESCAPED_UNICODE),
            ]);
        }
    }

    /** Baca CSV (header di baris pertama) dan sisipkan per 500 baris. */
    private function rows(string $path, callable $map, string $table): void
    {
        $fh = fopen($path, 'r');
        $head = fgetcsv($fh, 0, ',', '"', '\\');
        $buf = [];
        while (($line = fgetcsv($fh, 0, ',', '"', '\\')) !== false) {
            $row = array_combine($head, $line);
            foreach (self::BOOL as $b) {
                if (isset($row[$b])) {
                    $row[$b] = strtolower($row[$b]) === 'true' ? 1 : 0;
                }
            }
            $buf[] = $map($row);
            if (count($buf) === 500) {
                DB::table($table)->insert($buf);
                $buf = [];
            }
        }
        if ($buf) {
            DB::table($table)->insert($buf);
        }
        fclose($fh);
    }
}
