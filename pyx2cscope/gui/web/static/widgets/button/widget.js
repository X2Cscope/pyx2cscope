/**
 * Button Widget - Push button with toggle mode support
 *
 * Features:
 * - Momentary or Toggle mode
 * - Configurable press/release values
 * - Color change on press (toggle mode)
 * - Supports touch and mouse events
 */

function handleDashboardButtonPress(id) {
    const widget = dashboardWidgets.find(w => w.id === id);
    if (!widget) return;

    if (widget.toggleMode) {
        // Toggle mode: switch state — needs full re-render for button color change
        widget.buttonState = !widget.buttonState;
        const value = widget.buttonState ? widget.pressValue : widget.releaseValue || 0;
        updateDashboardVariable(widget.variable, value);
        renderDashboardWidget(widget); // button color change requires re-render
    } else {
        // Momentary mode: send press value
        updateDashboardVariable(widget.variable, widget.pressValue);
    }
}

function handleDashboardButtonRelease(id) {
    const widget = dashboardWidgets.find(w => w.id === id);
    // Don't handle release for toggle mode or if release is not enabled
    if (!widget || widget.toggleMode || !widget.releaseWrite) return;

    // Momentary mode: send release value
    updateDashboardVariable(widget.variable, widget.releaseValue);
}

function createButtonWidget(widget) {
    const btnColor = widget.toggleMode && widget.buttonState
        ? widget.pressedColor
        : widget.buttonColor;

    return `
        <button class="btn btn-${btnColor} w-100"
                id="btn-${widget.id}"
                onmousedown="handleDashboardButtonPress(${widget.id})"
                onmouseup="handleDashboardButtonRelease(${widget.id})"
                ontouchstart="handleDashboardButtonPress(${widget.id})"
                ontouchend="handleDashboardButtonRelease(${widget.id})"
                ${isDashboardEditMode ? 'disabled' : ''}>
            ${widget.displayName || widget.variable}
        </button>
    `;
}

function getButtonConfig(editWidget) {
    return `
        <div class="mb-3">
            <label class="form-label">Display Name</label>
            <input type="text" class="form-control" id="widgetDisplayName" value="${editWidget?.displayName || ''}" placeholder="Enter display name (optional)">
        </div>
        <div class="mb-3">
            <label class="form-label">Button Color</label>
            <select class="form-select" id="widgetButtonColor">
                <option value="primary" ${editWidget?.buttonColor === 'primary' ? 'selected' : ''}>Primary (Blue)</option>
                <option value="secondary" ${editWidget?.buttonColor === 'secondary' ? 'selected' : ''}>Secondary (Gray)</option>
                <option value="success" ${editWidget?.buttonColor === 'success' ? 'selected' : ''}>Success (Green)</option>
                <option value="danger" ${editWidget?.buttonColor === 'danger' ? 'selected' : ''}>Danger (Red)</option>
                <option value="warning" ${editWidget?.buttonColor === 'warning' ? 'selected' : ''}>Warning (Yellow)</option>
                <option value="info" ${editWidget?.buttonColor === 'info' ? 'selected' : ''}>Info (Cyan)</option>
            </select>
        </div>
        <div class="mb-3">
            <label class="form-label">Value on Press</label>
            <input type="text" class="form-control" id="widgetPressValue" value="${editWidget?.pressValue !== undefined ? editWidget.pressValue : 1}" placeholder="e.g., 1 or true">
        </div>
        <div class="mb-3">
            <label class="form-label">Write Value on Release</label>
            <select class="form-select" id="widgetReleaseWrite">
                <option value="false" ${!editWidget?.releaseWrite ? 'selected' : ''}>No</option>
                <option value="true" ${editWidget?.releaseWrite ? 'selected' : ''}>Yes</option>
            </select>
        </div>
        <div class="mb-3" id="releaseValueContainer">
            <label class="form-label">Value on Release</label>
            <input type="text" class="form-control" id="widgetReleaseValue" value="${editWidget?.releaseValue !== undefined ? editWidget.releaseValue : 0}" placeholder="e.g., 0 or false">
        </div>
        <div class="mb-3">
            <label class="form-label">Toggle Button</label>
            <select class="form-select" id="widgetToggleMode">
                <option value="false" ${!editWidget?.toggleMode ? 'selected' : ''}>No (Momentary)</option>
                <option value="true" ${editWidget?.toggleMode ? 'selected' : ''}>Yes (Toggle On/Off)</option>
            </select>
        </div>
        <div class="mb-3" id="pressedColorContainer">
            <label class="form-label">Color When Pressed (Toggle)</label>
            <select class="form-select" id="widgetPressedColor">
                <option value="success" ${editWidget?.pressedColor === 'success' ? 'selected' : ''}>Success (Green)</option>
                <option value="danger" ${editWidget?.pressedColor === 'danger' ? 'selected' : ''}>Danger (Red)</option>
                <option value="warning" ${editWidget?.pressedColor === 'warning' ? 'selected' : ''}>Warning (Yellow)</option>
                <option value="info" ${editWidget?.pressedColor === 'info' ? 'selected' : ''}>Info (Cyan)</option>
                <option value="primary" ${editWidget?.pressedColor === 'primary' ? 'selected' : ''}>Primary (Blue)</option>
            </select>
        </div>
    `;
}

function saveButtonConfig(widget) {
    widget.displayName = document.getElementById('widgetDisplayName').value;
    widget.buttonColor = document.getElementById('widgetButtonColor').value;
    widget.pressValue = parseValue(document.getElementById('widgetPressValue').value);
    widget.toggleMode = document.getElementById('widgetToggleMode').value === 'true';
    widget.releaseWrite = document.getElementById('widgetReleaseWrite').value === 'true';
    widget.releaseValue = parseValue(document.getElementById('widgetReleaseValue').value);
    widget.buttonState = widget.buttonState || false; // Track toggle state
    if (widget.toggleMode) {
        widget.pressedColor = document.getElementById('widgetPressedColor').value;
    }
}

function refreshButtonWidget(widget, widgetEl) {
    // Button changes require full re-render for color changes
    // This is intentionally empty - button updates handled by full render
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.button = {
    icon: 'radio_button_checked',
    create: createButtonWidget,
    getConfig: getButtonConfig,
    saveConfig: saveButtonConfig,
    refresh: refreshButtonWidget,
    requiresVariable: true,
    supportsGainOffset: false
};
