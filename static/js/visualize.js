/* === Data Visualization Page Logic === */

let numericCols = [];
let categoricalCols = [];
let allCols = [];

document.addEventListener('DOMContentLoaded', async function() {
    await loadColumns();
    bindEvents();
    // Show first chart type params
    onChartTypeChange();
});

async function loadColumns() {
    try {
        const data = await ajaxGet('/api/visualize/columns');
        if (data.error) {
            showToast(data.error);
            return;
        }
        numericCols = data.numeric_cols || [];
        categoricalCols = data.categorical_cols || [];
        allCols = data.all_cols || [];

        populateColumnSelects();
    } catch (e) {
        showToast('加载列信息失败: ' + e.message);
    }
}

function populateColumnSelects() {
    // Populate all column dropdowns
    function fill(selectId, options, includeEmpty = false) {
        const sel = document.getElementById(selectId);
        if (!sel) return;
        sel.innerHTML = '';
        if (includeEmpty) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = '— 选择列 —';
            sel.appendChild(opt);
        }
        options.forEach(col => {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            sel.appendChild(opt);
        });
    }

    fill('hist-column', allCols, true);
    fill('scatter-x', numericCols, true);
    fill('scatter-y', numericCols, true);
    fill('scatter-color', allCols, false);  // has "无" option in HTML
    fill('scatter-size', numericCols, false);
    fill('bar-x', allCols, true);
    fill('bar-y', numericCols, true);
    fill('line-x', allCols, true);
    fill('line-y', numericCols, false);
}

function bindEvents() {
    // Chart type change
    document.getElementById('chart-type').addEventListener('change', onChartTypeChange);

    // Histogram bins slider
    const binsSlider = document.getElementById('hist-bins');
    if (binsSlider) {
        binsSlider.addEventListener('input', function() {
            document.getElementById('hist-bins-val').textContent = this.value;
        });
    }

    // Auto-generate on parameter change (debounced)
    const debouncedGenerate = debounce(generateChart, 500);
    document.querySelectorAll('.chart-params select, .chart-params input').forEach(el => {
        el.addEventListener('change', debouncedGenerate);
        el.addEventListener('input', debouncedGenerate);
    });
}

function onChartTypeChange() {
    const chartType = document.getElementById('chart-type').value;
    // Hide all param groups
    document.querySelectorAll('.chart-params').forEach(el => el.style.display = 'none');
    // Show the relevant one
    const paramsEl = document.getElementById('params-' + chartType);
    if (paramsEl) paramsEl.style.display = 'block';
}

async function generateChart() {
    const chartType = document.getElementById('chart-type').value;
    const params = collectParams(chartType);

    showLoading('#chart-loading');
    document.getElementById('download-btn').disabled = true;

    try {
        const data = await ajaxPost('/api/visualize/chart', {
            chart_type: chartType,
            ...params
        });
        hideLoading('#chart-loading');

        if (data.error) {
            showToast(data.error, 'warning');
            return;
        }

        if (data.figure) {
            const fig = JSON.parse(data.figure);
            Plotly.react('main-chart', fig.data, fig.layout);
            document.getElementById('download-btn').disabled = false;
        }
    } catch (e) {
        hideLoading('#chart-loading');
        showToast('生成图表失败: ' + e.message);
    }
}

function collectParams(chartType) {
    const params = {};

    switch (chartType) {
        case 'histogram':
            params.column = document.getElementById('hist-column').value;
            params.bins = parseInt(document.getElementById('hist-bins').value);
            const color = document.getElementById('hist-color').value;
            if (color) params.color = color;
            break;

        case 'scatter':
            params.x_col = document.getElementById('scatter-x').value;
            params.y_col = document.getElementById('scatter-y').value;
            const colorCol = document.getElementById('scatter-color').value;
            if (colorCol) params.color_col = colorCol;
            const sizeCol = document.getElementById('scatter-size').value;
            if (sizeCol) params.size_col = sizeCol;
            params.trendline = document.getElementById('scatter-trendline').checked;
            break;

        case 'bar':
            params.x_col = document.getElementById('bar-x').value;
            params.y_col = document.getElementById('bar-y').value;
            params.agg_func = document.getElementById('bar-agg').value;
            const topN = document.getElementById('bar-topn').value;
            if (topN) params.top_n = parseInt(topN);
            break;

        case 'line':
            params.x_col = document.getElementById('line-x').value;
            params.y_cols = Array.from(document.getElementById('line-y').selectedOptions).map(o => o.value);
            break;
    }

    return params;
}

function downloadChart() {
    Plotly.downloadImage('main-chart', {
        format: 'png',
        width: 1200,
        height: 800,
        filename: 'chart'
    });
}

// Debounce utility
function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}
