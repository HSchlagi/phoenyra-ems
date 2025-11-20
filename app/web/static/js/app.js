// Phoenyra EMS - Dashboard JavaScript
// =====================================

let powerChart = null;
let priceChart = null;

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    loadForecastData();
    setupSSE();
    
    // Refresh forecast data every 5 minutes
    setInterval(loadForecastData, 5 * 60 * 1000);
});

// Setup Server-Sent Events for real-time updates
let sseConnection = null;

function setupSSE() {
    // Schließe alte Verbindung falls vorhanden
    if (sseConnection) {
        sseConnection.close();
    }
    
    sseConnection = new EventSource('/api/events');
    
    sseConnection.onmessage = (e) => {
        try {
            const state = JSON.parse(e.data);
            updateDashboard(state);
        } catch (err) {
            console.error('Error parsing SSE data:', err);
        }
    };
    
    sseConnection.onerror = (err) => {
        // Nur loggen, kein Reconnect - Browser macht das automatisch
        console.log('SSE verbindet neu...');
    };
    
    sseConnection.onopen = () => {
        console.log('✅ SSE verbunden');
    };
}

// Update Dashboard with new state
function updateDashboard(state) {
    // SoC
    const soc = state.soc || 0;
    document.getElementById('soc-value').innerText = soc.toFixed(1) + ' %';
    document.getElementById('soc-bar').style.width = soc + '%';
    
    // Power
    const power = state.p_bess || 0;
    const powerSign = power >= 0 ? '+' : '';
    document.getElementById('power-value').innerText = powerSign + power.toFixed(1) + ' kW';
    
    const powerStatus = power > 0 ? 'Discharging ⚡' : (power < 0 ? 'Charging 🔋' : 'Idle 💤');
    document.getElementById('power-status').innerText = powerStatus;
    
    // Strategy
    document.getElementById('strategy-value').innerText = state.active_strategy || '--';
    
    // Profit
    if (state.current_plan) {
        document.getElementById('profit-value').innerText = '€' + state.current_plan.expected_profit.toFixed(2);
    }
    
    // System Status
    document.getElementById('grid-power').innerText = (state.p_grid || 0).toFixed(1) + ' kW';
    document.getElementById('pv-power').innerText = (state.p_pv || 0).toFixed(1) + ' kW';
    document.getElementById('load-power').innerText = (state.p_load || 0).toFixed(1) + ' kW';
    document.getElementById('current-price').innerText = (state.price || 0).toFixed(1) + ' €/MWh';
}

// Load Forecast Data
async function loadForecastData() {
    let plan = null;
    let forecast = null;
    
    try {
        // Load Plan
        const planResp = await fetch('/api/plan');
        if (planResp.ok) {
            plan = await planResp.json();
            updatePowerChart(plan);
        }
    } catch (err) {
        console.error('Error loading plan:', err);
    }
    
    try {
        // Load Forecasts
        const forecastResp = await fetch('/api/forecast');
        if (forecastResp.ok) {
            forecast = await forecastResp.json();
            updatePriceChart(forecast, plan);
        }
    } catch (err) {
        console.error('Error loading forecast:', err);
    }
}

// Initialize Charts
function initializeCharts() {
    const powerCtx = document.getElementById('powerChart').getContext('2d');
    const priceCtx = document.getElementById('priceChart').getContext('2d');
    
    // Dark Theme Colors
    const textColor = 'rgb(229, 231, 235)';  // gray-200
    const gridColor = 'rgba(75, 85, 99, 0.3)';  // gray-600 with transparency
    
    powerChart = new Chart(powerCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'BESS Power (kW)',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                },
                {
                    label: 'PV (kW)',
                    data: [],
                    borderColor: 'rgb(234, 179, 8)',
                    backgroundColor: 'rgba(234, 179, 8, 0.2)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                },
                {
                    label: 'Load (kW)',
                    data: [],
                    borderColor: 'rgb(239, 68, 68)',
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: textColor,
                        font: { size: 12 }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMin: -150,
                    suggestedMax: 150,
                    title: {
                        display: true,
                        text: 'Power (kW)',
                        color: textColor
                    },
                    ticks: { color: textColor },
                    grid: { color: gridColor }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time',
                        color: textColor
                    },
                    ticks: { color: textColor },
                    grid: { color: gridColor }
                }
            }
        }
    });
    
    priceChart = new Chart(priceCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Price (€/MWh)',
                    data: [],
                    borderColor: 'rgb(34, 197, 94)',
                    backgroundColor: 'rgba(34, 197, 94, 0.2)',
                    fill: true,
                    yAxisID: 'y',
                    tension: 0.4,
                    borderWidth: 2
                },
                {
                    label: 'SoC (%)',
                    data: [],
                    borderColor: 'rgb(168, 85, 247)',
                    backgroundColor: 'rgba(168, 85, 247, 0.2)',
                    fill: false,
                    yAxisID: 'y1',
                    tension: 0.4,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: textColor,
                        font: { size: 12 }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: 'Price (€/MWh)',
                        color: textColor
                    },
                    ticks: { color: textColor },
                    grid: { color: gridColor }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    beginAtZero: false,
                    min: 0,
                    max: 100,
                    title: {
                        display: true,
                        text: 'SoC (%)',
                        color: textColor
                    },
                    ticks: { color: textColor },
                    grid: {
                        drawOnChartArea: false,
                        color: gridColor
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time',
                        color: textColor
                    },
                    ticks: { color: textColor },
                    grid: { color: gridColor }
                }
            }
        }
    });
}

// Update Power Chart
function updatePowerChart(plan) {
    if (!plan || !plan.schedule) return;
    
    const labels = [];
    const powerData = [];
    
    for (const [ts, power] of plan.schedule) {
        const date = new Date(ts);
        labels.push(date.getHours() + ':00');
        powerData.push(power);
    }
    
    powerChart.data.labels = labels;
    powerChart.data.datasets[0].data = powerData;
    powerChart.update();
}

// Update Price Chart
function updatePriceChart(forecast, plan) {
    if (!forecast || !forecast.prices) return;
    
    const labels = [];
    const priceData = [];
    const socData = [];
    
    // Prices
    for (const [ts, price] of forecast.prices) {
        const date = new Date(ts);
        labels.push(date.getHours() + ':00');
        priceData.push(price);
    }
    
    // SoC from plan metadata
    if (plan && plan.metadata && plan.metadata.soc_schedule) {
        for (const [ts, soc] of plan.metadata.soc_schedule) {
            socData.push(soc);
        }
    }
    
    // PV and Load
    if (forecast.pv && powerChart) {
        const pvData = forecast.pv.map(([ts, power]) => power);
        const loadData = forecast.load.map(([ts, power]) => power);
        
        powerChart.data.labels = labels;
        powerChart.data.datasets[1].data = pvData;
        powerChart.data.datasets[2].data = loadData;
        powerChart.update();
    }
    
    // Berechne dynamische Y-Achsen-Skalierung für Price
    if (priceData.length > 0) {
        const minPrice = Math.min(...priceData);
        const maxPrice = Math.max(...priceData);
        const pricePadding = (maxPrice - minPrice) * 0.1; // 10% Padding
        
        priceChart.options.scales.y.min = Math.max(0, minPrice - pricePadding);
        priceChart.options.scales.y.max = maxPrice + pricePadding;
    }
    
    priceChart.data.labels = labels;
    priceChart.data.datasets[0].data = priceData;
    priceChart.data.datasets[1].data = socData;
    priceChart.update();
}