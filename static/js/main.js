// Main JavaScript Utilities for AI Surplus Food Redistribution System

document.addEventListener('DOMContentLoaded', function () {
    // Auto dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });
});
