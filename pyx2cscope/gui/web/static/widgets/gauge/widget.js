/**
 * Gauge Widget - Semi-circular gauge display using Chart.js
 *
 * Features:
 * - Semi-circular doughnut chart visualization
 * - Configurable color zones (low/mid/high)
 * - Custom threshold values
 * - Percent or number display mode
 * - Supports gain/offset transformation
 */

// Get gauge color based on value and configurable thresholds
function getGaugeColor(value, widget) {
    const range = widget.max - widget.min;
    const low = widget.lowThreshold !== undefined ? widget.lowThreshold : widget.min + range * 0.6;
    const high = widget.highThreshold !== undefined ? widget.highThreshold : widget.min + range * 0.8;
    if (value >= high) return widget.highColor;
    if (value >= low) return widget.midColor;
    return widget.lowColor;
}

// Get gauge display text based on display mode
function getGaugeDisplayText(value, percent, widget) {
    if (widget.displayMode === 'number') {
        return Number.isInteger(value) ? value.toString() : value.toFixed(2);
    }
    return (percent * 100).toFixed(1) + '%';
}

// Chart.js gauge via doughnut chart with overlay labels
function renderDashboardGauge(widget, gaugeCanvas) {
    if (dashboardCharts[widget.id]) {
        dashboardCharts[widget.id].destroy();
    }

    let value = widget.value;
    let percent = ((value - widget.min) / (widget.max - widget.min));
    percent = Math.max(0, Math.min(1, percent));

    const color = getGaugeColor(value, widget);

    const config = {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [percent, 1 - percent],
                backgroundColor: [color, '#e9ecef'],
                borderWidth: 0
            }]
        },
        options: {
            aspectRatio: 2,
            circumference: 180,
            rotation: -90,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    };

    dashboardCharts[widget.id] = new Chart(gaugeCanvas, config);

    // Position the overlay labels
    setTimeout(() => {
        const overlay = document.getElementById(`gauge-label-${widget.id}`);
        const canvas = gaugeCanvas;
        if (overlay && canvas) {
            const rect = canvas.getBoundingClientRect();
            const centerX = rect.width / 2;
            const centerY = rect.height / 2 + rect.height / 3;
            overlay.style.position = 'absolute';
            overlay.style.left = centerX + 'px';
            overlay.style.top = centerY + 'px';
            overlay.style.transform = 'translate(-50%, -50%)';
            overlay.style.textAlign = 'center';
            overlay.style.pointerEvents = 'none';
        }
    }, 50);
}

function createGaugeWidget(widget) {
    return `
        <div style="position: relative;">
            <canvas class="gauge-container" id="dashboard-gauge-${widget.id}"></canvas>
            <div class="gauge-label-overlay" id="gauge-label-${widget.id}">
                <div class="gauge-value" style="font-size: 30px; font-weight: bold; color: #000;">${widget.value}</div>
                <div class="gauge-variable" style="font-size: 14px; color: #000;">${widget.displayName || widget.variable || 'Value'}</div>
            </div>
        </div>
    `;
}

function getGaugeConfig(editWidget) {
    return `
        <div class="mb-3">
            <label class="form-label">Display Name</label>
            <input type="text" class="form-control" id="widgetDisplayName" value="${editWidget?.displayName || ''}" placeholder="Enter display name (optional)">
        </div>
        <div class="mb-3">
            <label class="form-label">Min Value</label>
            <div class="d-flex gap-2">
                <input type="number" class="form-control" id="widgetMinValue" value="${editWidget?.min || 0}">
                <input type="color" class="form-control form-control-color" id="widgetLowColor"
                           value="${editWidget?.lowColor || '#198754'}"
                           title="Choose low threshold color">
            </div>
        </div>
        <div class="mb-3">
            <label class="form-label">Max Value</label>
            <input type="number" class="form-control" id="widgetMaxValue" value="${editWidget?.max || 100}">
        </div>
        <div class="mb-3">
            <label class="form-label">Low Threshold</label>
            <div class="d-flex gap-2">
                <input type="number" class="form-control" id="widgetLowThreshold"
                       value="${editWidget?.lowThreshold !== undefined ? editWidget.lowThreshold : ''}"
                       placeholder="Default: 60% of range">
                <input type="color" class="form-control form-control-color" id="widgetMidColor"
                       value="${editWidget?.midColor || '#ffc107'}"
                       title="Choose mid threshold color">
            </div>
        </div>
        <div class="mb-3">
            <label class="form-label">High Threshold</label>
            <div class="d-flex gap-2">
                <input type="number" class="form-control" id="widgetHighThreshold"
                       value="${editWidget?.highThreshold !== undefined ? editWidget.highThreshold : ''}"
                       placeholder="Default: 80% of range">
                <input type="color" class="form-control form-control-color" id="widgetHighColor"
                           value="${editWidget?.highColor || '#dc3545'}"
                           title="Choose high threshold color">
            </div>
        </div>
        <div class="mb-3">
            <label class="form-label">Display Mode</label>
            <select class="form-select" id="widgetDisplayMode">
                <option value="percent" ${!editWidget?.displayMode || editWidget?.displayMode === 'percent' ? 'selected' : ''}>Percent</option>
                <option value="number" ${editWidget?.displayMode === 'number' ? 'selected' : ''}>Number</option>
            </select>
        </div>
        <div class="mb-3">
            <label class="form-label">Gain</label>
            <input type="number" class="form-control" id="widgetGain" step="any"
                   value="${editWidget?.gain !== undefined ? editWidget.gain : 1}" placeholder="1">
        </div>
        <div class="mb-3">
            <label class="form-label">Offset</label>
            <input type="number" class="form-control" id="widgetOffset" step="any"
                   value="${editWidget?.offset !== undefined ? editWidget.offset : 0}" placeholder="0">
        </div>
    `;
}

function saveGaugeConfig(widget) {
    widget.displayName = document.getElementById('widgetDisplayName').value;
    widget.min = parseFloat(document.getElementById('widgetMinValue').value);
    widget.max = parseFloat(document.getElementById('widgetMaxValue').value);
    const lowVal = document.getElementById('widgetLowThreshold').value;
    const highVal = document.getElementById('widgetHighThreshold').value;
    widget.lowThreshold = lowVal !== '' ? parseFloat(lowVal) : undefined;
    widget.lowColor = document.getElementById('widgetLowColor').value;
    widget.midColor = document.getElementById('widgetMidColor').value;
    widget.highColor = document.getElementById('widgetHighColor').value;
    widget.highThreshold = highVal !== '' ? parseFloat(highVal) : undefined;
    widget.displayMode = document.getElementById('widgetDisplayMode').value;
    widget.gain = parseFloat(document.getElementById('widgetGain').value) || 1;
    widget.offset = parseFloat(document.getElementById('widgetOffset').value) || 0;
}

function afterRenderGaugeWidget(widget) {
    setTimeout(() => {
        const gaugeCanvas = document.getElementById(`dashboard-gauge-${widget.id}`);
        if (gaugeCanvas && typeof Chart !== 'undefined') {
            renderDashboardGauge(widget, gaugeCanvas);
        }
    }, 100);
}

function refreshGaugeWidget(widget, widgetEl) {
    const chart = dashboardCharts[widget.id];
    if (!chart) { 
        afterRenderGaugeWidget(widget);
        return; 
    }
    const percent = Math.max(0, Math.min(1, (widget.value - widget.min) / (widget.max - widget.min)));
    const color = getGaugeColor(widget.value, widget);
    const displayText = getGaugeDisplayText(widget.value, percent, widget);
    chart.data.datasets[0].data = [percent, 1 - percent];
    chart.data.datasets[0].backgroundColor = [color, '#e9ecef'];
    chart.update('none');
    
    // Update overlay labels
    const overlay = document.getElementById(`gauge-label-${widget.id}`);
    if (overlay) {
        const valueEl = overlay.querySelector('.gauge-value');
        const varEl = overlay.querySelector('.gauge-variable');
        if (valueEl) valueEl.textContent = displayText;
        if (varEl) varEl.textContent = widget.displayName || widget.variable || 'Value';
    }
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.gauge = {
    icon: 'speed',
    create: createGaugeWidget,
    getConfig: getGaugeConfig,
    saveConfig: saveGaugeConfig,
    afterRender: afterRenderGaugeWidget,
    refresh: refreshGaugeWidget,
    requiresVariable: true,
    supportsGainOffset: true
};
