/* === Shared Utility Functions === */

function showLoading(selector) {
    const el = document.querySelector(selector);
    if (el) el.classList.remove('d-none');
}

function hideLoading(selector) {
    const el = document.querySelector(selector);
    if (el) el.classList.add('d-none');
}

function showToast(message, type = 'danger') {
    const container = document.querySelector('.container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.insertBefore(alert, container.firstChild);
    setTimeout(() => alert.remove(), 5000);
}

async function ajaxPost(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return response.json();
}

async function ajaxGet(url) {
    const response = await fetch(url);
    return response.json();
}

function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '—';
    if (Number.isInteger(num)) return num.toLocaleString();
    return num.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 4
    });
}
