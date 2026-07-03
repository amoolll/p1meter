// Shared state used across dashboard.js, charts.js, tariffs.js, backup.js
// Loaded first so every other module can reference these.
const API = window.location.origin;
let charts = {};
let currentFilters = { interval: 'raw', range: '24h', date: new Date().toISOString().split('T')[0] };
let tariffRates = { import: 0.25, export: 0.11, gas: 1.35 };
let lastHistory = [];

function showNotification(message) {
    const notif = document.getElementById('notification');
    notif.textContent = message;
    notif.classList.add('show');
    setTimeout(() => notif.classList.remove('show'), 3000);
}
