/* === Data Cleaning Page Logic === */

let allColumns = [];
let numericCols = [];
let categoricalCols = [];

// Init on page load
document.addEventListener('DOMContentLoaded', async function() {
    await loadCleanInfo();
    bindEvents();
});

async function loadCleanInfo() {
    try {
        const data = await ajaxGet('/api/clean/info');
        if (data.error) {
            showToast(data.error);
            return;
        }
        allColumns = data.all_cols || [];
        numericCols = data.numeric_cols || [];
        categoricalCols = data.categorical_cols || [];

        updateRowCount(data.column_info);
        updatePreviewTable(data.preview_data, data.column_info);
        populateAllSelects(data);
    } catch (e) {
        showToast('加载数据失败: ' + e.message);
    }
}

function updateRowCount(colInfo) {
    if (colInfo && colInfo.summary) {
        document.getElementById('row-count-badge').textContent =
            `行: ${colInfo.summary.rows} | 列: ${colInfo.summary.columns}`;
    }
}

function updatePreviewTable(previewData, colInfo) {
    const container = document.getElementById('preview-table-body');
    if (!previewData || previewData.length === 0) {
        container.innerHTML = '<p class="text-center p-4 text-muted">无数据</p>';
        return;
    }
    const cols = colInfo ? colInfo.columns.map(c => c.name) : Object.keys(previewData[0]);

    let html = '<div class="preview-table-wrapper" style="max-height:400px;"><table class="table table-sm table-bordered mb-0 preview-table">';
    html += '<thead class="table-dark"><tr><th>#</th>';
    cols.forEach(c => { html += `<th>${c}</th>`; });
    html += '</tr></thead><tbody>';

    previewData.forEach((row, i) => {
        html += '<tr>';
        html += `<td class="text-muted small">${i + 1}</td>`;
        cols.forEach(c => {
            const val = row[c];
            if (val === null || val === undefined) {
                html += '<td class="text-danger small">NULL</td>';
            } else {
                html += `<td>${String(val).substring(0, 50)}</td>`;
            }
        });
        html += '</tr>';
    });
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function populateAllSelects(data) {
    // Helper to populate a select with options
    function populate(selectId, options, defaultAll = false) {
        const sel = document.getElementById(selectId);
        if (!sel) return;
        sel.innerHTML = '';
        if (defaultAll) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = '全部列';
            sel.appendChild(opt);
        }
        options.forEach(col => {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            sel.appendChild(opt);
        });
    }

    populate('missing-columns', allColumns);
    populate('dup-columns', allColumns);
    populate('outlier-columns', numericCols);
    populate('type-column', allColumns);
}

function bindEvents() {
    // Show/hide fill options based on missing method
    const missingMethod = document.getElementById('missing-method');
    const fillOptions = document.getElementById('fill-options');
    if (missingMethod && fillOptions) {
        missingMethod.addEventListener('change', function() {
            fillOptions.style.display = this.value === 'fill_missing' ? 'block' : 'none';
        });
    }

    // Show/hide fill value input
    const fillMethod = document.getElementById('fill-method');
    const fillValueGroup = document.getElementById('fill-value-group');
    if (fillMethod && fillValueGroup) {
        fillMethod.addEventListener('change', function() {
            fillValueGroup.style.display = this.value === 'constant' ? 'block' : 'none';
        });
    }

    // Threshold slider display
    const thresholdSlider = document.getElementById('outlier-threshold');
    const thresholdVal = document.getElementById('threshold-val');
    if (thresholdSlider && thresholdVal) {
        thresholdSlider.addEventListener('input', function() {
            thresholdVal.textContent = this.value;
        });
    }
}

async function applyCleaning(tab) {
    let operation, params = {};

    const resultEl = document.getElementById('clean-result');
    const errorEl = document.getElementById('clean-error');
    resultEl.style.display = 'none';
    errorEl.style.display = 'none';

    if (tab === 'missing') {
        const method = document.getElementById('missing-method').value;
        operation = method;
        const cols = Array.from(document.getElementById('missing-columns').selectedOptions).map(o => o.value);

        if (method === 'fill_missing') {
            params.columns = cols;
            params.method = document.getElementById('fill-method').value;
            if (params.method === 'constant') {
                params.fill_value = document.getElementById('fill-value').value;
            }
        } else {
            params.columns = cols;
            params.how = 'any';
        }
    } else if (tab === 'duplicates') {
        operation = 'drop_duplicates';
        params.subset = Array.from(document.getElementById('dup-columns').selectedOptions).map(o => o.value);
    } else if (tab === 'outliers') {
        const action = document.getElementById('outlier-action').value;
        if (action === 'detect') {
            operation = 'detect_outliers';
        } else {
            operation = 'handle_outliers';
        }
        params.columns = Array.from(document.getElementById('outlier-columns').selectedOptions).map(o => o.value);
        params.method = document.getElementById('outlier-method').value;
        params.threshold = parseFloat(document.getElementById('outlier-threshold').value);
        if (action !== 'detect') {
            params.method = action;
        }
    } else if (tab === 'type') {
        operation = 'convert_type';
        params.column = document.getElementById('type-column').value;
        params.new_type = document.getElementById('type-target').value;
    }

    const spinner = document.getElementById('preview-spinner');
    if (spinner) spinner.classList.remove('d-none');

    try {
        const data = await ajaxPost('/api/clean/apply', { operation, params });
        if (spinner) spinner.classList.add('d-none');

        if (data.success) {
            updateRowCount(data.column_info);
            updatePreviewTable(data.preview_data, data.column_info);

            const meta = data.result_metadata;
            let msg = '操作成功！';
            if (meta) {
                if (meta.rows_removed !== undefined) {
                    msg += ` 删除了 ${meta.rows_removed} 行。`;
                }
                if (meta.duplicates_removed !== undefined) {
                    msg += ` 删除了 ${meta.duplicates_removed} 个重复行。`;
                }
                if (meta.total_filled !== undefined) {
                    msg += ` 填充了 ${meta.total_filled} 个缺失值。`;
                }
                if (meta.outlier_counts) {
                    const total = Object.values(meta.outlier_counts).reduce((a, b) => a + b, 0);
                    msg += ` 检测到 ${total} 个异常值。`;
                }
                if (meta.outlier_pct) {
                    for (const [col, pct] of Object.entries(meta.outlier_pct)) {
                        msg += ` ${col}: ${pct}%`;
                    }
                }
            }
            resultEl.textContent = msg;
            resultEl.style.display = 'block';
        } else {
            errorEl.textContent = '操作失败: ' + (data.error || '未知错误');
            errorEl.style.display = 'block';
        }
    } catch (e) {
        if (spinner) spinner.classList.add('d-none');
        errorEl.textContent = '请求失败: ' + e.message;
        errorEl.style.display = 'block';
    }
}

async function resetData() {
    try {
        const data = await ajaxPost('/api/clean/reset', {});
        if (data.success) {
            updateRowCount(data.column_info);
            updatePreviewTable(data.preview_data, data.column_info);
            document.getElementById('clean-result').textContent = '数据已重置为原始状态。';
            document.getElementById('clean-result').style.display = 'block';
        }
    } catch (e) {
        showToast('重置失败: ' + e.message);
    }
}
