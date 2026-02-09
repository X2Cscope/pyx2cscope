/**
 * Number Widget - Numeric input field
 * 
 * Features:
 * - Direct number entry
 * - Supports gain/offset transformation
 */

function createNumberWidget(widget) {
    return `
        <input type="number" class="form-control"
               value="${widget.value}"
               onchange="updateDashboardVariable('${widget.variable}', parseFloat(this.value))"
               ${isDashboardEditMode ? 'disabled' : ''}>
    `;
}

function getNumberConfig(editWidget) {
    return `
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

function saveNumberConfig(widget) {
    widget.gain = parseFloat(document.getElementById('widgetGain').value) || 1;
    widget.offset = parseFloat(document.getElementById('widgetOffset').value) || 0;
}

function refreshNumberWidget(widget, widgetEl) {
    const input = widgetEl.querySelector('input[type="number"]');
    if (input && document.activeElement !== input) input.value = widget.value;
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.number = {
    icon: 'pin',
    create: createNumberWidget,
    getConfig: getNumberConfig,
    saveConfig: saveNumberConfig,
    refresh: refreshNumberWidget,
    requiresVariable: true,
    supportsGainOffset: true
};
