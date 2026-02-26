/**
 * Plot Scope Widget - Triggered oscilloscope-style plot using Chart.js
 * 
 * Features:
 * - Multiple variables on one plot
 * - Triggered data capture (replaces entire buffer on update)
 * - Auto-scaling
 * - Color-coded traces
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
            <small class="form-text text-muted">Search and select one or more variables</small>
        </div>
        <div class="mb-3">
            <label class="form-label">X Axis Label</label>
            <input type="text" class="form-control" id="widgetXLabel" value="${editWidget?.xLabel || 'Sample'}" placeholder="Sample">
        </div>
        <div class="mb-3">
            <label class="form-label">Y Axis Label</label>
            <input type="text" class="form-control" id="widgetYLabel" value="${editWidget?.yLabel || 'Value'}" placeholder="Value">
        </div>
        <hr>
        <h6>Trigger Configuration</h6>
        <div class="mb-3">
            <label class="form-label">Trigger Variable</label>
            <select class="form-select" id="widgetTriggerVar">
                <option value="">Select after adding variables</option>
            </select>
            <small class="form-text text-muted">Select which variable to trigger on</small>
        </div>
        <div class="mb-3">
            <label class="form-label">Trigger Edge</label>
            <div class="btn-group w-100" role="group">
                <input type="radio" class="btn-check" name="triggerEdge" id="triggerEdgeRising" value="rising" ${!editWidget?.triggerEdge || editWidget?.triggerEdge === 'rising' ? 'checked' : ''}>
                <label class="btn btn-outline-primary" for="triggerEdgeRising">Rising</label>
                <input type="radio" class="btn-check" name="triggerEdge" id="triggerEdgeFalling" value="falling" ${editWidget?.triggerEdge === 'falling' ? 'checked' : ''}>
                <label class="btn btn-outline-primary" for="triggerEdgeFalling">Falling</label>
            </div>
        </div>
        <div class="mb-3">
            <label class="form-label">Trigger Level</label>
            <input type="number" class="form-control" id="widgetTriggerLevel" step="any" value="${editWidget?.triggerLevel !== undefined ? editWidget.triggerLevel : 0}">
        </div>
    `;
}

function savePlotScopeConfig(widget) {
    widget.variables = $('#widgetVariables').val() || [];
    if (widget.variables.length === 0) {
        alert('Please enter at least one variable name');
        return false;
    }
    widget.data = {}; // Object to store data for each variable
    widget.variables.forEach(v => widget.data[v] = []);
    widget.xLabel = document.getElementById('widgetXLabel').value || 'Sample';
    widget.yLabel = document.getElementById('widgetYLabel').value || 'Value';
    // Trigger configuration
    widget.triggerVar = document.getElementById('widgetTriggerVar').value || '';
    widget.triggerEdge = document.querySelector('input[name="triggerEdge"]:checked')?.value || 'rising';
    widget.triggerLevel = parseFloat(document.getElementById('widgetTriggerLevel').value) || 0;
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

// Update trigger variable dropdown based on selected variables
function updateTriggerVarOptions(selectedVars, currentTriggerVar) {
    const triggerSelect = document.getElementById('widgetTriggerVar');
    if (!triggerSelect) return;

    triggerSelect.innerHTML = '<option value="">None (free running)</option>';
    if (selectedVars && selectedVars.length > 0) {
        selectedVars.forEach(v => {
            const option = document.createElement('option');
            option.value = v;
            option.textContent = v;
            if (v === currentTriggerVar) option.selected = true;
            triggerSelect.appendChild(option);
        });
    }
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

    // Update trigger variable options when variables change
    $('#widgetVariables').on('change', function() {
        const selectedVars = $(this).val() || [];
        updateTriggerVarOptions(selectedVars, editWidget?.triggerVar);
    });

    // Pre-populate existing variables when editing
    if (editWidget?.variables) {
        editWidget.variables.forEach(v => {
            $('#widgetVariables').append(new Option(v, v, true, true));
        });
        $('#widgetVariables').trigger('change');
        // Set trigger variable after populating
        updateTriggerVarOptions(editWidget.variables, editWidget.triggerVar);
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
