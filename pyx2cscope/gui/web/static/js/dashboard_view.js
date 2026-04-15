// Dashboard View JavaScript
// This file handles all dashboard widget functionality

let dashboardWidgets = [];
let selectedWidget = null;
let isDashboardEditMode = true;
let draggedWidget = null;
let dragOffsetX = 0;
let dragOffsetY = 0;
let currentWidgetType = '';
let widgetIdCounter = 0;
let dashboardSocket = null;
let scopeSocket = null; // Separate socket for scope-related commands

// Track chart.js instances per-widget
let dashboardCharts = {};

// Initialize widget types registry (widgets register themselves here)
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

// Initialize dashboard when page loads (use 'load' to ensure widget scripts have registered)
window.addEventListener('load', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Populate widget palette from registered widget types
    populateWidgetPalette();

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

        // Connect to scope-view namespace for sending scope trigger commands
        scopeSocket = io('/scope-view');
        scopeSocket.on('connect', () => {
            console.log('Dashboard connected to scope-view namespace');
            // Fetch current scope variables via HTTP
            fetchScopeVariables();
        });

        // Listen for scope table updates (variables added/removed)
        scopeSocket.on('scope_table_update', (data) => {
            console.log('Scope table update:', data);
            // Refetch variables when scope table changes
            fetchScopeVariables();
        });

        // Listen for sample control updates
        scopeSocket.on('sample_control_updated', (response) => {
            if (response.status === 'success' && response.data) {
                updateScopeControlSampleState(response.data);
            }
        });

        // Listen for trigger control updates
        scopeSocket.on('trigger_control_updated', (response) => {
            if (response.status === 'success' && response.data) {
                updateScopeControlTriggerState(response.data);
            }
        });

    }

    // Set up file input for import
    document.getElementById('dashboardFileInput').addEventListener('change', handleDashboardFileImport);

    // Set up canvas click handler for deselecting widgets
    initCanvasClickHandler();

    // Fetch scope variables via HTTP
    fetchScopeVariables();

    // Initialize UI for edit mode (default state)
    initEditModeUI();
}

function initEditModeUI() {
    const btn = document.getElementById('dashboardModeBtn');
    const icon = btn?.querySelector('.material-icons');
    const palette = document.getElementById('widgetPalette');
    const canvasCol = document.getElementById('dashboardCanvasCol');
    const canvas = document.getElementById('dashboardCanvas');

    if (isDashboardEditMode) {
        if (icon) {
            icon.textContent = 'edit';
            icon.classList.remove('text-secondary');
            icon.classList.add('text-success');
        }
        if (btn) btn.title = 'Edit Mode (Active)';
        if (palette) palette.style.display = 'block';
        if (canvasCol) {
            canvasCol.classList.remove('col-12');
            canvasCol.classList.add('col-12', 'col-md-9', 'col-lg-10');
        }
        if (canvas) {
            canvas.classList.remove('view-mode');
            canvas.classList.add('edit-mode');
        }
    }
}

// Track scope variables list from scope-view
window.scopeVariablesList = [];

// Fetch scope variables from server
function fetchScopeVariables() {
    fetch('/scope/data')
        .then(response => response.json())
        .then(data => {
            if (data.data) {
                window.scopeVariablesList = data.data.map(v => v.variable);
                updateScopeControlVariables();
            }
        })
        .catch(err => console.log('Could not fetch scope variables:', err));
}

// Update scope control widgets when variables change
function updateScopeControlVariables() {
    dashboardWidgets
        .filter(w => w.type === 'scope_control')
        .forEach(widget => {
            // Update trigger variable dropdown
            const dropdown = document.getElementById(`scopeCtrlTriggerVar-${widget.id}`);
            if (dropdown) {
                // Use saved widget.triggerVar if dropdown is empty (initial load)
                const currentValue = dropdown.value || widget.triggerVar || '';
                dropdown.innerHTML = '<option value="">None</option>';
                (window.scopeVariablesList || []).forEach(v => {
                    const opt = document.createElement('option');
                    opt.value = v;
                    opt.textContent = v;
                    if (v === currentValue) opt.selected = true;
                    dropdown.appendChild(opt);
                });
            }
        });
}

// Update scope control sample state
function updateScopeControlSampleState(data) {
    if (data.triggerAction) {
        scopeControlState = data.triggerAction;
    }
    dashboardWidgets
        .filter(w => w.type === 'scope_control')
        .forEach(widget => {
            // Update sample time/freq if elements exist
            const sampleTimeEl = document.getElementById('scopeCtrlSampleTime');
            const sampleFreqEl = document.getElementById('scopeCtrlSampleFreq');
            if (sampleTimeEl && data.sampleTime !== undefined) sampleTimeEl.value = data.sampleTime;
            if (sampleFreqEl && data.sampleFreq !== undefined) sampleFreqEl.value = data.sampleFreq;

            // Update button states
            const widgetEl = document.getElementById(`dashboard-widget-${widget.id}`);
            if (widgetEl) {
                const widgetDef = window.dashboardWidgetTypes[widget.type];
                if (widgetDef?.refresh) widgetDef.refresh(widget, widgetEl);
            }
        });
}

// Update scope control trigger state
function updateScopeControlTriggerState(data) {
    dashboardWidgets
        .filter(w => w.type === 'scope_control')
        .forEach(widget => {
            // Update trigger mode
            if (data.trigger_mode !== undefined) {
                const enableRadio = document.getElementById(`scopeCtrlTriggerEnable-${widget.id}`);
                const disableRadio = document.getElementById(`scopeCtrlTriggerDisable-${widget.id}`);
                if (enableRadio && disableRadio) {
                    enableRadio.checked = data.trigger_mode === '1' || data.trigger_mode === 1;
                    disableRadio.checked = data.trigger_mode === '0' || data.trigger_mode === 0;
                }
            }
            // Update trigger edge
            if (data.trigger_edge !== undefined) {
                const risingRadio = document.getElementById(`scopeCtrlEdgeRising-${widget.id}`);
                const fallingRadio = document.getElementById(`scopeCtrlEdgeFalling-${widget.id}`);
                if (risingRadio && fallingRadio) {
                    risingRadio.checked = data.trigger_edge === '1' || data.trigger_edge === 1;
                    fallingRadio.checked = data.trigger_edge === '0' || data.trigger_edge === 0;
                }
            }
            // Update trigger level (snake_case from backend)
            if (data.trigger_level !== undefined) {
                const levelEl = document.getElementById(`scopeCtrlTriggerLevel-${widget.id}`);
                if (levelEl) levelEl.value = data.trigger_level;
            }
            // Update trigger delay (snake_case from backend)
            if (data.trigger_delay !== undefined) {
                const delayEl = document.getElementById(`scopeCtrlTriggerDelay-${widget.id}`);
                if (delayEl) delayEl.value = data.trigger_delay;
            }
        });
}

// Sync scope control settings to backend after loading dashboard
function syncScopeControlToBackend() {
    if (!scopeSocket || !scopeSocket.connected) {
        // Retry after a short delay if socket not ready
        setTimeout(syncScopeControlToBackend, 500);
        return;
    }

    // First: Register plot_scope variables with scope view
    dashboardWidgets
        .filter(w => w.type === 'plot_scope')
        .forEach(widget => {
            if (widget.variables) {
                widget.variables.forEach(v => {
                    // Check if not already in scope view
                    if (!window.scopeVariablesList.includes(v)) {
                        scopeSocket.emit('add_scope_var', { var: v });
                    }
                });
            }
        });

    // Find scope_control widgets and sync their settings
    const scopeControlWidget = dashboardWidgets.find(w => w.type === 'scope_control');
    if (scopeControlWidget) {
        // Sync sample control settings
        const sampleTime = scopeControlWidget.sampleTime !== undefined ? scopeControlWidget.sampleTime : 1;
        const sampleFreq = scopeControlWidget.sampleFreq || 20;
        const sampleFormData = `triggerAction=off&sampleTime=${sampleTime}&sampleFreq=${sampleFreq}`;
        scopeSocket.emit('update_sample_control', sampleFormData);

        // Sync trigger control settings
        const triggerMode = scopeControlWidget.triggerMode || '0';
        const triggerEdge = scopeControlWidget.triggerEdge || '1';
        const triggerLevel = scopeControlWidget.triggerLevel || 0;
        const triggerDelay = scopeControlWidget.triggerDelay || 0;
        const triggerFormData = `trigger_mode=${triggerMode}&trigger_edge=${triggerEdge}&trigger_level=${triggerLevel}&trigger_delay=${triggerDelay}`;
        scopeSocket.emit('update_trigger_control', triggerFormData);

        // Sync trigger variable selection (wait for variables to be registered first)
        const triggerVar = scopeControlWidget.triggerVar || '';
        if (triggerVar) {
            // Wait for scope variables to be registered, then set trigger
            setTimeout(() => {
                // Refetch scope variables to ensure we have the latest list
                fetch('/scope/data')
                    .then(response => response.json())
                    .then(data => {
                        if (data.data) {
                            const scopeVars = data.data.map(v => v.variable);
                            scopeVars.forEach(varName => {
                                scopeSocket.emit('update_scope_var', {
                                    param: varName,
                                    field: 'trigger',
                                    value: varName === triggerVar ? '1' : '0'
                                });
                            });
                            // Re-send trigger control settings after setting trigger variable
                            // This ensures the backend properly initializes the trigger
                            setTimeout(() => {
                                scopeSocket.emit('update_trigger_control', triggerFormData);
                            }, 500);
                        }
                    })
                    .catch(err => console.log('Could not sync trigger variable:', err));
            }, 1500);
        }
    }
}

function populateWidgetPalette() {
    const container = document.getElementById('widgetPaletteButtons');
    if (!container || !window.dashboardWidgetTypes) return;

    container.innerHTML = '';

    for (const [type, def] of Object.entries(window.dashboardWidgetTypes)) {
        const displayName = def.name || type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-outline-primary text-start';
        btn.onclick = () => showWidgetConfig(type);
        btn.innerHTML = `<span class="material-icons md-18">${def.icon}</span> ${displayName}`;
        container.appendChild(btn);
    }
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
    selectedWidget = null; // Deselect any selected widget when switching modes
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
            data: function(params) {
                return { q: params.term, sfr: $('#widgetSfrToggle').is(':checked') };
            },
            processResults: function (data) {
                return { results: data.items };
            },
            cache: false
        },
        minimumInputLength: 3
    };
    return $.extend(true, {}, defaults, options);
}

function reinitWidgetVarSelect2() {
    if ($('#widgetVarName').data('select2')) {
        $('#widgetVarName').val(null).trigger('change');
        $('#widgetVarName').select2('destroy');
    }
    $('#widgetVarName').select2(initWidgetVarSelect2());
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
        // Reset SFR toggle for each new config session
        $('#widgetSfrToggle').prop('checked', false);

        if (widgetDef.requiresVariable && !widgetDef.requiresMultipleVariables) {
            $('#widgetVarName').select2(initWidgetVarSelect2());
            if (editWidget) {
                $('#widgetVarName').prop('disabled', true);
            }
            // Reinitialize select2 when SFR toggle changes
            $('#widgetSfrToggle').off('change.widgetVarSelect2').on('change.widgetVarSelect2', function() {
                if (!$('#widgetVarName').prop('disabled')) {
                    reinitWidgetVarSelect2();
                }
            });
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

// Select a widget in edit mode
function selectDashboardWidget(id) {
    if (!isDashboardEditMode) return;

    const prevSelectedId = selectedWidget;

    // Update selection state first (before re-rendering)
    if (selectedWidget === id) {
        selectedWidget = null; // Toggle off if clicking same widget
    } else {
        selectedWidget = id;
    }

    // Re-render previous widget (now deselected)
    if (prevSelectedId !== null && prevSelectedId !== id) {
        const prevWidget = dashboardWidgets.find(w => w.id === prevSelectedId);
        if (prevWidget) renderDashboardWidget(prevWidget);
    }

    // Re-render clicked widget (selected or deselected)
    const widget = dashboardWidgets.find(w => w.id === id);
    if (widget) renderDashboardWidget(widget);
}

// Deselect widget when clicking on canvas background
function initCanvasClickHandler() {
    const canvas = document.getElementById('dashboardCanvas');
    if (canvas) {
        canvas.addEventListener('click', (e) => {
            if (e.target === canvas && selectedWidget !== null) {
                const prevSelectedId = selectedWidget;
                selectedWidget = null; // Update state first
                const prevWidget = dashboardWidgets.find(w => w.id === prevSelectedId);
                if (prevWidget) renderDashboardWidget(prevWidget);
            }
        });
    }
}

// This is the major override for rendering widgets and using Chart.js for gauge/plot
function renderDashboardWidget(widget) {
    let widgetEl = document.getElementById(`dashboard-widget-${widget.id}`);
    const isSelected = selectedWidget === widget.id;

    if (!widgetEl) {
        widgetEl = document.createElement('div');
        widgetEl.id = `dashboard-widget-${widget.id}`;
        widgetEl.className = `dashboard-widget widget-type-${widget.type}`;
        widgetEl.style.left = widget.x + 'px';
        widgetEl.style.top = widget.y + 'px';

        // Set saved dimensions if available
        if (widget.width) widgetEl.style.width = widget.width + 'px';
        if (widget.height) widgetEl.style.height = widget.height + 'px';

        widgetEl.addEventListener('mousedown', startDashboardDrag);
        widgetEl.addEventListener('click', (e) => {
            e.stopPropagation();
            selectDashboardWidget(widget.id);
        });

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

    // Update widget classes based on mode and selection
    if (isDashboardEditMode) {
        widgetEl.classList.add('edit-mode');
        widgetEl.classList.remove('view-mode');
        if (isSelected) {
            widgetEl.classList.add('selected');
        } else {
            widgetEl.classList.remove('selected');
        }
    } else {
        widgetEl.classList.remove('edit-mode', 'selected');
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

    // Show header only in edit mode when widget is selected
    if (isDashboardEditMode && isSelected) {
        const header = `
            <div class="widget-header">
                <span class="widget-title">${typeIcons} ${displayName}</span>
                <div class="widget-controls">
                    <button class="btn btn-sm" onclick="event.stopPropagation(); showWidgetConfig('${widget.type}', dashboardWidgets.find(w => w.id === ${widget.id}))" title="Edit">
                        <span class="material-icons text-primary">settings</span>
                    </button>
                    <button class="btn btn-sm" onclick="event.stopPropagation(); deleteDashboardWidget(${widget.id})" title="Delete">
                        <span class="material-icons text-danger">delete</span>
                    </button>
                </div>
            </div>
            <div class="widget-content">
        `;
        content = header + widgetDef.create(widget) + '</div>';
    } else {
        // View mode or unselected edit mode: show only widget content
        content = `<div class="widget-content-only">${widgetDef.create(widget)}</div>`;
    }

    widgetEl.innerHTML = content;

    // Call afterRender if widget has it
    if (widgetDef.afterRender) {
        widgetDef.afterRender(widget);
    }
}

// Chart.js plot rendering (line)
function renderDashboardPlot(widget, plotCanvas) {
    if (dashboardCharts[widget.id]) {
        dashboardCharts[widget.id].destroy();
    }
    // Default colors if no custom settings
    const defaultColors = ['#0d6efd', '#dc3545', '#198754', '#ffc107', '#0dcaf0', '#6f42c1', '#fd7e14', '#20c997'];
    let datasets = [];
    let maxLen = 0;

    if (widget.variables && widget.variables.length > 0) {
        widget.variables.forEach((varName, idx) => {
            const rawData = widget.data[varName] || [];
            if (rawData.length > maxLen) maxLen = rawData.length;

            // Get per-variable settings (color, gain, offset)
            const settings = widget.varSettings?.[varName] || {};
            const color = settings.color || defaultColors[idx % defaultColors.length];
            const gain = settings.gain !== undefined ? settings.gain : 1;
            const offset = settings.offset !== undefined ? settings.offset : 0;

            // Apply gain and offset to data
            const processedData = rawData.map(v => (v * gain) + offset);

            datasets.push({
                label: varName,
                data: processedData,
                borderColor: color,
                backgroundColor: color,
                tension: 0.1,
                pointRadius: 0,
                fill: false,
            });
        });
    }

    // Generate X-axis labels
    let labels = [];
    let xLabel = widget.xLabel || 'Sample';

    if (widget.type === 'plot_scope' && typeof generateTimeLabels === 'function') {
        const timeData = generateTimeLabels(maxLen);
        labels = timeData.labels;
        xLabel = `Time (${timeData.unit})`;
    } else {
        labels = Array.from({length: maxLen}, (_, i) => i + 1);
    }

    const yLabel = widget.yLabel || 'Value';
    const showLegend = widget.showLegend !== false; // default true

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
                legend: {display: showLegend, position: 'top'},
                zoom: (window.Chart && Chart.HasOwnProperty && Chart.hasOwnProperty('zoom')) ? {
                    pan: {enabled: true, modifierKey: 'ctrl'},
                    zoom: {wheel: {enabled: true}, pinch: {enabled: true}, mode: 'xy'}
                } : undefined
            },
            animation: {duration: 0},
            scales: {
                x: {
                    title: {display: true, text: xLabel},
                    ticks: {autoSkip: true, maxTicksLimit: 20}
                },
                y: {
                    title: {display: true, text: yLabel}
                }
            }
        }
    });
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
        fetch('/dashboard/update', {
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

        // Check if widget should be updated based on its update rate setting
        if (window.shouldUpdateWidget && !window.shouldUpdateWidget(widget)) return;

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
            // Deselect if this widget is selected
            if (selectedWidget === id) {
                selectedWidget = null;
            }
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
    fetch('/dashboard/save-layout', {
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
    fetch('/dashboard/load-layout')
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            // Unregister old variables
            removeAllDashboardVariables();
            // Destroy all existing chart instances before clearing
            for (const id in dashboardCharts) {
                if (dashboardCharts[id]) {
                    dashboardCharts[id].destroy();
                    delete dashboardCharts[id];
                }
            }
            // Load new layout
            dashboardWidgets = data.layout;
            widgetIdCounter = Math.max(...dashboardWidgets.map(w => w.id), 0) + 1;
            // Clear canvas
            document.getElementById('dashboardCanvas').innerHTML = '';
            // Render new widgets
            dashboardWidgets.forEach(w => renderDashboardWidget(w));
            registerAllDashboardVariables();
            syncScopeControlToBackend();
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

function clearDashboard() {
    if (dashboardWidgets.length === 0) {
        alert('Dashboard is already empty');
        return;
    }
    if (confirm('Are you sure you want to remove all widgets from the dashboard?')) {
        // Unregister all variables
        removeAllDashboardVariables();
        // Destroy all chart instances
        for (const id in dashboardCharts) {
            dashboardCharts[id].destroy();
            delete dashboardCharts[id];
        }
        // Clear widgets array
        dashboardWidgets = [];
        selectedWidget = null;
        // Clear the canvas
        document.getElementById('dashboardCanvas').innerHTML = '';
    }
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
                // Unregister old variables
                removeAllDashboardVariables();
                // Destroy all existing chart instances before clearing
                for (const id in dashboardCharts) {
                    if (dashboardCharts[id]) {
                        dashboardCharts[id].destroy();
                        delete dashboardCharts[id];
                    }
                }
                // Parse and load new layout
                dashboardWidgets = JSON.parse(event.target.result);
                widgetIdCounter = Math.max(...dashboardWidgets.map(w => w.id), 0) + 1;
                // Clear canvas
                document.getElementById('dashboardCanvas').innerHTML = '';
                // Render new widgets
                dashboardWidgets.forEach(w => renderDashboardWidget(w));
                registerAllDashboardVariables();
                syncScopeControlToBackend();
                alert('Layout imported successfully');
            } catch (err) {
                console.error('Import error:', err);
                alert('Error importing layout: Invalid JSON file');
            }
        };
        reader.readAsText(file);
    }
}
