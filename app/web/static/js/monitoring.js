// Phoenyra EMS - Monitoring Page

let socChart = null;
let powerChart = null;
let sseConnection = null;

const telemetryHistory = [];
const maxPoints = 900; // ~30 min bei 2s Intervall
let lastRawJson = '';
let lastRawFetch = 0;
const lastStatusSnapshot = {
    mode: null,
    bits: null,
    updated: null,
    source: null,
    text: null,
    code: null
};

document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    loadTelemetryHistory();
    setupSSE();
});

async function loadTelemetryHistory() {
    try {
        const resp = await fetch('/api/monitoring/telemetry?minutes=60&limit=' + maxPoints);
        if (!resp.ok) {
            throw new Error('HTTP ' + resp.status);
        }
        const payload = await resp.json();
        const data = payload.data || [];
        
        telemetryHistory.splice(0, telemetryHistory.length, ...data);
        rebuildChartData();
        
        if (payload.current) {
            updateKpis(payload.current);
            updateStatusSection(data.length ? data[data.length - 1] : payload.current);
        }
    } catch (err) {
        console.error('Monitoring history load failed:', err);
    }
}

function rebuildChartData() {
    if (!socChart || !powerChart) {
        return;
    }
    
    const labels = [];
    const socSeries = [];
    const bessSeries = [];
    const pvSeries = [];
    const loadSeries = [];
    const gridSeries = [];
    
    telemetryHistory.forEach(point => {
        const label = formatTimestamp(point.timestamp);
        labels.push(label);
        socSeries.push(point.soc ?? null);
        bessSeries.push(point.p_bess_kw ?? null);
        pvSeries.push(point.p_pv_kw ?? null);
        loadSeries.push(point.p_load_kw ?? null);
        gridSeries.push(point.p_grid_kw ?? null);
    });
    
    socChart.data.labels = labels;
    socChart.data.datasets[0].data = socSeries;
    socChart.update('none');
    
    powerChart.data.labels = labels;
    powerChart.data.datasets[0].data = bessSeries;
    powerChart.data.datasets[1].data = pvSeries;
    powerChart.data.datasets[2].data = loadSeries;
    powerChart.data.datasets[3].data = gridSeries;
    powerChart.update('none');
}

function initializeCharts() {
    const textColor = 'rgb(226, 232, 240)';
    const gridColor = 'rgba(100, 116, 139, 0.25)';
    
    const socCtx = document.getElementById('socChart').getContext('2d');
    socChart = new Chart(socCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'SoC (%)',
                data: [],
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.2)',
                fill: true,
                tension: 0.2,
                borderWidth: 2,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: textColor, callback: (value) => value + '%' },
                    grid: { color: gridColor }
                },
                x: {
                    ticks: { color: textColor, maxTicksLimit: 8 },
                    grid: { color: 'transparent' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: textColor }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.parsed.y?.toFixed(2)} %`
                    }
                }
            }
        }
    });
    
    const powerCtx = document.getElementById('powerChart').getContext('2d');
    powerChart = new Chart(powerCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'BESS (kW)',
                    data: [],
                    borderColor: '#34d399',
                    backgroundColor: 'rgba(52, 211, 153, 0.15)',
                    tension: 0.2,
                    borderWidth: 2,
                    pointRadius: 0
                },
                {
                    label: 'PV (kW)',
                    data: [],
                    borderColor: '#facc15',
                    backgroundColor: 'rgba(250, 204, 21, 0.1)',
                    tension: 0.2,
                    borderWidth: 2,
                    pointRadius: 0
                },
                {
                    label: 'Last (kW)',
                    data: [],
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(96, 165, 250, 0.1)',
                    tension: 0.2,
                    borderWidth: 2,
                    pointRadius: 0
                },
                {
                    label: 'Netz (kW)',
                    data: [],
                    borderColor: '#f87171',
                    backgroundColor: 'rgba(248, 113, 113, 0.1)',
                    tension: 0.2,
                    borderWidth: 2,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'nearest' },
            scales: {
                y: {
                    ticks: { color: textColor, callback: (value) => value + ' kW' },
                    grid: { color: gridColor }
                },
                x: {
                    ticks: { color: textColor, maxTicksLimit: 8 },
                    grid: { color: 'transparent' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: textColor }
                }
            }
        }
    });
}

function setupSSE() {
    if (sseConnection) {
        sseConnection.close();
    }
    
    sseConnection = new EventSource('/api/events');
    sseConnection.onmessage = (event) => {
        try {
            const state = JSON.parse(event.data);
            handleStateUpdate(state);
        } catch (err) {
            console.error('Failed to parse monitoring SSE:', err);
        }
    };
    
    sseConnection.onerror = () => {
        console.log('Monitoring SSE reconnecting...');
    };
}

function handleStateUpdate(state) {
    if (!state || !state.timestamp) {
        return;
    }
    
    updateKpis(state);
    
    const point = {
        timestamp: state.timestamp,
        soc: state.soc,
        p_bess_kw: state.p_bess,
        p_grid_kw: state.p_grid,
        p_load_kw: state.p_load,
        p_pv_kw: state.p_pv,
        setpoint_kw: state.setpoint_kw,
        voltage_v: state.voltage_v,
        temperature_c: state.temp_c,
        mode: state.mode,
        status_bits: state.status_bits,
        telemetry_source: state.telemetry_source,
        soh: state.soh,
        max_charge_power_kw: state.max_charge_power_kw,
        max_discharge_power_kw: state.max_discharge_power_kw,
        status_code: state.status_code,
        status_text: state.status_text,
        active_alarms: Array.isArray(state.active_alarms) ? state.active_alarms : [],
        insulation_kohm: state.insulation_kohm
    };
    
    mergeTelemetryPoint(point);
    updateStatusSection(point);
    
    if (state.telemetry_source === 'mqtt') {
        const now = Date.now();
        if (now - lastRawFetch > 8000) {
            refreshLatestRaw();
        }
    }
}

function mergeTelemetryPoint(point) {
    const label = formatTimestamp(point.timestamp);
    const lastEntry = telemetryHistory[telemetryHistory.length - 1];
    const lastLabel = socChart.data.labels[socChart.data.labels.length - 1];
    
    if (lastEntry && lastLabel === label) {
        telemetryHistory[telemetryHistory.length - 1] = Object.assign({}, lastEntry, point);
        socChart.data.datasets[0].data[socChart.data.datasets[0].data.length - 1] = point.soc ?? null;
        powerChart.data.datasets[0].data[powerChart.data.datasets[0].data.length - 1] = point.p_bess_kw ?? null;
        powerChart.data.datasets[1].data[powerChart.data.datasets[1].data.length - 1] = point.p_pv_kw ?? null;
        powerChart.data.datasets[2].data[powerChart.data.datasets[2].data.length - 1] = point.p_load_kw ?? null;
        powerChart.data.datasets[3].data[powerChart.data.datasets[3].data.length - 1] = point.p_grid_kw ?? null;
    } else {
        telemetryHistory.push(point);
        socChart.data.labels.push(label);
        socChart.data.datasets[0].data.push(point.soc ?? null);
        powerChart.data.labels.push(label);
        powerChart.data.datasets[0].data.push(point.p_bess_kw ?? null);
        powerChart.data.datasets[1].data.push(point.p_pv_kw ?? null);
        powerChart.data.datasets[2].data.push(point.p_load_kw ?? null);
        powerChart.data.datasets[3].data.push(point.p_grid_kw ?? null);
        
        if (telemetryHistory.length > maxPoints) {
            telemetryHistory.shift();
            socChart.data.labels.shift();
            socChart.data.datasets[0].data.shift();
            powerChart.data.labels.shift();
            powerChart.data.datasets.forEach(ds => ds.data.shift());
        }
    }
    
    socChart.update('none');
    powerChart.update('none');
}

async function refreshLatestRaw() {
    try {
        const resp = await fetch('/api/monitoring/telemetry?minutes=5&limit=1');
        if (!resp.ok) return;
        const payload = await resp.json();
        const data = payload.data || [];
        if (!data.length) return;
        const latest = data[data.length - 1];
        
        mergeTelemetryPoint(latest);
        updateStatusSection(latest);
        lastRawFetch = Date.now();
    } catch (err) {
        console.error('Failed to refresh raw telemetry:', err);
    }
}

function updateKpis(state) {
    const socElem = document.getElementById('kpi-soc');
    const powerElem = document.getElementById('kpi-power');
    const voltageElem = document.getElementById('kpi-voltage');
    const tempElem = document.getElementById('kpi-temperature');
    const sourceElem = document.getElementById('kpi-source');
    const sohElem = document.getElementById('kpi-soh');
    const maxChargeElem = document.getElementById('kpi-max-charge');
    const maxDischargeElem = document.getElementById('kpi-max-discharge');
    const insulationElem = document.getElementById('kpi-insulation');
    
    if (socElem) socElem.textContent = `${formatNumber(state.soc)} %`;
    if (powerElem) powerElem.textContent = `${formatSigned(state.p_bess)} kW`;
    if (voltageElem) voltageElem.textContent = state.voltage_v != null ? `${formatNumber(state.voltage_v)} V` : '-- V';
    if (tempElem) tempElem.textContent = state.temp_c != null ? `${formatNumber(state.temp_c)} °C` : '-- °C';
    if (sourceElem) sourceElem.textContent = `Quelle: ${state.telemetry_source === 'mqtt' ? 'MQTT Telemetrie' : 'Simulation'}`;
    if (sohElem) sohElem.textContent = state.soh != null ? `${formatNumber(state.soh)} %` : '-- %';
    if (maxChargeElem) maxChargeElem.textContent = state.max_charge_power_kw != null ? `${formatNumber(state.max_charge_power_kw)} kW` : '-- kW';
    if (maxDischargeElem) maxDischargeElem.textContent = state.max_discharge_power_kw != null ? `${formatNumber(state.max_discharge_power_kw)} kW` : '-- kW';
    if (insulationElem) insulationElem.textContent = state.insulation_kohm != null ? `${formatNumber(state.insulation_kohm)} kOhm` : '-- kOhm';
}

function updateStatusSection(point) {
    const modeElem = document.getElementById('status-mode');
    const bitsElem = document.getElementById('status-bits');
    const updatedElem = document.getElementById('status-updated');
    const sourceElem = document.getElementById('status-source');
    const rawElem = document.getElementById('status-raw');
    const statusTextElem = document.getElementById('status-text');
    const statusCodeElem = document.getElementById('status-code');
    const alarmsElem = document.getElementById('status-alarms');
    
    const modeLabel = point.mode || '—';
    const bitsLabel = point.status_bits || '—';
    const updatedLabel = formatTimestamp(point.timestamp);
    const sourceLabel = point.telemetry_source === 'mqtt' ? 'MQTT' : 'Simulation';
    const statusText = point.status_text || '—';
    const statusCode = point.status_code != null ? String(point.status_code) : '--';
    
    if (modeElem && lastStatusSnapshot.mode !== modeLabel) {
        modeElem.textContent = modeLabel;
        lastStatusSnapshot.mode = modeLabel;
    }
    if (bitsElem && lastStatusSnapshot.bits !== bitsLabel) {
        bitsElem.textContent = bitsLabel;
        lastStatusSnapshot.bits = bitsLabel;
    }
    if (updatedElem && lastStatusSnapshot.updated !== updatedLabel) {
        updatedElem.textContent = updatedLabel;
        lastStatusSnapshot.updated = updatedLabel;
    }
    if (sourceElem && lastStatusSnapshot.source !== sourceLabel) {
        sourceElem.textContent = sourceLabel;
        lastStatusSnapshot.source = sourceLabel;
    }
    if (statusTextElem && lastStatusSnapshot.text !== statusText) {
        statusTextElem.textContent = statusText;
        lastStatusSnapshot.text = statusText;
    }
    if (statusCodeElem && lastStatusSnapshot.code !== statusCode) {
        statusCodeElem.textContent = `Code: ${statusCode}`;
        lastStatusSnapshot.code = statusCode;
    }
    
    if (alarmsElem) {
        const alarms = Array.isArray(point.active_alarms) ? point.active_alarms.filter(Boolean) : [];
        alarmsElem.innerHTML = '';
        if (!alarms.length) {
            const li = document.createElement('li');
            li.style.color = '#6b7280';
            li.textContent = 'Keine aktiven Alarme';
            alarmsElem.appendChild(li);
        } else {
            alarms.forEach(alarm => {
                const li = document.createElement('li');
                li.textContent = alarm;
                alarmsElem.appendChild(li);
            });
        }
    }
    
    if (rawElem && point.raw) {
        const rawJson = JSON.stringify(point.raw, null, 2);
        if (rawJson !== lastRawJson) {
            rawElem.textContent = rawJson;
            lastRawJson = rawJson;
        }
    }
}

function formatTimestamp(ts) {
    if (!ts) return '--';
    const date = new Date(ts);
    if (Number.isNaN(date.getTime())) return '--';
    
    return date.toLocaleTimeString('de-DE', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatNumber(value, digits = 1) {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return '--';
    }
    return Number(value).toFixed(digits);
}

function formatSigned(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return '--';
    }
    const num = Number(value);
    const sign = num > 0 ? '+' : '';
    return `${sign}${num.toFixed(1)}`;
}

