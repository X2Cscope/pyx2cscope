/**
 * Slider Widget - Range slider control
 * 
 * Features:
 * - Configurable min/max/step values
 * - Real-time value display
 * - Supports gain/offset transformation
 */

function createSliderWidget(widget) {
    return `
        <div class="value-display">${widget.value}</div>
        <input type="range" class="form-range"
               min="${widget.min}"
               max="${widget.max}"
               step="${widget.step}"
               value="${widget.value}"
               onchange="updateDashboardVariable('${widget.variable}', parseFloat(this.value))"
               ${isDashboardEditMode ? 'disabled' : ''}>
    `;
}

function getSliderConfig(editWidget) {
    return `
        <div class="mb-3">
            <label class="form-label">Min Value</label>
            <input type="number" class="form-control" id="widgetMinValue" value="${editWidget?.min || 0}">
        </div>
        <div class="mb-3">
            <label class="form-label">Max Value</label>
            <input type="number" class="form-control" id="widgetMaxValue" value="${editWidget?.max || 100}">
        </div>
        <div class="mb-3">
            <label class="form-label">Step</label>
            <input type="number" class="form-control" id="widgetStepValue" value="${editWidget?.step || 1}">
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

function saveSliderConfig(widget) {
    widget.min = parseFloat(document.getElementById('widgetMinValue').value);
    widget.max = parseFloat(document.getElementById('widgetMaxValue').value);
    widget.step = parseFloat(document.getElementById('widgetStepValue').value);
    widget.gain = parseFloat(document.getElementById('widgetGain').value) || 1;
    widget.offset = parseFloat(document.getElementById('widgetOffset').value) || 0;
}

function refreshSliderWidget(widget, widgetEl) {
    const display = widgetEl.querySelector('.value-display');
    const input = widgetEl.querySelector('input[type="range"]');
    if (display) display.textContent = widget.value;
    if (input) input.value = widget.value;
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.slider = {
    icon: 'tune',
    create: createSliderWidget,
    getConfig: getSliderConfig,
    saveConfig: saveSliderConfig,
    refresh: refreshSliderWidget,
    requiresVariable: true,
    supportsGainOffset: true
};
