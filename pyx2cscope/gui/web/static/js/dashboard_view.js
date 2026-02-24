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

    // Get widget type definition from modular system
    const widgetDef = window.dashboardWidgetTypes[type];
    if (!widgetDef) {
        console.error(`Unknown widget type: ${type}`);
        return;
    }

    extraConfig.innerHTML = '';
    modalTitle.textContent = editWidget ? 'Edit Widget Configuration' : 'Configure Widget';

    // Destroy previous Select2 instances
    if ($('#widgetVarName').data('select2')) {
        $('#widgetVarName').select2('destroy');
    }

    // Show/hide the single variable selector based on widget type
    if (widgetDef.requiresMultipleVariables || !widgetDef.requiresVariable) {
        varNameContainer.style.display = 'none';
    } else {
        varNameContainer.style.display = '';
        // Reset and populate for edit mode
        $('#widgetVarName').empty();
        if (editWidget) {
            $('#widgetVarName').append(new Option(editWidget.variable, editWidget.variable, true, true));
        }
    }

    // Get widget-specific configuration HTML
    if (widgetDef.getConfig) {
        extraConfig.innerHTML = widgetDef.getConfig(editWidget);
    }

    const modal = new bootstrap.Modal(document.getElementById('widgetConfigModal'));
    modal.show();

    // Initialize Select2 after modal is shown so dropdown renders correctly
    $('#widgetConfigModal').one('shown.bs.modal', function() {
        if (widgetDef.requiresVariable && !widgetDef.requiresMultipleVariables) {
            $('#widgetVarName').select2(initWidgetVarSelect2());
            if (editWidget) {
                $('#widgetVarName').prop('disabled', true);
            }
        }
        if (widgetDef.initSelect2) {
            widgetDef.initSelect2(editWidget);
        }
    });

    // Store reference to widget being edited
    window.editingWidget = editWidget;
}

function addDashboardWidget() {
    const editWidget = window.editingWidget;
    const widgetDef = window.dashboardWidgetTypes[currentWidgetType];

    if (!widgetDef) {
        console.error(`Unknown widget type: ${currentWidgetType}`);
        return;
    }

    let widget;
    if (editWidget) {
        // Editing existing widget
        widget = editWidget;
    } else {
        // Creating new widget
        const varName = widgetDef.requiresMultipleVariables ? '' : ($('#widgetVarName').val() || '');
        if (!varName && widgetDef.requiresVariable) {
            alert('Please select a variable name');
            return;
        }

        widget = {
            id: widgetIdCounter++,
            type: currentWidgetType,
            variable: varName,
            icon: widgetDef.icon,
            x: 50,
            y: 50,
            value: currentWidgetType === 'text' ? '' : 0
        };
    }

    // Call widget-specific save config
    if (widgetDef.saveConfig) {
        const result = widgetDef.saveConfig(widget);
        if (result === false) return; // Config validation failed
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

    // Get widget definition from modular system
    const widgetDef = window.dashboardWidgetTypes[widget.type];
    if (!widgetDef) {
        console.error(`Unknown widget type: ${widget.type}`);
        return;
    }

    let content = '';
    const typeIcons = `<span class="material-icons md-18">${widget.icon}</span>`;
    const displayName = widget.type === 'plot_logger' || widget.type === 'plot_scope'
        ? widget.variables?.join(', ') || widget.variable
        : widget.variable;

    const header = `
        <div class="widget-header">
            <span class="widget-title">${typeIcons} ${displayName}</span>
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

    // Use modular widget's create function
    content = header + widgetDef.create(widget) + '</div>';

    widgetEl.innerHTML = content;

    // Call afterRender if widget has it
    if (widgetDef.afterRender) {
        widgetDef.afterRender(widget);
    }
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

// Scope data only updates plot_scope widgets
function updateDashboardScopeWidgets(varName, value) {
    dashboardWidgets.forEach(widget => {
        if (widget.type !== 'plot_scope') return;
        if (!widget.variables || !widget.variables.includes(varName)) return;
        if (!widget.data) widget.data = {};
        widget.data[varName] = Array.isArray(value) ? value : [value];
        refreshWidgetInPlace(widget);
    });
}

// In-place update without full re-render to avoid chart blinking
function refreshWidgetInPlace(widget) {
    const widgetEl = document.getElementById(`dashboard-widget-${widget.id}`);
    if (!widgetEl) {
        renderDashboardWidget(widget);
        return;
    }

    const widgetDef = window.dashboardWidgetTypes[widget.type];
    if (widgetDef && widgetDef.refresh) {
        widgetDef.refresh(widget, widgetEl);
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