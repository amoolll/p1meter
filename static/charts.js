// Chart rendering & data-shaping. Pure presentation — no business math here.

// "Today" / "Yesterday" / "Jun 25, 2026" — used in chart tooltip titles so
// the tooltip reflects whichever date is actually selected, not a hardcoded "Today".
function formatDateLabel(dateStr) {
    const todayStr = new Date().toISOString().split('T')[0];
    const yesterdayStr = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    if (dateStr === todayStr) return 'Today';
    if (dateStr === yesterdayStr) return 'Yesterday';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function applyTimeRangeFilter(history) {
    if (!history || history.length === 0) return history;
    
    // Parse the last data point's time
    const lastTime = history[history.length - 1].time;
    const [lastHour, lastMin] = lastTime.split(':').map(Number);
    const lastDate = new Date(2000, 0, 1, lastHour, lastMin, 0);
    
    let cutoffDate;
    if (currentFilters.range === '1h') {
        cutoffDate = new Date(lastDate.getTime() - 60 * 60 * 1000);
    } else if (currentFilters.range === '6h') {
        cutoffDate = new Date(lastDate.getTime() - 6 * 60 * 60 * 1000);
    } else if (currentFilters.range === '12h') {
        cutoffDate = new Date(lastDate.getTime() - 12 * 60 * 60 * 1000);
    } else if (currentFilters.range === '7d') {
        cutoffDate = new Date(lastDate.getTime() - 7 * 24 * 60 * 60 * 1000);
    } else {
        return history; // 24h - return all
    }
    
    return history.filter(h => {
        const [hour, min] = h.time.split(':').map(Number);
        const pointDate = new Date(2000, 0, 1, hour, min, 0);
        return pointDate >= cutoffDate;
    });
}

function applyIntervalAggregation(history) {
    if (currentFilters.interval === 'raw') return history;
    
    const aggregateMinutes = {
        '5m': 5,
        '10m': 10,
        '1h': 60
    }[currentFilters.interval] || 1;
    
    const aggregated = [];
    let bucket = [];
    let bucketTime = null;
    
    history.forEach(point => {
        // Parse "HH:MM" manually instead of new Date('2000-01-01 ' + point.time) —
        // that non-ISO string format ("YYYY-MM-DD HH:MM" with a space) is parsed
        // leniently by Chrome/V8 but returns Invalid Date in Safari/WebKit, which
        // silently breaks bucketing (NaN) only in Safari. The multi-arg Date
        // constructor below is spec-defined and behaves identically everywhere.
        const [pHour, pMin] = point.time.split(':').map(Number);
        const time = new Date(2000, 0, 1, pHour, pMin, 0);
        const minutes = Math.floor(time.getTime() / 60000);
        const bucketIndex = Math.floor(minutes / aggregateMinutes);
        
        if (bucketTime === null) bucketTime = bucketIndex;
        
        if (bucketIndex !== bucketTime) {
            if (bucket.length > 0) {
                const sum = bucket.reduce((a, b) => ({
                    time: bucket[0].time,
                    import_w: (a.import_w || 0) + (b.import_w || 0),
                    export_w: (a.export_w || 0) + (b.export_w || 0),
                    gas_m3: (a.gas_m3 || 0) + (b.gas_m3 || 0),
                    solar_w: (a.solar_w || 0) + (b.solar_w || 0)
                }));
                aggregated.push({
                    time: sum.time,
                    import_w: sum.import_w / bucket.length,
                    export_w: sum.export_w / bucket.length,
                    gas_m3: sum.gas_m3 / bucket.length,
                    solar_w: sum.solar_w / bucket.length
                });
            }
            bucket = [point];
            bucketTime = bucketIndex;
        } else {
            bucket.push(point);
        }
    });
    
    if (bucket.length > 0) {
        const sum = bucket.reduce((a, b) => ({
            time: bucket[0].time,
            import_w: (a.import_w || 0) + (b.import_w || 0),
            export_w: (a.export_w || 0) + (b.export_w || 0),
            gas_m3: (a.gas_m3 || 0) + (b.gas_m3 || 0),
            solar_w: (a.solar_w || 0) + (b.solar_w || 0)
        }));
        aggregated.push({
            time: sum.time,
            import_w: sum.import_w / bucket.length,
            export_w: sum.export_w / bucket.length,
            gas_m3: sum.gas_m3 / bucket.length,
            solar_w: sum.solar_w / bucket.length
        });
    }
    
    return aggregated;
}

function renderDynamicCharts(history) {
    let filteredHistory = applyTimeRangeFilter(history);
    filteredHistory = applyIntervalAggregation(filteredHistory);

    if (filteredHistory.length === 0) return;

    const labels = filteredHistory.map(h => h.time);
    
    // Split grid import (red) and surplus export (green)
    const gridImport = filteredHistory.map(h => {
        const imp = (h.import_w || 0) / 1000;
        return imp > 0 ? imp : 0;
    });
    const surplusExport = filteredHistory.map(h => {
        const exp = (h.export_w || 0) / 1000;
        return exp > 0 ? exp : 0;
    });
    
    // Gas: Calculate delta (change between consecutive points, not cumulative)
    const gasData = filteredHistory.map((h, i) => {
        if (i === 0) return 0; // First point has no previous value
        const prev = filteredHistory[i - 1].gas_m3 || 0;
        const curr = h.gas_m3 || 0;
        const delta = curr - prev;
        return delta > 0 ? delta : 0; // Only show positive changes
    });
    
    const solarFlow = filteredHistory.map(h => {
        // Show on negative side of chart
        const val = (h.solar_w || 0);
        return val > 0 ? -val : 0;
    });
    
    // Also update surplus to show on negative side
    const surplusExportNegative = filteredHistory.map((h) => {
        const exp = (h.export_w || 0) / 1000;
        return exp > 0 ? -exp : 0;
    });

    // Power Flow Chart: Red (grid import) + Light Yellow (surplus export) + Light Green (solar)
    drawChart('mainFlowChart', labels, [
        {
            label: 'Grid Import',
            data: gridImport,
            borderColor: '#fca5a5',
            backgroundColor: 'rgba(252, 165, 165, 0.15)',
            borderWidth: 2,
            fill: true,
            tension: 0.3
        },
        {
            label: 'Surplus Export',
            data: surplusExportNegative,
            borderColor: '#fef08a',  // Light yellow
            backgroundColor: 'rgba(254, 240, 138, 0.25)',
            borderWidth: 2,
            fill: true,
            tension: 0.3
        },
        {
            label: 'Solar Generated',
            data: solarFlow,
            borderColor: '#86efac',  // Light green
            backgroundColor: 'rgba(134, 239, 172, 0.25)',
            borderWidth: 2.5,
            fill: true,
            tension: 0.3
        }
    ]);

    // Update the solar chart title
    // (no longer needed - title is already correct in HTML)

    // --- GAS CHART ---
    drawChart('gasChart2', labels, [{
        label: 'Gas Usage',
        data: gasData,
        borderColor: '#a78bfa',
        backgroundColor: 'rgba(167, 139, 250, 0.15)',
        fill: true,
        tension: 0.1,
        borderWidth: 2
    }]);

    // --- SOLAR PRODUCED CHART ---
    const solarData = filteredHistory.map(h => (h.solar_w || 0));
    drawChart('solarChart2', labels, [{
        label: 'Solar Produced',
        data: solarData,
        borderColor: '#86efac',  // Light green
        backgroundColor: 'rgba(134, 239, 172, 0.25)',
        fill: true,
        tension: 0.3,
        borderWidth: 2.5
    }]);
}

function drawChart(id, labels, datasets) {
    try {
        const canvas = document.getElementById(id);
        if (!canvas) {
            console.error('[CHART] Canvas not found:', id);
            return;
        }
        
        // Destroy existing chart if it exists to avoid canvas reuse issues
        if (charts[id]) {
            charts[id].destroy();
            delete charts[id];
        }
        
        charts[id] = new Chart(canvas, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                elements: { point: { radius: 0 } },
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0, 0, 0, 0.85)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#555',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                        callbacks: {
                            title: (ctx) => {
                                const timeStr = ctx[0].label || '';
                                return `${formatDateLabel(currentFilters.date)} ${timeStr}`;
                            },
                            beforeLabel: (ctx) => {
                                // Return empty to skip default label
                                return '';
                            },
                            label: (ctx) => {
                                // Only process first dataset to avoid multiple lines
                                if (ctx.datasetIndex !== 0) {
                                    return '';
                                }
                                
                                if (id === 'mainFlowChart') {
                                    // Power Flow Chart
                                    // Dataset 0: Grid Import (positive = import from grid in kW)
                                    // Dataset 1: Surplus Export (negative = export to grid in kW)
                                    // Dataset 2: Solar (negative on chart, but we ignore it for display)
                                    
                                    const chart = ctx.chart;
                                    const dataIndex = ctx.dataIndex;
                                    
                                    const gridKw = chart.data.datasets[0].data[dataIndex] || 0;
                                    const surplusKw = chart.data.datasets[1].data[dataIndex] || 0;
                                    
                                    // Convert kW to W and show appropriately
                                    const gridW = gridKw * 1000;
                                    const surplusW = Math.abs(surplusKw) * 1000; // Take absolute since stored as negative
                                    
                                    if (gridW > 50) {
                                        // Showing grid import
                                        return `Grid: ${gridW.toFixed(0)} W`;
                                    } else if (surplusW > 50) {
                                        // Showing surplus export
                                        return `Surplus: ${surplusW.toFixed(0)} W`;
                                    } else {
                                        // Both near zero
                                        return `Net: 0 W`;
                                    }
                                    
                                } else if (id === 'gasChart2') {
                                    // Gas Consumption Chart
                                    // Data is in m³ (cubic meters)
                                    const gasM3 = ctx.parsed.y || 0;
                                    return `Gas: ${gasM3.toFixed(4)} m³`;
                                    
                                } else if (id === 'solarChart2') {
                                    // Solar Production Chart
                                    // Data is in W (watts) - actual solar power at that moment
                                    const solarW = ctx.parsed.y || 0;
                                    return `Solar: ${solarW.toFixed(0)} W`;
                                    
                                } else {
                                    // Default for other charts
                                    const val = ctx.parsed.y;
                                    if (val === null) return '';
                                    return `${ctx.dataset.label}: ${val.toFixed(2)}`;
                                }
                            },
                            footer: () => ''
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#a0aec0', font: { size: 11 } } },
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#a0aec0', font: { size: 11 } } }
                }
            }
        });
    } catch (err) {
        console.error('[CHART] Error drawing', id, err);
    }
}
