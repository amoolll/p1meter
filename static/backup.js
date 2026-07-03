// Database backup & restore buttons. Unchanged from v3 — this was already
// thin (just handles the file download/upload UX, no business logic).

async function backupDatabase() {
    try {
        const response = await fetch(`${API}/api/backup`, { method: 'GET' });
        if (!response.ok) {
            showNotification('❌ Backup failed: ' + response.statusText);
            return;
        }

        const blob = await response.blob();
        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        const filename = `p1meter_backup_${timestamp}.sql`;

        // Download the file
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showNotification(`✅ Database backup downloaded: ${filename}`);
    } catch (error) {
        console.error('Backup error:', error);
        showNotification('❌ Backup error: ' + error.message);
    }
}

async function restoreDatabase(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
        showNotification('⏳ Restoring database... Please wait');

        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API}/api/restore`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.text();
            showNotification('❌ Restore failed: ' + error);
            return;
        }

        showNotification('✅ Database restored! Reloading...');

        // Reset file input
        document.getElementById('fileInput').value = '';

        // Reload page after 2 seconds
        setTimeout(() => location.reload(), 2000);
    } catch (error) {
        console.error('Restore error:', error);
        showNotification('❌ Restore error: ' + error.message);
        document.getElementById('fileInput').value = '';
    }
}
