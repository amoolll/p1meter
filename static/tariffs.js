// Tariff settings panel: load current rates, save new ones.
// This was already "thin" (no business math), so it's unchanged from v3.

async function loadTariffs() {
    try {
        // Try to load from database first
        const response = await fetch(`${API}/api/tariff`);
        const data = await response.json();

        tariffRates.import = data.import_rate;
        tariffRates.export = data.export_rate;
        tariffRates.gas = data.gas_rate;

        // Save to localStorage as backup
        localStorage.setItem('tariffRates', JSON.stringify({
            import: data.import_rate,
            export: data.export_rate,
            gas: data.gas_rate
        }));
    } catch (error) {
        // Fallback to localStorage
        const stored = localStorage.getItem('tariffRates');
        if (stored) {
            const data = JSON.parse(stored);
            tariffRates.import = data.import;
            tariffRates.export = data.export;
            tariffRates.gas = data.gas;
        }
    }

    // Update UI with current values
    document.getElementById('rate-import').value = tariffRates.import;
    document.getElementById('rate-export').value = tariffRates.export;
    document.getElementById('rate-gas').value = tariffRates.gas;

    document.getElementById('tariff-quick-summary').textContent =
        `Import: €${tariffRates.import.toFixed(2)}/kWh | Export: €${tariffRates.export.toFixed(2)}/kWh | Gas: €${tariffRates.gas.toFixed(2)}/m³`;
}

async function saveTariffs() {
    const rImp = parseFloat(document.getElementById('rate-import').value);
    const rExp = parseFloat(document.getElementById('rate-export').value);
    const rGas = parseFloat(document.getElementById('rate-gas').value);

    if (isNaN(rImp) || isNaN(rExp) || isNaN(rGas) || rImp < 0 || rExp < 0 || rGas < 0) {
        showNotification('❌ Please enter valid positive numbers');
        return;
    }

    try {
        // Save to database
        await fetch(`${API}/api/tariff?import_rate=${rImp}&export_rate=${rExp}&gas_rate=${rGas}`, {
            method: 'POST'
        });

        // Also save to localStorage as backup
        localStorage.setItem('tariffRates', JSON.stringify({
            import: rImp,
            export: rExp,
            gas: rGas
        }));

        // Update local state
        tariffRates.import = rImp;
        tariffRates.export = rExp;
        tariffRates.gas = rGas;

        // Update display
        document.getElementById('tariff-quick-summary').textContent =
            `Import: €${rImp.toFixed(2)}/kWh | Export: €${rExp.toFixed(2)}/kWh | Gas: €${rGas.toFixed(2)}/m³`;

        // Re-fetch the current view so cost figures reflect the new rates
        // (costs are computed server-side now, so we can't just re-format
        // in place — ask the backend to recompute with the new tariff)
        loadChartData(currentFilters.date);

        showNotification('✅ Rates saved!');
    } catch (error) {
        console.error('Tariff save error:', error);
        // Still save to localStorage even if database fails
        localStorage.setItem('tariffRates', JSON.stringify({
            import: rImp,
            export: rExp,
            gas: rGas
        }));
        showNotification('✅ Rates saved locally!');
    }
}
