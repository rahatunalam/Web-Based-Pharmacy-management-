// ---- Filter tabs (Today / Weekly / Monthly / Yearly) ----
document.querySelectorAll('#rangeFilter button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#rangeFilter button').forEach(b => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    // Hook real data fetching here based on btn.dataset.range
  });
});

const css = getComputedStyle(document.documentElement);
const color = name => css.getPropertyValue(name).trim();

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = color('--ink-soft');

// ---- Donut: stock distribution ----
const donutData = {
  labels: ['Napa', 'Napa Extra', 'Famotack', 'Eye Drop'],
  values: [55, 25, 15, 5],
  colors: [color('--data-blue'), color('--data-teal'), color('--data-amber'), color('--data-coral')]
};

new Chart(document.getElementById('donutChart'), {
  type: 'doughnut',
  data: {
    labels: donutData.labels,
    datasets: [{
      data: donutData.values,
      backgroundColor: donutData.colors,
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

// Build matching legend
const legendEl = document.getElementById('donutLegend');
donutData.labels.forEach((label, i) => {
  const item = document.createElement('span');
  item.className = 'legend__item';
  item.innerHTML = `<span class="legend__dot" style="background:${donutData.colors[i]}"></span>${label} · ${donutData.values[i]}%`;
  legendEl.appendChild(item);
});

// ---- Bar: Sale vs Buy ----
new Chart(document.getElementById('barChart'), {
  type: 'bar',
  data: {
    labels: ['Jan', 'Feb', 'Mar'],
    datasets: [
      {
        label: 'Sale',
        data: [3850, 3450, 2150],
        backgroundColor: color('--data-blue'),
        borderRadius: 6,
        maxBarThickness: 34
      },
      {
        label: 'Buy',
        data: [2350, 1300, 1050],
        backgroundColor: color('--data-teal'),
        borderRadius: 6,
        maxBarThickness: 34
      }
    ]
  },
  options: {
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false } },
      y: { grid: { color: '#EEF2F1' }, ticks: { callback: v => v.toLocaleString() } }
    }
  }
});

// ---- Line: yearly trend ----
new Chart(document.getElementById('lineChart'), {
  type: 'line',
  data: {
    labels: ['2021', '2022', '2023', '2024', '2025'],
    datasets: [{
      label: 'Units sold',
      data: [8, 18, 20, 33, 36],
      borderColor: color('--data-blue'),
      backgroundColor: 'rgba(47,111,237,0.08)',
      pointBackgroundColor: color('--data-blue'),
      pointRadius: 4,
      tension: 0.35,
      fill: true
    }]
  },
  options: {
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false } },
      y: { grid: { color: '#EEF2F1' } }
    }
  }
});
