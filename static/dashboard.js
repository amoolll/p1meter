// Main dashboard controller. As of v4, this file does NOT calculate any
// business values (self-sufficiency %, net kWh, monthly cost projections).
// All of that comes pre-computed from /api/dashboard and /api/dashboard/month.
// This file's job is: fetch, then paint the DOM. Formatting only.

function saveUIState() {
    const state = {
        filterOpen: document.getElementById('filter-section').classList.contains('open'),
        chartPowerOpen: document.getElementById('chart-power').classList.contains('open'),
        chartGasOpen: document.getElementById('chart-gas').classList.contains('open'),
        chartSolarOpen: document.getElementById('chart-solar2').classList.contains('open'),
        tariffOpen: document.querySelector('.tariff-section').classList.contains('open'),
        interval: currentFilters.interval,
        range: currentFilters.range,
        date: currentFilters.date
    };
    localStorage.setItem('uiState', JSON.stringify(state));
}

function restoreUIState() {
    const saved = localStorage.getItem('uiState');
    if (!saved) return;

    const state = JSON.parse(saved);

    if (state.filterOpen) document.getElementById('filter-section').classList.add('open');
    if (state.chartPowerOpen) document.getElementById('chart-power').classList.add('open');
    if (state.chartGasOpen) document.getElementById('chart-gas').classList.add('open');
    // Always force solar chart open
    document.getElementById('chart-solar2').classList.add('open');
    if (state.tariffOpen) document.querySelector('.tariff-section').classList.add('open');

    currentFilters.interval = state.interval;
    currentFilters.range = state.range;
    currentFilters.date = state.date || new Date().toISOString().split('T')[0];

    document.querySelectorAll('[data-interval]').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.interval === state.interval) btn.classList.add('active');
    });
    document.querySelectorAll('[data-range]').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.range === state.range) btn.classList.add('active');
    });
}

function toggleFilter() {
    document.getElementById('filter-section').classList.toggle('open');
    saveUIState();
}

function toggleChart(btn) {
    btn.closest('.chart-container-box').classList.toggle('open');
    saveUIState();
    setTimeout(() => {
        Object.keys(charts).forEach(key => {
            if (charts[key]) {
                try { charts[key].resize(); } catch (e) {}
            }
        });
    }, 300);
}

function toggleTariff() {
    document.querySelector('.tariff-section').classList.toggle('open');
    saveUIState();
}

async function populateDateDropdown() {
    try {
        const today = new Date();
        const dateSelect = document.getElementById('dateSelect');

        dateSelect.innerHTML = '<option value="">Select Date</option>';

        // Add last 30 days
        for (let i = 0; i < 30; i++) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];
            const option = document.createElement('option');
            option.value = dateStr;

            let displayText = dateStr;
            if (i === 0) {
                displayText = `Today (${dateStr})`;
            } else if (i === 1) {
                displayText = `Yesterday (${dateStr})`;
            } else {
                const dateObj = new Date(dateStr);
                displayText = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            }

            option.textContent = displayText;
            dateSelect.appendChild(option);
        }

        const todayStr = today.toISOString().split('T')[0];
        dateSelect.value = todayStr;
        currentFilters.date = todayStr;
    } catch (e) {
        console.error("Error populating date dropdown:", e);
    }
}

function initializeMonth() {
    const now = new Date();
    const monthName = now.toLocaleString('default', { month: 'long', year: 'numeric' });

    document.querySelectorAll('.month-title').forEach(el => {
        el.textContent = el.textContent.split(' -')[0] + ' - ' + monthName;
    });
}

function populateMonthSelector() {
    const select = document.getElementById('month-select');
    const now = new Date();

    for (let i = 0; i < 12; i++) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        const monthStr = d.toLocaleString('default', { month: 'long', year: 'numeric' });
        const dateStr = d.toISOString().split('T')[0].substring(0, 7);

        const opt = document.createElement('option');
        opt.value = dateStr;
        opt.textContent = monthStr;
        select.appendChild(opt);
    }
}

// Paints all 4 top cards from a /api/dashboard response. No math — the
// backend already decided labels, css classes, bands, and rounded values.
function updateAllCards(data) {
    const daily = data.daily;

    const cardTotal = document.getElementById('card-total');
    const hdrTotal = document.getElementById('hdr-total');
    const lblNet = document.getElementById('lbl-net-val');

    hdrTotal.textContent = daily.total_label;
    cardTotal.className = `card ${daily.total_css_class}`;
    lblNet.textContent = `${daily.net_is_surplus ? '+' : ''}${daily.net_kwh.toFixed(2)} kWh`;
    lblNet.classList.remove('grid', 'surplus');
    lblNet.classList.add(daily.total_css_class);

    document.getElementById('lbl-today-grid').textContent = `${daily.import_kwh.toFixed(2)} kWh`;
    document.getElementById('lbl-today-surplus').textContent = `${daily.export_kwh.toFixed(2)} kWh`;
    document.getElementById('lbl-gas-val').textContent = `${daily.gas_m3.toFixed(3)} m³`;
    document.getElementById('lbl-gas-yday').textContent = `${data.yesterday.gas_m3.toFixed(3)} m³`;

    document.getElementById('lbl-solar-val').textContent = `${daily.solar_kwh.toFixed(2)} kWh`;
    document.getElementById('lbl-solar-yday').textContent = `${data.yesterday.solar_kwh.toFixed(2)} kWh`;

    const selfSuffElement = document.getElementById('lbl-self-suff');
    selfSuffElement.textContent = `${daily.self_sufficiency_percent.toFixed(1)} %`;
    window.lastDailySelfSufficiency = daily.self_sufficiency_percent;
    selfSuffElement.classList.remove('low', 'medium', 'high');
    selfSuffElement.classList.add(daily.self_sufficiency_band);

    updateCostLabels(data.monthly_projection);
}

// Paints the "monthly projection" card from a monthly_projection object.
// Shared shape between /api/dashboard's projection and /api/dashboard/month's
// explicit month summary — see loadMonthData below.
function updateCostLabels(mp) {
    document.getElementById('m-grid-kwh').textContent = `${mp.grid_kwh.toFixed(2)} kWh`;
    document.getElementById('m-grid-cost').textContent = `€${mp.grid_cost.toFixed(2)}`;

    document.getElementById('m-surplus-kwh').textContent = `${mp.surplus_kwh.toFixed(2)} kWh`;
    document.getElementById('m-surplus-cost').textContent = `€${mp.surplus_cost.toFixed(2)}`;

    document.getElementById('m-solar-kwh').textContent = `${mp.solar_kwh.toFixed(2)} kWh`;

    document.getElementById('m-gas-m3').textContent = `${mp.gas_m3.toFixed(3)} m³`;
    document.getElementById('m-gas-cost').textContent = `€${mp.gas_cost.toFixed(2)}`;
}

// Explicit month selector (separate from the daily date picker).
async function loadMonthData() {
    const monthVal = document.getElementById('month-select').value;
    if (!monthVal) return;

    try {
        const res = await fetch(`${API}/api/dashboard/month?month=${monthVal}`);
        const data = await res.json();

        updateCostLabels(data);

        const mSuffElement = document.getElementById('m-solar-suff');
        mSuffElement.textContent = `${data.self_sufficiency_percent.toFixed(1)}%`;
        mSuffElement.classList.remove('low', 'medium', 'high');
        mSuffElement.classList.add(data.self_sufficiency_band);

        const [year, month] = monthVal.split('-');
        const monthName = new Date(year, parseInt(month) - 1).toLocaleString('default', { month: 'long', year: 'numeric' });
        document.querySelectorAll('.month-title').forEach(el => {
            el.textContent = el.textContent.split(' -')[0] + ' - ' + monthName;
        });
    } catch (e) {
        console.error("Month data error:", e);
    }
}

// Fetches the full view-model for one date and paints cards + chart.
// Called both on initial load and whenever the date picker changes.
async function loadChartData(dateStr) {
    try {
        const res = await fetch(`${API}/api/dashboard?date=${dateStr}`);
        const data = await res.json();

        lastHistory = data.history || [];
        updateAllCards(data);

        if (lastHistory.length > 0) {
            renderDynamicCharts(lastHistory);
        }
    } catch (e) {
        console.error("Error loading chart data:", e);
    }
}

function setFilter(type, value, btnElement) {
    currentFilters[type] = value;

    if (btnElement) {
        const parent = btnElement.parentElement;
        parent.querySelectorAll('.btn-toggle').forEach(b => b.classList.remove('active'));
        btnElement.classList.add('active');
    }

    if (type === 'range') {
        document.getElementById('timeRangeSelect').value = value;
    } else if (type === 'interval') {
        document.getElementById('intervalSelect').value = value;
    } else if (type === 'date') {
        document.getElementById('dateSelect').value = value;
    }

    saveUIState();

    if (type === 'date') {
        loadChartData(value);
    } else if (lastHistory.length > 0) {
        renderDynamicCharts(lastHistory);
    }
}

// Live power reading — always "now", independent of the selected date.
// Polled every 10s so the tab title / header status never goes stale,
// even while you're looking at a past date's chart.
async function refreshLiveStatus() {
    try {
        const res = await fetch(`${API}/api/live`);
        const live = await res.json();

        document.title = live.title;

        const liveStatus = document.getElementById('liveStatus');
        const arrow = live.is_surplus ? '⬆' : '⬇';
        liveStatus.innerHTML = `${live.status_label} <span class="arrow-icon blink">${arrow}</span>`;
        liveStatus.className = live.is_surplus ? 'surplus' : 'grid';
    } catch (e) {
        console.error("Live status error:", e);
    }
}

// Runs on load and every 10s. Only re-fetches the dashboard view (cards +
// chart) when the user is actually viewing today — otherwise a selected
// past date would get silently overwritten by this poll, which was the
// original bug we fixed in v3. Live status always refreshes regardless.
async function loadDashboard() {
    try {
        await loadTariffs();

        document.getElementById('timeRangeSelect').value = currentFilters.range;
        document.getElementById('intervalSelect').value = currentFilters.interval;

        await refreshLiveStatus();

        const todayStr = new Date().toISOString().split('T')[0];
        if (currentFilters.date === todayStr) {
            await loadChartData(todayStr);
        }
    } catch (e) {
        console.error("Dashboard error:", e);
    }
}
