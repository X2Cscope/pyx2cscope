/**
 * Plot Logger Widget - Scrolling time-series plot using Chart.js
 *
 * Features:
 * - Multiple variables on one plot
 * - Configurable max data points (scrolling window)
 * - Auto-scaling
 * - Per-variable color, gain, and offset
 * - Show/hide legend option
 */

const plotLoggerDefaultColors = ['#0d6efd', '#dc3545', '#198754', '#ffc107', '#0dcaf0', '#6f42c1', '#fd7e14', '#20c997'];

function createPlotLoggerWidget(widget) {
    return `
        <canvas class="plot-container" id="dashboard-plot-${widget.id}"></canvas>
    `;
}

function getPlotLoggerConfig(editWidget) {
    // Build variable settings HTML if variables exist
    let varSettingsHtml = '';
    if (editWidget?.variables && editWidget.variables.length > 0) {
        varSettingsHtml = buildPlotLoggerVariableSettingsHtml(editWidget);
    }

    const showLegend = editWidget?.showLegend !== false; // default true

    return `
        <div class="mb-3">
            <label class="form-label">Variables</label>
            <select class="form-control" id="widgetVariables" multiple="multiple" style="width: 100%;"></select>
            <small class="form-text text-muted">Search and select variables, then configure each below</small>
        </div>
        <div id="variableSettingsContainer">${varSettingsHtml}</div>
        <div class="row mb-3">
            <div class="col-6">
                <label class="form-label">Max Data Points</label>
                <input type="number" class="form-control" id="widgetMaxPoints" value="${editWidget?.maxPoints || 50}">
            </div>
            <div class="col-6">
                <label class="form-label">Show Legend</label>
                <select class="form-select" id="widgetShowLegend">
                    <option value="true" ${showLegend ? 'selected' : ''}>Yes</option>
                    <option value="false" ${!showLegend ? 'selected' : ''}>No</option>
                </select>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-6">
                <label class="form-label">X Axis Label</label>
                <input type="text" class="form-control" id="widgetXLabel" value="${editWidget?.xLabel || 'Sample'}" placeholder="Sample">
            </div>
            <div class="col-6">
                <label class="form-label">Y Axis Label</label>
                <input type="text" class="form-control" id="widgetYLabel" value="${editWidget?.yLabel || 'Value'}" placeholder="Value">
            </div>
        </div>
    `;
}

function buildPlotLoggerVariableSettingsHtml(widget) {
    if (!widget?.variables || widget.variables.length === 0) return '';

    let html = '<label class="form-label mt-3">Variable Settings</label>';
    widget.variables.forEach((varName, idx) => {
        const settings = widget.varSettings?.[varName] || {};
        const color = settings.color || plotLoggerDefaultColors[idx % plotLoggerDefaultColors.length];
        const gain = settings.gain !== undefined ? settings.gain : 1;
        const offset = settings.offset !== undefined ? settings.offset : 0;

        html += `
            <div class="card mb-2">
                <div class="card-body p-2">
                    <div class="fw-bold small mb-2">${varName}</div>
                    <div class="row g-2">
                        <div class="col-4">
                            <label class="form-label small mb-0">Color</label>
                            <input type="color" class="form-control form-control-sm form-control-color w-100"
                                   id="varColor-${idx}" value="${color}">
                        </div>
                        <div class="col-4">
                            <label class="form-label small mb-0">Gain</label>
                            <input type="number" class="form-control form-control-sm"
                                   id="varGain-${idx}" value="${gain}" step="0.1">
                        </div>
                        <div class="col-4">
                            <label class="form-label small mb-0">Offset</label>
                            <input type="number" class="form-control form-control-sm"
                                   id="varOffset-${idx}" value="${offset}" step="0.1">
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    return html;
}

function updatePlotLoggerVariableSettingsUI() {
    const selectedVars = $('#widgetVariables').val() || [];
    const container = document.getElementById('variableSettingsContainer');
    if (!container) return;

    // Build a temporary widget object with current selections
    const tempWidget = {
        variables: selectedVars,
        varSettings: {}
    };

    // Preserve existing settings from current inputs
    selectedVars.forEach((varName, idx) => {
        const colorEl = document.getElementById(`varColor-${idx}`);
        const gainEl = document.getElementById(`varGain-${idx}`);
        const offsetEl = document.getElementById(`varOffset-${idx}`);
        if (colorEl || gainEl || offsetEl) {
            tempWidget.varSettings[varName] = {
                color: colorEl?.value || plotLoggerDefaultColors[idx % plotLoggerDefaultColors.length],
                gain: parseFloat(gainEl?.value) || 1,
                offset: parseFloat(offsetEl?.value) || 0
            };
        } else {
            tempWidget.varSettings[varName] = {
                color: plotLoggerDefaultColors[idx % plotLoggerDefaultColors.length],
                gain: 1,
                offset: 0
            };
        }
    });

    container.innerHTML = buildPlotLoggerVariableSettingsHtml(tempWidget);
}

function savePlotLoggerConfig(widget) {
    widget.variables = $('#widgetVariables').val() || [];
    if (widget.variables.length === 0) {
        alert('Please enter at least one variable name');
        return false;
    }

    // Initialize data storage, preserving existing data
    if (!widget.data) widget.data = {};
    widget.variables.forEach(v => {
        if (!widget.data[v]) widget.data[v] = [];
    });

    // Save per-variable settings
    widget.varSettings = {};
    widget.variables.forEach((varName, idx) => {
        const colorEl = document.getElementById(`varColor-${idx}`);
        const gainEl = document.getElementById(`varGain-${idx}`);
        const offsetEl = document.getElementById(`varOffset-${idx}`);
        widget.varSettings[varName] = {
            color: colorEl?.value || plotLoggerDefaultColors[idx % plotLoggerDefaultColors.length],
            gain: parseFloat(gainEl?.value) || 1,
            offset: parseFloat(offsetEl?.value) || 0
        };
    });

    widget.maxPoints = parseInt(document.getElementById('widgetMaxPoints').value) || 50;
    widget.showLegend = document.getElementById('widgetShowLegend').value === 'true';
    widget.xLabel = document.getElementById('widgetXLabel').value || 'Sample';
    widget.yLabel = document.getElementById('widgetYLabel').value || 'Value';
    return true;
}

function afterRenderPlotLoggerWidget(widget) {
    setTimeout(() => {
        const plotCanvas = document.getElementById(`dashboard-plot-${widget.id}`);
        if (plotCanvas && typeof Chart !== 'undefined') {
            renderDashboardPlot(widget, plotCanvas);
        }
    }, 100);
}

function refreshPlotLoggerWidget(widget, widgetEl) {
    const chart = dashboardCharts[widget.id];
    if (!chart) {
        afterRenderPlotLoggerWidget(widget);
        return;
    }
    if (widget.variables) {
        widget.variables.forEach((varName, idx) => {
            if (chart.data.datasets[idx]) {
                const settings = widget.varSettings?.[varName] || { gain: 1, offset: 0 };
                const rawData = widget.data[varName] || [];
                // Apply gain and offset
                chart.data.datasets[idx].data = rawData.map(v => (v * settings.gain) + settings.offset);
            }
        });
        const maxLen = Math.max(0, ...widget.variables.map(v => (widget.data[v]?.length || 0)));
        chart.data.labels = Array.from({length: maxLen}, (_, i) => i + 1);
    }
    chart.update('none');
}

// Initialize Select2 for variables
function initPlotLoggerSelect2(editWidget) {
    $('#widgetVariables').select2({
        placeholder: "Search and select variables",
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
        minimumInputLength: 3,
        multiple: true
    });

    // Pre-populate existing variables when editing
    if (editWidget?.variables) {
        editWidget.variables.forEach(v => {
            $('#widgetVariables').append(new Option(v, v, true, true));
        });
        $('#widgetVariables').trigger('change');
    }

    // Update variable settings when selection changes
    $('#widgetVariables').on('change', function() {
        updatePlotLoggerVariableSettingsUI();
    });
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.plot_logger = {
    icon: 'timeline',
    create: createPlotLoggerWidget,
    getConfig: getPlotLoggerConfig,
    saveConfig: savePlotLoggerConfig,
    afterRender: afterRenderPlotLoggerWidget,
    refresh: refreshPlotLoggerWidget,
    initSelect2: initPlotLoggerSelect2,
    requiresVariable: false,
    requiresMultipleVariables: true,
    supportsGainOffset: false
};
