// Bootstraps the page once everything else has loaded.
window.addEventListener('load', () => {
    populateMonthSelector();
    populateDateDropdown();
    initializeMonth();
    restoreUIState();
    loadDashboard();
    // Cards/chart only refresh when viewing today (see loadDashboard);
    // live status always refreshes regardless of selected date.
    setInterval(loadDashboard, 10000);
});
