/* === Data Analysis Page Logic === */

let numericColumns = [];
let allColumns = [];

document.addEventListener('DOMContentLoaded', async function() {
    await loadStatistics();
    await initMLControls();
    bindEvents();
});

async function loadStatistics() {
    const spinner = document.getElementById('stats-spinner');
    if (spinner) spinner.classList.remove('d-none');

    try {
        const data = await ajaxGet('/api/analyze/statistics');
        if (spinner) spinner.classList.add('d-none');

        if (data.error) {
            showToast(data.error);
            return;
        }

        numericColumns = data.numeric_cols || [];
        allColumns = data.all_cols || [];

        renderStatistics(data.statistics);
        renderCorrelation(data.correlation);
    } catch (e) {
        if (spinner) spinner.classList.add('d-none');
        showToast('加载统计失败: ' + e.message);
    }
}

function renderStatistics(stats) {
    const container = document.getElementById('stats-container');
    if (!stats) {
        container.innerHTML = '<p class="text-center p-4 text-muted">无统计数据</p>';
        return;
    }

    let html = '';

    // Numeric statistics
    if (stats.numeric_stats && stats.numeric_stats.length > 0) {
        html += '<h6 class="px-3 pt-3">数值列统计</h6>';
        html += '<div class="table-responsive"><table class="table table-sm table-hover">';
        html += '<thead class="table-light"><tr>';
        ['列名', '数量', '均值', '标准差', '最小值', '25%', '50%', '75%', '最大值', '偏度', '峰度'].forEach(h => {
            html += `<th>${h}</th>`;
        });
        html += '</tr></thead><tbody>';

        stats.numeric_stats.forEach(s => {
            html += '<tr>';
            html += `<td><strong>${s.column}</strong></td>`;
            html += `<td>${s.count}</td>`;
            html += `<td>${formatNumber(s.mean)}</td>`;
            html += `<td>${formatNumber(s.std)}</td>`;
            html += `<td>${formatNumber(s.min)}</td>`;
            html += `<td>${formatNumber(s['25%'])}</td>`;
            html += `<td>${formatNumber(s['50%'])}</td>`;
            html += `<td>${formatNumber(s['75%'])}</td>`;
            html += `<td>${formatNumber(s.max)}</td>`;
            html += `<td>${formatNumber(s.skewness)}</td>`;
            html += `<td>${formatNumber(s.kurtosis)}</td>`;
            html += '</tr>';
        });
        html += '</tbody></table></div>';
    }

    // Categorical statistics
    if (stats.categorical_stats && stats.categorical_stats.length > 0) {
        html += '<h6 class="px-3 pt-3">分类列统计</h6>';
        html += '<div class="table-responsive"><table class="table table-sm table-hover">';
        html += '<thead class="table-light"><tr>';
        ['列名', '数量', '唯一值数', '最常见值', '最常见频数'].forEach(h => {
            html += `<th>${h}</th>`;
        });
        html += '</tr></thead><tbody>';

        stats.categorical_stats.forEach(s => {
            html += '<tr>';
            html += `<td><strong>${s.column}</strong></td>`;
            html += `<td>${s.count}</td>`;
            html += `<td>${s.unique}</td>`;
            html += `<td>${s.top || '—'}</td>`;
            html += `<td>${s.freq}</td>`;
            html += '</tr>';
        });
        html += '</tbody></table></div>';
    }

    if (!stats.numeric_stats?.length && !stats.categorical_stats?.length) {
        html += '<p class="text-center p-4 text-muted">无数据列可统计</p>';
    }

    container.innerHTML = html;
}

function renderCorrelation(corr) {
    const container = document.getElementById('corr-container');
    if (!corr || !corr.columns || corr.columns.length < 2) {
        container.innerHTML = '<p class="text-muted">需要至少 2 个数值列来计算相关性矩阵。</p>';
        return;
    }

    // Render heatmap with Plotly
    const data = [{
        type: 'heatmap',
        z: corr.matrix,
        x: corr.columns,
        y: corr.columns,
        colorscale: 'RdBu',
        zmin: -1,
        zmax: 1,
        text: corr.matrix.map(row => row.map(v => v !== null ? v.toFixed(2) : '—')),
        texttemplate: '%{text}',
        hovertemplate: '%{x} vs %{y}<br>相关性: %{z:.4f}<extra></extra>'
    }];
    const layout = {
        title: '数值列相关性矩阵',
        template: 'plotly_white',
        autosize: true,
        height: 400,
        margin: { l: 120, r: 20, t: 40, b: 80 },
        xaxis: { tickangle: -45 }
    };
    Plotly.react('corr-plot', data, layout);
}

async function initMLControls() {
    try {
        const data = await ajaxGet('/api/analyze/statistics');
        numericColumns = data.numeric_cols || [];
        allColumns = data.all_cols || [];

        // Populate K-Means columns
        const kmSel = document.getElementById('kmeans-columns');
        if (kmSel) {
            kmSel.innerHTML = '';
            numericColumns.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col;
                opt.textContent = col;
                kmSel.appendChild(opt);
            });
            // Select first 2 by default
            if (kmSel.options.length >= 2) {
                kmSel.options[0].selected = true;
                kmSel.options[1].selected = true;
            }
        }

        // Populate LR y-column (numeric only)
        const lrY = document.getElementById('lr-y-column');
        if (lrY) {
            lrY.innerHTML = '';
            numericColumns.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col;
                opt.textContent = col;
                lrY.appendChild(opt);
            });
        }

        // Populate LR x-columns (all numeric)
        const lrX = document.getElementById('lr-x-columns');
        if (lrX) {
            lrX.innerHTML = '';
            numericColumns.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col;
                opt.textContent = col;
                lrX.appendChild(opt);
            });
            // Select first 2 by default (excluding y-column default)
            if (lrX.options.length >= 2) {
                lrX.options[0].selected = true;
                if (lrX.options.length > 1) lrX.options[1].selected = true;
            }
        }
    } catch (e) {
        showToast('初始化ML控件失败: ' + e.message);
    }
}

function bindEvents() {
    // K slider
    const kSlider = document.getElementById('kmeans-k');
    const kDisplay = document.getElementById('k-val-display');
    if (kSlider && kDisplay) {
        kSlider.addEventListener('input', function() {
            kDisplay.textContent = this.value;
        });
    }

    // Test size slider
    const tsSlider = document.getElementById('lr-test-size');
    const tsDisplay = document.getElementById('test-size-display');
    if (tsSlider && tsDisplay) {
        tsSlider.addEventListener('input', function() {
            tsDisplay.textContent = parseFloat(this.value).toFixed(2);
        });
    }
}

async function runKMeans() {
    const columns = Array.from(document.getElementById('kmeans-columns').selectedOptions).map(o => o.value);
    const n_clusters = parseInt(document.getElementById('kmeans-k').value);

    if (columns.length < 2) {
        showToast('请至少选择 2 个数值列', 'warning');
        return;
    }

    showLoading('#kmeans-loading');
    try {
        const data = await ajaxPost('/api/analyze/kmeans', { columns, n_clusters });
        hideLoading('#kmeans-loading');

        if (data.error) {
            showToast(data.error, 'warning');
            return;
        }

        // Render plot
        if (data.plot) {
            const fig = JSON.parse(data.plot);
            Plotly.react('kmeans-plot', fig.data, fig.layout);
        }

        // Render metrics
        const metricsEl = document.getElementById('kmeans-metrics');
        let html = '<div class="card bg-light"><div class="card-body p-2">';
        html += `<p class="mb-1"><strong>样本数:</strong> ${data.n_samples}</p>`;
        html += `<p class="mb-1"><strong>簇内平方和 (Inertia):</strong> ${formatNumber(data.inertia)}</p>`;
        if (data.silhouette_score !== null && data.silhouette_score !== undefined) {
            html += `<p class="mb-1"><strong>轮廓系数:</strong> ${formatNumber(data.silhouette_score)}</p>`;
        }
        html += '<p class="mb-1"><strong>各簇大小:</strong></p><ul class="mb-0 small">';
        for (const [k, v] of Object.entries(data.cluster_sizes || {})) {
            html += `<li>聚类 ${k}: ${v} 个样本</li>`;
        }
        html += '</ul>';
        if (data.explained_variance) {
            html += `<p class="mb-1 mt-2"><strong>PCA 解释方差:</strong>
                PC1 ${(data.explained_variance[0]*100).toFixed(1)}%,
                PC2 ${(data.explained_variance[1]*100).toFixed(1)}%</p>`;
        }
        html += '</div></div>';
        metricsEl.innerHTML = html;
    } catch (e) {
        hideLoading('#kmeans-loading');
        showToast('K-Means 运行失败: ' + e.message);
    }
}

async function runLinearRegression() {
    const x_columns = Array.from(document.getElementById('lr-x-columns').selectedOptions).map(o => o.value);
    const y_column = document.getElementById('lr-y-column').value;
    const test_size = parseFloat(document.getElementById('lr-test-size').value);

    if (!y_column) {
        showToast('请选择目标变量 (Y)', 'warning');
        return;
    }
    if (x_columns.length === 0) {
        showToast('请至少选择一个特征变量 (X)', 'warning');
        return;
    }

    showLoading('#lr-loading');
    try {
        const data = await ajaxPost('/api/analyze/linear-regression', {
            x_columns, y_column, test_size
        });
        hideLoading('#lr-loading');

        if (data.error) {
            showToast(data.error, 'warning');
            return;
        }

        // Render plot
        if (data.plot) {
            const fig = JSON.parse(data.plot);
            Plotly.react('lr-plot', fig.data, fig.layout);
        }

        // Render metrics
        const metricsEl = document.getElementById('lr-metrics');
        let html = '<div class="card bg-light"><div class="card-body p-2">';
        html += `<p class="mb-1"><strong>训练集 R²:</strong> ${formatNumber(data.train_r2)}</p>`;
        html += `<p class="mb-1"><strong>测试集 R²:</strong> ${formatNumber(data.r2_score)}</p>`;
        html += `<p class="mb-1"><strong>MSE:</strong> ${formatNumber(data.mse)}</p>`;
        html += `<p class="mb-1"><strong>MAE:</strong> ${formatNumber(data.mae)}</p>`;
        html += `<p class="mb-1"><strong>截距:</strong> ${formatNumber(data.intercept)}</p>`;
        html += '<p class="mb-1"><strong>系数:</strong></p><ul class="mb-0 small">';
        for (const [k, v] of Object.entries(data.coefficients || {})) {
            html += `<li>${k}: ${formatNumber(v)}</li>`;
        }
        html += '</ul>';
        html += `<p class="mb-1 mt-2"><strong>训练/测试集:</strong> ${data.train_size} / ${data.test_size}</p>`;
        html += '</div></div>';
        metricsEl.innerHTML = html;
    } catch (e) {
        hideLoading('#lr-loading');
        showToast('线性回归运行失败: ' + e.message);
    }
}
