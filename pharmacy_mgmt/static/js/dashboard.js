// Read data injected by Django's json_script filter
const distributionData = JSON.parse(
    document.getElementById('distribution-data').textContent
);
const monthlyData = JSON.parse(
    document.getElementById('monthly-data').textContent
);
const yearlyData = JSON.parse(
    document.getElementById('yearly-data').textContent
);

const css   = getComputedStyle(document.documentElement);
const color = name => css.getPropertyValue(name).trim();

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color       = color('--ink-soft');

const palette = [
    color('--data-blue'),
    color('--data-teal'),
    color('--data-amber'),
    color('--data-coral'),
    '#9B59B6',
    '#E67E22',
];

// ── Donut — stock distribution ──────────────────────────
if (distributionData.labels.length > 0) {
    new Chart(document.getElementById('donutChart'), {
        type: 'doughnut',
        data: {
            labels: distributionData.labels,
            datasets: [{
                data: distributionData.values,
                backgroundColor: distributionData.labels.map(
                    (_, i) => palette[i % palette.length]
                ),
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 4
            }]
        },
        options: {
            cutout: '68%',
            plugins: { legend: { display: false } },
            maintainAspectRatio: false
        }
    });

    // Build legend manually below the chart
    const legendEl = document.getElementById('donutLegend');
    if (legendEl) {
        distributionData.labels.forEach((label, i) => {
            const item = document.createElement('span');
            item.className = 'legend__item';
            item.innerHTML = `
                <span class="legend__dot"
                  style="background:${palette[i % palette.length]}">
                </span>
                ${label} · ${distributionData.values[i]}
            `;
            legendEl.appendChild(item);
        });
    }
} else {
    const canvas = document.getElementById('donutChart');
    if (canvas) {
        canvas.parentElement.innerHTML =
            '<p style="text-align:center; color:var(--ink-faint); ' +
            'padding:40px 0; font-size:13px;">No sales recorded yet.</p>';
    }
}

// ── Bar — monthly sales ─────────────────────────────────
new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: {
        labels: monthlyData.labels,
        datasets: [{
            label: 'Units Sold',
            data: monthlyData.values,
            backgroundColor: color('--data-blue'),
            borderRadius: 6,
            maxBarThickness: 40
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false } },
            y: {
                grid: { color: '#EEF2F1' },
                ticks: { callback: v => v.toLocaleString() }
            }
        }
    }
});

// ── Line — yearly revenue trend ─────────────────────────
new Chart(document.getElementById('lineChart'), {
    type: 'line',
    data: {
        labels: yearlyData.labels,
        datasets: [{
            label: 'Revenue (৳)',
            data: yearlyData.values,
            borderColor: color('--data-blue'),
            backgroundColor: 'rgba(47,111,237,0.08)',
            pointBackgroundColor: color('--data-blue'),
            pointRadius: 5,
            tension: 0.35,
            fill: true
        }]
    },
    options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false } },
            y: {
                grid: { color: '#EEF2F1' },
                ticks: { callback: v => '৳' + v.toLocaleString() }
            }
        }
    }
});