/**
 * Plot Logger Widget - Scrolling time-series plot using Chart.js
 * 
 * Features:
 * - Multiple variables on one plot
 * - Configurable max data points (scrolling window)
 * - Auto-scaling
 * - Color-coded traces
 */

function createPlotLoggerWidget(widget) {
    return `
        <canvas class="plot-container" id="dashboard-plot-${widget.id}"></canvas>
    `;
}

function getPlotLoggerConfig(editWidget) {
    return `
        <div class="mb-3">
            <label class="form-label">Variables</label>
            <select class="form-control" id="widgetVariables" multiple="multiple" style="width: 100%;"></select>
            <small class="form-text text-muted">Search and select one or more variables</small>
        </div>
        <div class="mb-3">
            <label class="form-label">Max Data Points</label>
            <input type="number" class="form-control" id="widgetMaxPoints" value="${editWidget?.maxPoints || 50}">
        </div>
        <div class="mb-3">
            <label class="form-label">X Axis Label</label>
            <input type="text" class="form-control" id="widgetXLabel" value="${editWidget?.xLabel || 'Sample'}" placeholder="Sample">
        </div>
        <div class="mb-3">
            <label class="form-label">Y Axis Label</label>
            <input type="text" class="form-control" id="widgetYLabel" value="${editWidget?.yLabel || 'Value'}" placeholder="Value">
        </div>
    `;
}

function savePlotLoggerConfig(widget) {
    widget.variables = $('#widgetVariables').val() || [];
    if (widget.variables.length === 0) {
        alert('Please enter at least one variable name');
        return false;
    }
    widget.data = {}; // Object to store data for each variable
    widget.variables.forEach(v => widget.data[v] = []);
    widget.maxPoints = parseInt(document.getElementById('widgetMaxPoints').value);
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
                chart.data.datasets[idx].data = widget.data[varName] || [];
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
