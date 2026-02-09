/**
 * Label Widget - Static text display
 * 
 * Features:
 * - Customizable text
 * - Font size selection (small/medium/large/xlarge)
 * - Text alignment (left/center/right)
 */

function createLabelWidget(widget) {
    const fontSizes = { small: '0.875rem', medium: '1rem', large: '1.5rem', xlarge: '2rem' };
    const fontSize = fontSizes[widget.fontSize] || fontSizes.medium;
    return `
        <div style="font-size: ${fontSize}; text-align: ${widget.textAlign}; padding: 10px; font-weight: 500;">
            ${widget.labelText}
        </div>
    `;
}

function getLabelConfig(editWidget) {
    return `
        <div class="mb-3">
            <label class="form-label">Label Text</label>
            <input type="text" class="form-control" id="widgetLabelText" value="${editWidget?.labelText || ''}" placeholder="Enter text to display">
        </div>
        <div class="mb-3">
            <label class="form-label">Font Size</label>
            <select class="form-select" id="widgetFontSize">
                <option value="small" ${editWidget?.fontSize === 'small' ? 'selected' : ''}>Small</option>
                <option value="medium" ${!editWidget?.fontSize || editWidget?.fontSize === 'medium' ? 'selected' : ''}>Medium</option>
                <option value="large" ${editWidget?.fontSize === 'large' ? 'selected' : ''}>Large</option>
                <option value="xlarge" ${editWidget?.fontSize === 'xlarge' ? 'selected' : ''}>Extra Large</option>
            </select>
        </div>
        <div class="mb-3">
            <label class="form-label">Text Alignment</label>
            <select class="form-select" id="widgetTextAlign">
                <option value="left" ${editWidget?.textAlign === 'left' ? 'selected' : ''}>Left</option>
                <option value="center" ${!editWidget?.textAlign || editWidget?.textAlign === 'center' ? 'selected' : ''}>Center</option>
                <option value="right" ${editWidget?.textAlign === 'right' ? 'selected' : ''}>Right</option>
            </select>
        </div>
    `;
}

function saveLabelConfig(widget) {
    widget.labelText = document.getElementById('widgetLabelText').value;
    widget.fontSize = document.getElementById('widgetFontSize').value;
    widget.textAlign = document.getElementById('widgetTextAlign').value;
    widget.variable = 'label_' + widget.id; // Generate unique variable name
}

function refreshLabelWidget(widget, widgetEl) {
    // Labels are static, no refresh needed
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.label = {
    icon: 'label',
    create: createLabelWidget,
    getConfig: getLabelConfig,
    saveConfig: saveLabelConfig,
    refresh: refreshLabelWidget,
    requiresVariable: false,
    supportsGainOffset: false
};
