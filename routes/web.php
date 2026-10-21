<?php

use App\Http\Controllers\DashboardController;
use Illuminate\Support\Facades\Route;

Route::controller(DashboardController::class)->group(function () {
    Route::get('/', 'overview')->name('overview');
    Route::get('/pola', 'patterns')->name('patterns');
    Route::get('/anomali', 'anomalies')->name('anomalies');
    Route::get('/simulasi', 'simulation')->name('simulation');
    Route::get('/pesanan', 'orders')->name('orders');
    Route::get('/tentang', 'about')->name('about');
});
