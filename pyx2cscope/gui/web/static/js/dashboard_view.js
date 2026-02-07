// Dashboard View JavaScript
// This file handles all dashboard widget functionality

let dashboardWidgets = [];
let selectedWidget = null;
let isDashboardEditMode = false;
let draggedWidget = null;
let dragOffsetX = 0;
let dragOffsetY = 0;
let currentWidgetType = '';
let widgetIdCounter = 0;
let dashboardSocket = null;

// Track chart.js instances per-widget
let dashboardCharts = {};

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Initialize Socket.IO if available
    if (typeof io !== 'undefined') {
        dashboardSocket = io('/dashboard');

        dashboardSocket.on('connect', () => {
            console.log('Dashboard connected to server');
            registerAllDashboardVariables();
        });

        dashboardSocket.on('dashboard_data_update', (data) => {
            // data is {var1: value1, var2: value2, ...} — for watch-like widgets only
            for (let varName in data) {
                updateDashboardWatchWidgets(varName, data[varName]);
            }
        });

        dashboardSocket.on('dashboard_scope_update', (data) => {
            // data is {var1: [...], var2: [...]} — for plot_scope widgets only
            for (let varName in data) {
                updateDashboardScopeWidgets(varName, data[varName]);
            }
        });
    }

    // Set up file input for import
    document.getElementById('dashboardFileInput').addEventListener('change', handleDashboardFileImport);
}

function registerAllDashboardVariables() {
    dashboardWidgets.forEach(widget => registerWidgetVariables(widget));
}

function removeAllDashboardVariables() {
    dashboardWidgets.forEach(widget => unregisterWidgetVariables(widget));
}

function registerWidgetVariables(widget) {
    if (!dashboardSocket || !dashboardSocket.connected) return;

    if (widget.type === 'plot_scope') {
        // Register as shared scope channels so data flows when scope is triggered
        widget.variables?.forEach(varName => {
            dashboardSocket.emit('register_scope_channel', {var: varName});
        });
    } else if (widget.type === 'plot_logger') {
        widget.variables?.forEach(varName => {
            dashboardSocket.emit('add_dashboard_var', {var: varName});
        });
    } else if (widget.type !== 'label') {
        dashboardSocket.emit('add_dashboard_var', {var: widget.variable});
    }
}

function isVarUsedByOtherWidgets(widget, varName) {
    return dashboardWidgets.some(w => {
        if (w.id === widget.id) return false;
        if (w.type === 'plot_logger' || w.type === 'plot_scope') {
            return w.variables && w.variables.includes(varName);
        }
        return w.variable === varName;
    });
}

function unregisterWidgetVariables(widget) {
    if (!dashboardSocket || !dashboardSocket.connected) return;

    if (widget.type === 'plot_scope') {
        widget.variables?.forEach(varName => {
            if (!isVarUsedByOtherWidgets(widget, varName)) {
                dashboardSocket.emit('unregister_scope_channel', {var: varName});
            }
        });
    } else if (widget.type === 'plot_logger') {
        widget.variables?.forEach(varName => {
            if (!isVarUsedByOtherWidgets(widget, varName)) {
                dashboardSocket.emit('remove_dashboard_var', {var: varName});
            }
        });
    } else if (widget.type !== 'label') {
        if (!isVarUsedByOtherWidgets(widget, widget.variable)) {
            dashboardSocket.emit('remove_dashboard_var', {var: widget.variable});
        }
    }
}

function toggleDashboardMode() {
    isDashboardEditMode = !isDashboardEditMode;
    const btn = document.getElementById('dashboardModeBtn');
    const icon = btn.querySelector('.material-icons');
    const palette = document.getElementById('widgetPalette');
    const canvasCol = document.getElementById('dashboardCanvasCol');
    const canvas = document.getElementById('dashboardCanvas');

    if (isDashboardEditMode) {
        icon.textContent = 'edit';
        icon.classList.remove('text-secondary');
        icon.classList.add('text-success');
        btn.title = 'Edit Mode (Active)';
        palette.style.display = 'block';
        canvasCol.classList.remove('col-12');
        canvasCol.classList.add('col-12', 'col-md-9', 'col-lg-10');
        canvas.classList.remove('view-mode');
        canvas.classList.add('edit-mode');
    } else {
        icon.textContent = 'visibility';
        icon.classList.remove('text-success');
        icon.classList.add('text-secondary');
        btn.title = 'View Mode';
        palette.style.display = 'none';
        canvasCol.classList.remove('col-md-9', 'col-lg-10');
        canvasCol.classList.add('col-12');
        canvas.classList.remove('edit-mode');
        canvas.classList.add('view-mode');
    }

    // Update all widgets
    dashboardWidgets.forEach(w => renderDashboardWidget(w));
}

function initWidgetVarSelect2(options = {}) {
    const defaults = {
        placeholder: "Select a variable",
        allowClear: true,
        dropdownParent: $('#widgetConfigModal'),
        ajax: {
            url: '/variables',
            dataType: 'json',
            delay: 250,
            processResults: function (data) {
                return { results: data.items };
            },
            cache: true
        },
        minimumInputLength: 3
    };
    return $.extend(true, {}, defaults, options);
}

function showWidgetConfig(type, editWidget = null) {
    currentWidgetType = type;
    const extraConfig = document.getElementById('widgetExtraConfig');
    const varNameContainer = document.getElementById('widgetVarNameContainer');
    const modalTitle = document.querySelector('#widgetConfigModal .modal-title');
    const isPlotType = (type === 'plot_logger' || type === 'plot_scope');

    extraConfig.innerHTML = '';
    modalTitle.textContent = editWidget ? 'Edit Widget Configuration' : 'Configure Widget';

    // Destroy previous Select2 instances
    if ($('#widgetVarName').data('select2')) {
        $('#widgetVarName').select2('destroy');
    }

    // Show/hide the single variable selector based on widget type
    if (isPlotType || type === 'label') {
        varNameContainer.style.display = 'none';
    } else {
        varNameContainer.style.display = '';
        // Reset and populate for edit mode
        $('#widgetVarName').empty();
        if (editWidget) {
            $('#widgetVarName').append(new Option(editWidget.variable, editWidget.variable, true, true));
        }
    }

    // Gain/offset fields for value-based widgets
    const gainOffsetHtml = `
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

    // Add type-specific configuration
    if (type === 'slider') {
        extraConfig.innerHTML = `
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
            ${gainOffsetHtml}
        `;
    } else if (type === 'button') {
        extraConfig.innerHTML = `
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

    } else if (type === 'gauge') {
        extraConfig.innerHTML = `
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
            ${gainOffsetHtml}
        `;
    } else if (type === 'number' || type === 'text') {
        extraConfig.innerHTML = gainOffsetHtml;
    } else if (isPlotType) {
        const isLogger = type === 'plot_logger';
        extraConfig.innerHTML = `
            <div class="mb-3">
                <label class="form-label">Variables</label>
                <select class="form-control" id="widgetVariables" multiple="multiple" style="width: 100%;"></select>
                <small class="form-text text-muted">Search and select one or more variables</small>
            </div>
            ${isLogger ? `
            <div class="mb-3">
                <label class="form-label">Max Data Points</label>
                <input type="number" class="form-control" id="widgetMaxPoints" value="${editWidget?.maxPoints || 50}">
            </div>
            ` : ''}
        `;
    } else if (type === 'label') {
        extraConfig.innerHTML = `
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

    const modal = new bootstrap.Modal(document.getElementById('widgetConfigModal'));
    modal.show();

    // Initialize Select2 after modal is shown so dropdown renders correctly
    $('#widgetConfigModal').one('shown.bs.modal', function() {
        if (!isPlotType && type !== 'label') {
            $('#widgetVarName').select2(initWidgetVarSelect2());
            if (editWidget) {
                $('#widgetVarName').prop('disabled', true);
            }
        }
        if (isPlotType) {
            $('#widgetVariables').select2(initWidgetVarSelect2({
                placeholder: "Search and select variables",
                multiple: true
            }));
            // Pre-populate existing variables when editing
            if (editWidget?.variables) {
                editWidget.variables.forEach(v => {
                    $('#widgetVariables').append(new Option(v, v, true, true));
                });
                $('#widgetVariables').trigger('change');
            }
        }
    });

    // Store reference to widget being edited
    window.editingWidget = editWidget;
}

function addDashboardWidget() {
    const editWidget = window.editingWidget;

    let widget;
    if (editWidget) {
        // Editing existing widget
        widget = editWidget;
    } else {
        // Creating new widget
        const isPlotType = (currentWidgetType === 'plot_logger' || currentWidgetType === 'plot_scope');
        const varName = isPlotType ? '' : ($('#widgetVarName').val() || '');
        if (!varName && currentWidgetType !== 'label' && !isPlotType) {
            alert('Please select a variable name');
            return;
        }

        widget = {
            id: widgetIdCounter++,
            type: currentWidgetType,
            variable: varName,
            x: 50,
            y: 50,
            value: currentWidgetType === 'text' ? '' : 0
        };
    }

    // Update type-specific properties
    if (currentWidgetType === 'slider') {
        widget.min = parseFloat(document.getElementById('widgetMinValue').value);
        widget.max = parseFloat(document.getElementById('widgetMaxValue').value);
        widget.step = parseFloat(document.getElementById('widgetStepValue').value);
    } else if (currentWidgetType === 'button') {
        widget.buttonColor = document.getElementById('widgetButtonColor').value;
        widget.pressValue = parseValue(document.getElementById('widgetPressValue').value);
        widget.toggleMode = document.getElementById('widgetToggleMode').value === 'true';
        widget.releaseWrite = document.getElementById('widgetReleaseWrite').value === 'true';
        widget.releaseValue = parseValue(document.getElementById('widgetReleaseValue').value);
        widget.buttonState = false; // Track toggle state
        if (widget.toggleMode) {
            widget.pressedColor = document.getElementById('widgetPressedColor').value;
        }
    } else if (currentWidgetType === 'gauge') {
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
    } else if (currentWidgetType === 'plot_logger' || currentWidgetType === 'plot_scope') {
        widget.variables = $('#widgetVariables').val() || [];
        if (widget.variables.length === 0) {
            alert('Please enter at least one variable name');
            return;
        }
        widget.data = {}; // Object to store data for each variable
        widget.variables.forEach(v => widget.data[v] = []);

        if (currentWidgetType === 'plot_logger') {
            widget.maxPoints = parseInt(document.getElementById('widgetMaxPoints').value);
        }
    } else if (currentWidgetType === 'label') {
        widget.labelText = document.getElementById('widgetLabelText').value;
        widget.fontSize = document.getElementById('widgetFontSize').value;
        widget.textAlign = document.getElementById('widgetTextAlign').value;
        widget.variable = 'label_' + widget.id; // Generate unique variable name
    }

    // Read gain/offset for types that show the fields
    const gainOffsetTypes = ['slider', 'number', 'text', 'gauge'];
    if (gainOffsetTypes.includes(currentWidgetType)) {
        const gainEl = document.getElementById('widgetGain');
        const offsetEl = document.getElementById('widgetOffset');
        widget.gain = gainEl ? parseFloat(gainEl.value) || 1 : 1;
        widget.offset = offsetEl ? parseFloat(offsetEl.value) || 0 : 0;
    }

    if (!editWidget) {
        dashboardWidgets.push(widget);
        registerWidgetVariables(widget);
    }

    renderDashboardWidget(widget);

    // Close modal and clean up Select2
    const modal = bootstrap.Modal.getInstance(document.getElementById('widgetConfigModal'));
    modal.hide();
    if ($('#widgetVarName').data('select2')) {
        $('#widgetVarName').val(null).trigger('change');
    }
    if ($('#widgetVariables').data('select2')) {
        $('#widgetVariables').val(null).trigger('change');
    }
    window.editingWidget = null;
}

// Helper function to parse values that might be numbers, booleans, or strings
function parseValue(val) {
    if (val === 'true') return true;
    if (val === 'false') return false;
    const num = parseFloat(val);
    if (!isNaN(num)) return num;
    return val;
}

// This is the major override for rendering widgets and using Chart.js for gauge/plot
function renderDashboardWidget(widget) {
    let widgetEl = document.getElementById(`dashboard-widget-${widget.id}`);

    if (!widgetEl) {
        widgetEl = document.createElement('div');
        widgetEl.id = `dashboard-widget-${widget.id}`;
        widgetEl.className = 'dashboard-widget';
        widgetEl.style.left = widget.x + 'px';
        widgetEl.style.top = widget.y + 'px';

        // Set saved dimensions if available
        if (widget.width) widgetEl.style.width = widget.width + 'px';
        if (widget.height) widgetEl.style.height = widget.height + 'px';

        widgetEl.addEventListener('mousedown', startDashboardDrag);

        // Save dimensions on resize
        const resizeObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                const id = parseInt(entry.target.id.replace('dashboard-widget-', ''));
                const w = dashboardWidgets.find(w => w.id === id);
                if (w) {
                    w.width = entry.contentRect.width + 24;
                    w.height = entry.contentRect.height + 24;
                }
            }
        });
        resizeObserver.observe(widgetEl);

        document.getElementById('dashboardCanvas').appendChild(widgetEl);
    }

    // Update widget classes based on mode
    if (isDashboardEditMode) {
        widgetEl.classList.add('edit-mode');
        widgetEl.classList.remove('view-mode');
    } else {
        widgetEl.classList.remove('edit-mode');
        widgetEl.classList.add('view-mode');
    }

    let content = '';
    const typeIcons = {
        slider: '<span class="material-icons md-18">tune</span>',
        button: '<span class="material-icons md-18">radio_button_checked</span>',
        number: '<span class="material-icons md-18">pin</span>',
        text: '<span class="material-icons md-18">text_fields</span>',
        label: '<span class="material-icons md-18">label</span>',
        gauge: '<span class="material-icons md-18">speed</span>',
        plot_logger: '<span class="material-icons md-18">timeline</span>',
        plot_scope: '<span class="material-icons md-18">show_chart</span>'
    };

    const displayName = widget.type === 'plot_logger' || widget.type === 'plot_scope'
        ? widget.variables?.join(', ') || widget.variable
        : widget.variable;

    const header = `
        <div class="widget-header">
            <span class="widget-title">${typeIcons[widget.type]} ${displayName}</span>
            <div class="widget-controls">
                <button class="btn btn-sm" onclick="showWidgetConfig('${widget.type}', dashboardWidgets.find(w => w.id === ${widget.id}))" title="Edit">
                    <span class="material-icons text-primary">settings</span>
                </button>
                <button class="btn btn-sm" onclick="deleteDashboardWidget(${widget.id})" title="Delete">
                    <span class="material-icons text-danger">delete</span>
                </button>
            </div>
        </div>
        <div class="widget-content">
    `;

    switch (widget.type) {
        case 'slider':
            content = `
                ${header}
                <div class="value-display">${widget.value}</div>
                <input type="range" class="form-range"
                       min="${widget.min}"
                       max="${widget.max}"
                       step="${widget.step}"
                       value="${widget.value}"
                       onchange="updateDashboardVariable('${widget.variable}', parseFloat(this.value))">
                </div>
            `;
            break;

        case 'button':
            const btnColor = widget.toggleMode && widget.buttonState
                ? widget.pressedColor
                : widget.buttonColor;
            content = `
                ${header}
                <button class="btn btn-${btnColor} w-100"
                        id="btn-${widget.id}"
                        onmousedown="handleDashboardButtonPress(${widget.id})"
                        onmouseup="handleDashboardButtonRelease(${widget.id})"
                        ontouchstart="handleDashboardButtonPress(${widget.id})"
                        ontouchend="handleDashboardButtonRelease(${widget.id})">
                    ${widget.variable}
                </button>
                </div>
            `;
            break;

        case 'number':
            content = `
                ${header}
                <input type="number" class="form-control"
                       value="${widget.value}"
                       onchange="updateDashboardVariable('${widget.variable}', parseFloat(this.value))">
                </div>
            `;
            break;

        case 'text':
            content = `
                ${header}
                <input type="text" class="form-control"
                       value="${widget.value}"
                       onchange="updateDashboardVariable('${widget.variable}', this.value)">
                </div>
            `;
            break;

        case 'label':
            const fontSizes = { small: '0.875rem', medium: '1rem', large: '1.5rem', xlarge: '2rem' };
            const fontSize = fontSizes[widget.fontSize] || fontSizes.medium;
            content = `
                ${header}
                <div style="font-size: ${fontSize}; text-align: ${widget.textAlign}; padding: 10px; font-weight: 500;">
                    ${widget.labelText}
                </div>
                </div>
            `;
            break;

        // Use Chart.js for gauge
        case 'gauge':
            content = `
                ${header}
                <div style="position: relative;">
                    <canvas class="gauge-container" id="dashboard-gauge-${widget.id}"></canvas>
                    <div class="gauge-label-overlay" id="gauge-label-${widget.id}">
                        <div class="gauge-value" style="font-size: 30px; font-weight: bold; color: #000;">${widget.value}</div>
                        <div class="gauge-variable" style="font-size: 14px; color: #000;">${widget.displayName || widget.variable || 'Value'}</div>
                    </div>
                </div>
                </div>
            `;
            setTimeout(() => {
                const gaugeCanvas = document.getElementById(`dashboard-gauge-${widget.id}`);
                if (gaugeCanvas && typeof Chart !== 'undefined') {
                    renderDashboardGauge(widget, gaugeCanvas);
                }
            }, 100);
            break;

        // Use Chart.js for plots
        case 'plot_logger':
        case 'plot_scope':
            content = `
                ${header}
                <canvas class="plot-container" id="dashboard-plot-${widget.id}"></canvas>
                </div>
            `;
            setTimeout(() => {
                const plotCanvas = document.getElementById(`dashboard-plot-${widget.id}`);
                if (plotCanvas && typeof Chart !== 'undefined') {
                    renderDashboardPlot(widget, plotCanvas);
                }
            }, 100);
            break;
    }

    widgetEl.innerHTML = content;
}

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
            const centerY = rect.height / 2 + rect.height / 3; // Adjust for semi-circle and move 10px down
            overlay.style.position = 'absolute';
            overlay.style.left = centerX + 'px';
            overlay.style.top = centerY + 'px';
            overlay.style.transform = 'translate(-50%, -50%)';
            overlay.style.textAlign = 'center';
            overlay.style.pointerEvents = 'none';
        }
    }, 50);
}

// Chart.js plot rendering (line)
function renderDashboardPlot(widget, plotCanvas) {
    // Code generated by MCHP Chatbot
    if (dashboardCharts[widget.id]) {
        dashboardCharts[widget.id].destroy();
    }
    // Build datasets for each variable
    const colors = ['#0d6efd', '#dc3545', '#198754', '#ffc107', '#0dcaf0', '#6f42c1', '#fd7e14'];
    let datasets = [];
    let labels = [];
    if (widget.variables && widget.variables.length > 0) {
        widget.variables.forEach((varName, idx) => {
            if (!labels || labels.length < (widget.data[varName]?.length || 0)) {
                labels = Array.from({length: widget.data[varName]?.length || 0}, (_, i) => i + 1);
            }
            datasets.push({
                label: varName,
                data: widget.data[varName] || [],
                borderColor: colors[idx % colors.length],
                backgroundColor: colors[idx % colors.length],
                tension: 0.1,
                pointRadius: 0,
                fill: false,
            });
        });
    }
    dashboardCharts[widget.id] = new Chart(plotCanvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {display: true, position: 'top'},
                zoom: (window.Chart && Chart.HasOwnProperty && Chart.hasOwnProperty('zoom')) ? {
                    pan: {enabled: true, modifierKey: 'ctrl'},
                    zoom: {wheel: {enabled: true}, pinch: {enabled: true}, mode: 'xy'}
                } : undefined
            },
            animation: {duration: 0},
            scales: {
                x: {
                    title: {display: true, text: 'Sample'},
                    ticks: {autoSkip: true, maxTicksLimit: 100}
                },
                y: {
                    title: {display: true, text: 'Value'}
                }
            }
        }
    });
}

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

function updateDashboardVariable(varName, value) {
    // Update local widget state
    const widgets = dashboardWidgets.filter(w => {
        if (w.type === 'plot_logger' || w.type === 'plot_scope') {
            return w.variables && w.variables.includes(varName);
        }
        return w.variable === varName;
    });

    // Find the first matching widget with gain/offset to reverse for device write
    const refWidget = widgets.find(w => w.variable === varName && w.type !== 'plot_logger' && w.type !== 'plot_scope');
    const rawValue = refWidget ? reverseGainOffset(value, refWidget) : value;

    widgets.forEach(widget => {
        if (widget.type === 'plot_logger') {
            if (!widget.data) widget.data = {};
            if (!widget.data[varName]) widget.data[varName] = [];
            widget.data[varName].push(value);
            if (widget.data[varName].length > widget.maxPoints) {
                widget.data[varName].shift();
            }
        } else if (widget.type === 'plot_scope') {
            if (!widget.data) widget.data = {};
            widget.data[varName] = Array.isArray(value) ? value : [value];
        } else {
            widget.value = value;
        }
        refreshWidgetInPlace(widget);
    });

    // Send raw (reversed) value to server via Socket.IO or HTTP
    if (dashboardSocket && dashboardSocket.connected) {
        dashboardSocket.emit('widget_interaction', {
            variable: varName,
            value: rawValue
        });
    } else {
        fetch('/dashboard-view/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ variable: varName, value: rawValue })
        });
    }
}

// Apply gain/offset: displayed = raw * gain + offset
function applyGainOffset(rawValue, widget) {
    const gain = widget.gain !== undefined ? widget.gain : 1;
    const offset = widget.offset !== undefined ? widget.offset : 0;
    return rawValue * gain + offset;
}

// Reverse gain/offset for writing: raw = (displayed - offset) / gain
function reverseGainOffset(displayedValue, widget) {
    const gain = widget.gain !== undefined ? widget.gain : 1;
    const offset = widget.offset !== undefined ? widget.offset : 0;
    return gain !== 0 ? (displayedValue - offset) / gain : displayedValue;
}

// Separate routing — watch data only updates non-scope widgets
function updateDashboardWatchWidgets(varName, value) {
    dashboardWidgets.forEach(widget => {
        if (widget.type === 'plot_scope') return; // scope data handled separately
        if (widget.type === 'plot_logger') {
            if (!widget.variables || !widget.variables.includes(varName)) return;
            if (!widget.data) widget.data = {};
            if (!widget.data[varName]) widget.data[varName] = [];
            widget.data[varName].push(applyGainOffset(value, widget));
            if (widget.data[varName].length > widget.maxPoints) {
                widget.data[varName].shift();
            }
            refreshWidgetInPlace(widget);
        } else if (widget.variable === varName && widget.type !== 'label') {
            widget.value = applyGainOffset(value, widget);
            refreshWidgetInPlace(widget);
        }
    });
}

// Fix 4: Scope data only updates plot_scope widgets
function updateDashboardScopeWidgets(varName, value) {
    dashboardWidgets.forEach(widget => {
        if (widget.type !== 'plot_scope') return;
        if (!widget.variables || !widget.variables.includes(varName)) return;
        if (!widget.data) widget.data = {};
        widget.data[varName] = Array.isArray(value) ? value : [value];
        refreshWidgetInPlace(widget);
    });
}

// Fix 3: In-place update without full re-render to avoid chart blinking
function refreshWidgetInPlace(widget) {
    const widgetEl = document.getElementById(`dashboard-widget-${widget.id}`);
    if (!widgetEl) {
        renderDashboardWidget(widget);
        return;
    }

    if (widget.type === 'gauge') {
        const chart = dashboardCharts[widget.id];
        if (!chart) { renderDashboardWidget(widget); return; }
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
        return;
    }

    if (widget.type === 'plot_logger' || widget.type === 'plot_scope') {
        const chart = dashboardCharts[widget.id];
        if (!chart) { renderDashboardWidget(widget); return; }
        if (widget.variables) {
            widget.variables.forEach((varName, idx) => {
                if (chart.data.datasets[idx]) {
                    chart.data.datasets[idx].data = widget.data[varName] || [];
                }
            });
            const maxLen = Math.max(0, ...widget.variables.map(v => (widget.data[v]?.length || 0)));
            chart.data.labels = Array.from({length: maxLen}, (_, i) => i + 1);
        }
        chart.update('none');
        return;
    }

    if (widget.type === 'slider') {
        const display = widgetEl.querySelector('.value-display');
        const input = widgetEl.querySelector('input[type="range"]');
        if (display) display.textContent = widget.value;
        if (input) input.value = widget.value;
        return;
    }

    if (widget.type === 'number') {
        const input = widgetEl.querySelector('input[type="number"]');
        if (input && document.activeElement !== input) input.value = widget.value;
        return;
    }

    if (widget.type === 'text') {
        const input = widgetEl.querySelector('input[type="text"]');
        if (input && document.activeElement !== input) input.value = widget.value;
        return;
    }
}

// Legacy function kept for updateDashboardVariable (user interactions)
function updateDashboardWidgetValue(varName, value) {
    const widgets = dashboardWidgets.filter(w => {
        if (w.type === 'plot_logger' || w.type === 'plot_scope') {
            return w.variables && w.variables.includes(varName);
        }
        return w.variable === varName;
    });

    widgets.forEach(widget => {
        if (widget.type === 'plot_logger') {
            if (!widget.data) widget.data = {};
            if (!widget.data[varName]) widget.data[varName] = [];
            widget.data[varName].push(value);
            if (widget.data[varName].length > widget.maxPoints) {
                widget.data[varName].shift();
            }
        } else if (widget.type === 'plot_scope') {
            if (!widget.data) widget.data = {};
            widget.data[varName] = Array.isArray(value) ? value : [value];
        } else {
            widget.value = value;
        }
        refreshWidgetInPlace(widget);
    });
}

function updateDashboardWidgetsFromData(data) {
    for (let varName in data) {
        updateDashboardWidgetValue(varName, data[varName]);
    }
}

function deleteDashboardWidget(id) {
    if (confirm('Delete this widget?')) {
        const index = dashboardWidgets.findIndex(w => w.id === id);
        if (index > -1) {
            unregisterWidgetVariables(dashboardWidgets[index]);
            dashboardWidgets.splice(index, 1);
            const el = document.getElementById(`dashboard-widget-${id}`);
            if (el) el.remove();
            // Also clean up any Chart.js instance for this widget
            if (dashboardCharts[id]) {
                dashboardCharts[id].destroy();
                delete dashboardCharts[id];
            }
        }
    }
}

function startDashboardDrag(e) {
    if (!isDashboardEditMode) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const resizeZone = 20; // px from bottom-right corner

    // Don't start drag if clicking near the resize handle (bottom-right corner)
    if (e.clientX > rect.right - resizeZone && e.clientY > rect.bottom - resizeZone) {
        return;
    }

    draggedWidget = e.currentTarget;

    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;

    document.addEventListener('mousemove', dashboardDrag);
    document.addEventListener('mouseup', stopDashboardDrag);
}

function dashboardDrag(e) {
    if (!draggedWidget) return;

    const canvas = document.getElementById('dashboardCanvas').getBoundingClientRect();
    let x = e.clientX - canvas.left - dragOffsetX;
    let y = e.clientY - canvas.top - dragOffsetY;

    draggedWidget.style.left = x + 'px';
    draggedWidget.style.top = y + 'px';
}

function stopDashboardDrag() {
    if (draggedWidget) {
        const id = parseInt(draggedWidget.id.replace('dashboard-widget-', ''));
        const widget = dashboardWidgets.find(w => w.id === id);
        if (widget) {
            widget.x = parseInt(draggedWidget.style.left);
            widget.y = parseInt(draggedWidget.style.top);
        }
    }

    draggedWidget = null;
    document.removeEventListener('mousemove', dashboardDrag);
    document.removeEventListener('mouseup', stopDashboardDrag);
}

function saveDashboardLayout() {
    fetch('/dashboard-view/save-layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dashboardWidgets)
    })
    .then(r => r.json())
    .then(data => {
        alert(data.message || 'Layout saved successfully');
    })
    .catch(err => {
        console.error('Error saving layout:', err);
        alert('Error saving layout');
    });
}

function loadDashboardLayout() {
    fetch('/dashboard-view/load-layout')
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            removeAllDashboardVariables();
            dashboardWidgets = data.layout;
            widgetIdCounter = Math.max(...dashboardWidgets.map(w => w.id), 0) + 1;
            document.getElementById('dashboardCanvas').innerHTML = '';
            dashboardWidgets.forEach(w => renderDashboardWidget(w));
            registerAllDashboardVariables();
            alert('Layout loaded successfully');
        } else {
            alert(data.message || 'No saved layout found');
        }
    })
    .catch(err => {
        console.error('Error loading layout:', err);
        alert('No saved layout found');
    });
}

function exportDashboardLayout() {
    const dataStr = JSON.stringify(dashboardWidgets, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'dashboard_layout.json';
    link.click();
    URL.revokeObjectURL(url);
}

function importDashboardLayout() {
    document.getElementById('dashboardFileInput').click();
}

function handleDashboardFileImport(e) {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                removeAllDashboardVariables();
                dashboardWidgets = JSON.parse(event.target.result);
                widgetIdCounter = Math.max(...dashboardWidgets.map(w => w.id), 0) + 1;
                document.getElementById('dashboardCanvas').innerHTML = '';
                dashboardWidgets.forEach(w => renderDashboardWidget(w));
                registerAllDashboardVariables();
                alert('Layout imported successfully');
            } catch (err) {
                console.error('Import error:', err);
                alert('Error importing layout: Invalid JSON file');
            }
        };
        reader.readAsText(file);
    }
}