/**
 * Plot Scope Widget - Triggered oscilloscope-style plot using Chart.js
 *
 * Features:
 * - Multiple variables on one plot
 * - Triggered data capture (replaces entire buffer on update)
 * - Auto-scaling
 * - Color-coded traces
 *
 * Note: Trigger configuration is managed in Scope View.
 * Use Scope Control widget to start/stop sampling.
 */

function createPlotScopeWidget(widget) {
    return `
        <canvas class="plot-container" id="dashboard-plot-${widget.id}"></canvas>
    `;
}

function getPlotScopeConfig(editWidget) {
    return `
        <div class="mb-3">
            <label class="form-label">Variables</label>
            <select class="form-control" id="widgetVariables" multiple="multiple" style="width: 100%;"></select>
            <small class="form-text text-muted">Select variables configured in Scope View</small>
        </div>
        <div class="mb-3">
            <label class="form-label">X Axis Label</label>
            <input type="text" class="form-control" id="widgetXLabel" value="${editWidget?.xLabel || 'Sample'}" placeholder="Sample">
        </div>
        <div class="mb-3">
            <label class="form-label">Y Axis Label</label>
            <input type="text" class="form-control" id="widgetYLabel" value="${editWidget?.yLabel || 'Value'}" placeholder="Value">
        </div>
        <div class="alert alert-info mb-0">
            <small>
                <strong>Note:</strong> Configure trigger settings in Scope View.
                Use the Scope Control widget to start/stop sampling.
            </small>
        </div>
    `;
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

    widget.xLabel = document.getElementById('widgetXLabel').value || 'Sample';
    widget.yLabel = document.getElementById('widgetYLabel').value || 'Value';

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
                chart.data.datasets[idx].data = widget.data[varName] || [];
            }
        });
        const maxLen = Math.max(0, ...widget.variables.map(v => (widget.data[v]?.length || 0)));
        chart.data.labels = Array.from({length: maxLen}, (_, i) => i + 1);
    }
    chart.update('none');
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
