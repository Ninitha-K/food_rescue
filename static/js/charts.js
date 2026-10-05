// Dashboard Chart Visualizations using Chart.js

function renderAdminCharts(statsData) {
    const statusCtx = document.getElementById('donationsStatusChart');
    if (statusCtx && statsData) {
        new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Pending', 'Assigned', 'Picked Up', 'In Transit', 'Delivered', 'Distributed'],
                datasets: [{
                    data: [
                        statsData.donations_by_status.PENDING || 0,
                        statsData.donations_by_status.VOLUNTEER_ASSIGNED || 0,
                        statsData.donations_by_status.PICKED_UP || 0,
                        statsData.donations_by_status.IN_TRANSIT || 0,
                        statsData.donations_by_status.DELIVERED || 0,
                        statsData.donations_by_status.DISTRIBUTED || 0
                    ],
                    backgroundColor: [
                        '#f59e0b', '#3b82f6', '#0284c7', '#8b5cf6', '#10b981', '#059669'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    const perfCtx = document.getElementById('deliveryPerformanceChart');
    if (perfCtx && statsData) {
        new Chart(perfCtx, {
            type: 'bar',
            data: {
                labels: ['Active Deliveries', 'Completed Deliveries', 'Meals Redistributed', 'Beneficiaries Served'],
                datasets: [{
                    label: 'Redistribution System Metrics',
                    data: [
                        statsData.active_deliveries,
                        statsData.completed_deliveries,
                        statsData.total_meals_redistributed,
                        statsData.total_beneficiaries_served
                    ],
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#6366f1']
                }]
            },
            options: {
                responsive: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // Fetch stats via REST API if chart containers exist
    if (document.getElementById('donationsStatusChart')) {
        fetch('/api/stats')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    renderAdminCharts(data);
                }
            })
            .catch(err => console.error('Error fetching chart stats:', err));
    }
});
