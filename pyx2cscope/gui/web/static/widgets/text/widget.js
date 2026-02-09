/**
 * Text Widget - Text input field
 * 
 * Features:
 * - String/text entry
 * - Supports gain/offset transformation
 */

function createTextWidget(widget) {
    return `
        <input type="text" class="form-control"
               value="${widget.value}"
               onchange="updateDashboardVariable('${widget.variable}', this.value)"
               ${isDashboardEditMode ? 'disabled' : ''}>
    `;
}

function getTextConfig(editWidget) {
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

function saveTextConfig(widget) {
    widget.gain = parseFloat(document.getElementById('widgetGain').value) || 1;
    widget.offset = parseFloat(document.getElementById('widgetOffset').value) || 0;
}

function refreshTextWidget(widget, widgetEl) {
    const input = widgetEl.querySelector('input[type="text"]');
    if (input && document.activeElement !== input) input.value = widget.value;
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.text = {
    icon: 'text_fields',
    create: createTextWidget,
    getConfig: getTextConfig,
    saveConfig: saveTextConfig,
    refresh: refreshTextWidget,
    requiresVariable: true,
    supportsGainOffset: true
};
