<?php

namespace App\Http\Controllers;

use App\Models\Anomaly;
use App\Models\Chart;
use App\Models\Insight;
use App\Models\Order;
use App\Models\Snapshot;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class DashboardController extends Controller
{
    /** Ringkasan: KPI dihitung langsung dari MySQL; insight & grafik berasal dari pipeline Python. */
    public function overview()
    {
        $k = Order::query()->selectRaw('
            COUNT(*) AS orders,
            SUM(items_revenue) AS revenue,
            SUM(units) AS units,
            AVG(items_revenue) AS aov,
            AVG(is_cod) * 100 AS cod_pct,
            COUNT(DISTINCT buyer_id) AS buyers,
            MIN(ordered_at) AS first_at,
            MAX(ordered_at) AS last_at,
            SUM(discount_total) * 100.0 / NULLIF(SUM(list_value), 0) AS discount_pct
        ')->first();

        $analysis = Snapshot::get('analysis');

        return view('pages.overview', [
            'k' => $k,
            'window' => $analysis['window'] ?? [],
            'pyKpi' => $analysis['kpi'] ?? [],
            'insights' => Insight::orderBy('sort')->get(),
            'anomalies' => Anomaly::whereIn('severity', ['warning'])->limit(4)->get(),
            'chart' => Chart::where('slug', 'daily-orders')->first(),
        ]);
    }

    public function patterns()
    {
        $slugs = ['hourly', 'top-products', 'category', 'payment', 'province'];
        $charts = Chart::whereIn('slug', $slugs)->get()->sortBy(fn ($c) => array_search($c->slug, $slugs))->values();
        $a = Snapshot::get('analysis');

        return view('pages.patterns', [
            'charts' => $charts,
            'a' => $a,
            'static' => Snapshot::get('static_charts'),
            'topSkus' => DB::table('order_items')->where('is_gift', 0)
                ->selectRaw('sku, SUM(qty) AS units, SUM(line_subtotal) AS revenue')
                ->groupBy('sku')->orderByDesc('units')->limit(10)->get(),
        ]);
    }

    public function anomalies()
    {
        $order = ['warning' => 0, 'info' => 1];
        $items = Anomaly::all()->sortBy(fn ($a) => $order[$a->severity] ?? 9)->values();
        return view('pages.anomalies', ['items' => $items]);
    }

    public function simulation()
    {
        $sim = Snapshot::get('simulation');
        $charts = Chart::whereIn('slug', ['sim-daily', 'sim-dist'])->get()->keyBy('slug');
        return view('pages.simulation', ['s' => $sim, 'charts' => $charts]);
    }

    public function orders(Request $r)
    {
        $q = Order::query()->orderByDesc('ordered_at');
        if ($r->filled('province')) {
            $q->where('province', $r->string('province'));
        }
        if ($r->filled('payment')) {
            $q->where('payment_method', $r->string('payment'));
        }
        if ($r->filled('q')) {
            $q->where('order_id', 'like', '%' . $r->string('q') . '%');
        }
        return view('pages.orders', [
            'orders' => $q->paginate(25)->withQueryString(),
            'provinces' => Order::distinct()->orderBy('province')->pluck('province')->filter(),
            'payments' => Order::distinct()->orderBy('payment_method')->pluck('payment_method'),
        ]);
    }

    public function about()
    {
        return view('pages.about');
    }
}
