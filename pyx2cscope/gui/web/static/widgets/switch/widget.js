/**
 * Switch Widget - Toggle switch control
 *
 * Features:
 * - On/Off toggle switch (iOS-style)
 * - Configurable on/off values
 * - Display name label
 * - Visual state indication
 */

function handleSwitchToggle(id) {
    const widget = dashboardWidgets.find(w => w.id === id);
    if (!widget) return;

    widget.switchState = !widget.switchState;
    const value = widget.switchState ? widget.onValue : widget.offValue;
    updateDashboardVariable(widget.variable, value);
    renderDashboardWidget(widget);
}

function createSwitchWidget(widget) {
    const isOn = widget.switchState || false;

    return `
        <div class="form-check form-switch m-0 d-flex justify-content-center">
            <input class="form-check-input" type="checkbox" role="switch"
                   id="switch-${widget.id}"
                   ${isOn ? 'checked' : ''}
                   onchange="handleSwitchToggle(${widget.id})"
                   style="width: 3em; height: 1.5em; cursor: pointer;"
                   ${isDashboardEditMode ? 'disabled' : ''}>
        </div>
    `;
}

function getSwitchConfig(editWidget) {
    return `
        <div class="mb-3">
            <label class="form-label">Display Name</label>
            <input type="text" class="form-control" id="widgetDisplayName" value="${editWidget?.displayName || ''}" placeholder="Enter display name (optional)">
        </div>
        <div class="mb-3">
            <label class="form-label">Value when ON</label>
            <input type="text" class="form-control" id="widgetOnValue" value="${editWidget?.onValue !== undefined ? editWidget.onValue : 1}" placeholder="e.g., 1 or true">
        </div>
        <div class="mb-3">
            <label class="form-label">Value when OFF</label>
            <input type="text" class="form-control" id="widgetOffValue" value="${editWidget?.offValue !== undefined ? editWidget.offValue : 0}" placeholder="e.g., 0 or false">
        </div>
    `;
}

function saveSwitchConfig(widget) {
    widget.displayName = document.getElementById('widgetDisplayName').value;
    widget.onValue = parseValue(document.getElementById('widgetOnValue').value);
    widget.offValue = parseValue(document.getElementById('widgetOffValue').value);
    widget.switchState = widget.switchState || false;
}

function refreshSwitchWidget(widget, widgetEl) {
    const checkbox = widgetEl.querySelector('input[type="checkbox"]');
    if (checkbox) {
        checkbox.checked = widget.switchState || false;
    }
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.switch = {
    icon: 'toggle_on',
    create: createSwitchWidget,
    getConfig: getSwitchConfig,
    saveConfig: saveSwitchConfig,
    refresh: refreshSwitchWidget,
    requiresVariable: true,
    supportsGainOffset: false
};
