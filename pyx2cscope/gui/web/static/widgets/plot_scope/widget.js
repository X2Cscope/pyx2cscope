/**
 * Plot Scope Widget - Triggered oscilloscope-style plot using Chart.js
 *
 * Features:
 * - Multiple variables on one plot
 * - Triggered data capture (replaces entire buffer on update)
 * - Auto-scaling
 * - Per-variable color, gain, and offset
 * - Time-based X-axis from scope control settings
 * - Show/hide legend option
 *
 * Note: Trigger configuration is managed in Scope View.
 * Use Scope Control widget to start/stop sampling.
 */

const plotScopeDefaultColors = ['#0d6efd', '#dc3545', '#198754', '#ffc107', '#0dcaf0', '#6f42c1', '#fd7e14', '#20c997'];

function createPlotScopeWidget(widget) {
    return `
        <canvas class="plot-container" id="dashboard-plot-${widget.id}"></canvas>
    `;
}

function getPlotScopeConfig(editWidget) {
    // Build variable settings HTML if variables exist
    let varSettingsHtml = '';
    if (editWidget?.variables && editWidget.variables.length > 0) {
        varSettingsHtml = buildPlotScopeVariableSettingsHtml(editWidget);
    }

    const showLegend = editWidget?.showLegend !== false; // default true

    return `
        <div class="mb-3">
            <label class="form-label">Variables</label>
            <select class="form-control" id="widgetVariables" multiple="multiple" style="width: 100%;"></select>
            <small class="form-text text-muted">Select variables, then configure each below</small>
        </div>
        <div id="variableSettingsContainer">${varSettingsHtml}</div>
        <div class="row mb-3">
            <div class="col-6">
                <label class="form-label">Y Axis Label</label>
                <input type="text" class="form-control" id="widgetYLabel" value="${editWidget?.yLabel || 'Value'}" placeholder="Value">
            </div>
            <div class="col-6">
                <label class="form-label">Show Legend</label>
                <select class="form-select" id="widgetShowLegend">
                    <option value="true" ${showLegend ? 'selected' : ''}>Yes</option>
                    <option value="false" ${!showLegend ? 'selected' : ''}>No</option>
                </select>
            </div>
        </div>
        <div class="alert alert-info mb-0">
            <small>
                <strong>Note:</strong> X-axis time is calculated from Scope Control settings (Time factor × 1/Frequency).
                Use the Scope Control widget to adjust sampling parameters.
            </small>
        </div>
    `;
}

function buildPlotScopeVariableSettingsHtml(widget) {
    if (!widget?.variables || widget.variables.length === 0) return '';

    let html = '<label class="form-label mt-3">Variable Settings</label>';
    widget.variables.forEach((varName, idx) => {
        const settings = widget.varSettings?.[varName] || {};
        const color = settings.color || plotScopeDefaultColors[idx % plotScopeDefaultColors.length];
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

function updatePlotScopeVariableSettingsUI() {
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
                color: colorEl?.value || plotScopeDefaultColors[idx % plotScopeDefaultColors.length],
                gain: parseFloat(gainEl?.value) || 1,
                offset: parseFloat(offsetEl?.value) || 0
            };
        } else {
            tempWidget.varSettings[varName] = {
                color: plotScopeDefaultColors[idx % plotScopeDefaultColors.length],
                gain: 1,
                offset: 0
            };
        }
    });

    container.innerHTML = buildPlotScopeVariableSettingsHtml(tempWidget);
}

function savePlotScopeConfig(widget) {
    widget.variables = $('#widgetVariables').val() || [];
    if (widget.variables.length === 0) {
        alert('Please select at least one variable');
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
            color: colorEl?.value || plotScopeDefaultColors[idx % plotScopeDefaultColors.length],
            gain: parseFloat(gainEl?.value) || 1,
            offset: parseFloat(offsetEl?.value) || 0
        };
    });

    widget.yLabel = document.getElementById('widgetYLabel').value || 'Value';
    widget.showLegend = document.getElementById('widgetShowLegend').value === 'true';

    // Register new variables with scope view
    if (scopeSocket && scopeSocket.connected) {
        const currentScopeVars = window.scopeVariablesList || [];
        widget.variables.forEach(v => {
            // Only add if not already in scope view
            if (!currentScopeVars.includes(v)) {
                scopeSocket.emit('add_scope_var', { var: v });
            }
        });
    }

    return true;
}

function afterRenderPlotScopeWidget(widget) {
    setTimeout(() => {
        const plotCanvas = document.getElementById(`dashboard-plot-${widget.id}`);
        if (plotCanvas && typeof Chart !== 'undefined') {
            renderDashboardPlot(widget, plotCanvas);
        }
    }, 100);
}

function refreshPlotScopeWidget(widget, widgetEl) {
    const chart = dashboardCharts[widget.id];
    if (!chart) {
        afterRenderPlotScopeWidget(widget);
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
        // Update X-axis labels with time values
        const maxLen = Math.max(0, ...widget.variables.map(v => (widget.data[v]?.length || 0)));
        const timeData = generateTimeLabels(maxLen);
        chart.data.labels = timeData.labels;
        // Update X-axis title with unit
        if (chart.options.scales.x) {
            chart.options.scales.x.title.text = `Time (${timeData.unit})`;
        }
    }
    chart.update('none');
}

// Generate time labels based on scope control settings
// Returns { labels: number[], unit: string }
function generateTimeLabels(numSamples) {
    // Get sample time and frequency from scope control widget
    const scopeControlWidget = dashboardWidgets.find(w => w.type === 'scope_control');
    const sampleTime = scopeControlWidget?.sampleTime !== undefined ? scopeControlWidget.sampleTime : 1;
    const sampleFreq = scopeControlWidget?.sampleFreq || 20; // in KHz

    // Calculate time per sample: (1 / freq_Hz) * sampleTime
    // sampleTime is user-facing: 1 = every sample, 2 = every 2nd sample, etc.
    // freq is in KHz, so freq_Hz = sampleFreq * 1000
    const timePerSampleUs = (1 / (sampleFreq * 1000)) * sampleTime * 1000000; // in microseconds
    const totalTimeUs = (numSamples - 1) * timePerSampleUs;

    // Determine best unit based on total time
    let unit, divisor;
    if (totalTimeUs >= 1000000) {
        unit = 's';
        divisor = 1000000;
    } else if (totalTimeUs >= 1000) {
        unit = 'ms';
        divisor = 1000;
    } else {
        unit = 'µs';
        divisor = 1;
    }

    const labels = [];
    for (let i = 0; i < numSamples; i++) {
        const timeUs = i * timePerSampleUs;
        labels.push(parseFloat((timeUs / divisor).toFixed(1)));
    }

    return { labels, unit };
}

// Initialize Select2 for variables
function initPlotScopeSelect2(editWidget) {
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
        updatePlotScopeVariableSettingsUI();
    });
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.plot_scope = {
    icon: 'show_chart',
    create: createPlotScopeWidget,
    getConfig: getPlotScopeConfig,
    saveConfig: savePlotScopeConfig,
    afterRender: afterRenderPlotScopeWidget,
    refresh: refreshPlotScopeWidget,
    initSelect2: initPlotScopeSelect2,
    requiresVariable: false,
    requiresMultipleVariables: true,
    supportsGainOffset: false
};
