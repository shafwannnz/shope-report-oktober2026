import './bootstrap';
import Plotly from 'plotly.js-cartesian-dist-min';

// Setiap <div data-plotly="id-script-json"> dirender dari JSON Plotly buatan pipeline Python.
function render() {
    document.querySelectorAll('[data-plotly]').forEach((el) => {
        const src = document.getElementById(el.dataset.plotly);
        if (!src) return;
        const fig = JSON.parse(src.textContent);
        Plotly.newPlot(el, fig.data, { ...fig.layout, autosize: true, height: fig.layout.height ?? 340 }, {
            responsive: true, displaylogo: false, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
        });
    });
}
document.addEventListener('DOMContentLoaded', render);
