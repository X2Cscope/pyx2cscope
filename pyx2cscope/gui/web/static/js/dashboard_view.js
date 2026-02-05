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
        });

        dashboardSocket.on('variable_update', (data) => {
            console.log('Variable update:', data);
            updateDashboardWidgetValue(data.variable, data.value);
        });

        dashboardSocket.on('initial_data', (data) => {
            console.log('Received initial data:', data);
            updateDashboardWidgetsFromData(data);
        });
    }

    // Set up file input for import
    document.getElementById('dashboardFileInput').addEventListener('change', handleDashboardFileImport);
}

function toggleDashboardMode() {
    isDashboardEditMode = !isDashboardEditMode;
    const btn = document.getElementById('dashboardModeBtn');
    const palette = document.getElementById('widgetPalette');
    const canvasCol = document.getElementById('dashboardCanvasCol');
    const canvas = document.getElementById('dashboardCanvas');

    if (isDashboardEditMode) {
        btn.innerHTML = '<span class="material-icons md-18">edit</span> Edit Mode';
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-success');
        palette.style.display = 'block';
        canvasCol.classList.remove('col-12');
        canvasCol.classList.add('col-12', 'col-md-9', 'col-lg-10');
        canvas.classList.remove('view-mode');
        canvas.classList.add('edit-mode');
    } else {
        btn.innerHTML = '<span class="material-icons md-18">visibility</span> View Mode';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-secondary');
        palette.style.display = 'none';
        canvasCol.classList.remove('col-md-9', 'col-lg-10');
        canvasCol.classList.add('col-12');
        canvas.classList.remove('edit-mode');
        canvas.classList.add('view-mode');
    }

    // Update all widgets
    dashboardWidgets.forEach(w => renderDashboardWidget(w));
}

function showWidgetConfig(type) {
    currentWidgetType = type;
    const extraConfig = document.getElementById('widgetExtraConfig');
    extraConfig.innerHTML = '';

    // Add type-specific configuration
    if (type === 'slider') {
        extraConfig.innerHTML = `
            <div class="mb-3">
                <label class="form-label">Min Value</label>
                <input type="number" class="form-control" id="widgetMinValue" value="0">
            </div>
            <div class="mb-3">
                <label class="form-label">Max Value</label>
                <input type="number" class="form-control" id="widgetMaxValue" value="100">
            </div>
            <div class="mb-3">
                <label class="form-label">Step</label>
                <input type="number" class="form-control" id="widgetStepValue" value="1">
            </div>
        `;
    } else if (type === 'gauge') {
        extraConfig.innerHTML = `
            <div class="mb-3">
                <label class="form-label">Min Value</label>
                <input type="number" class="form-control" id="widgetMinValue" value="0">
            </div>
            <div class="mb-3">
                <label class="form-label">Max Value</label>
                <input type="number" class="form-control" id="widgetMaxValue" value="100">
            </div>
        `;
    } else if (type === 'plot') {
        extraConfig.innerHTML = `
            <div class="mb-3">
                <label class="form-label">Max Data Points</label>
                <input type="number" class="form-control" id="widgetMaxPoints" value="50">
            </div>
        `;
    }

    const modal = new bootstrap.Modal(document.getElementById('widgetConfigModal'));
    modal.show();
}

function addDashboardWidget() {
    const varName = document.getElementById('widgetVarName').value.trim();
    if (!varName) {
        alert('Please enter a variable name');
        return;
    }

    const widget = {
        id: widgetIdCounter++,
        type: currentWidgetType,
        variable: varName,
        x: 50,
        y: 50,
        value: currentWidgetType === 'text' ? '' : 0
    };

    // Add type-specific properties
    if (currentWidgetType === 'slider') {
        widget.min = parseFloat(document.getElementById('widgetMinValue').value);
        widget.max = parseFloat(document.getElementById('widgetMaxValue').value);
        widget.step = parseFloat(document.getElementById('widgetStepValue').value);
    } else if (currentWidgetType === 'gauge') {
        widget.min = parseFloat(document.getElementById('widgetMinValue').value);
        widget.max = parseFloat(document.getElementById('widgetMaxValue').value);
    } else if (currentWidgetType === 'plot') {
        widget.maxPoints = parseInt(document.getElementById('widgetMaxPoints').value);
        widget.data = [];
    }

    dashboardWidgets.push(widget);
    renderDashboardWidget(widget);

    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('widgetConfigModal'));
    modal.hide();
    document.getElementById('widgetVarName').value = '';
}

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
        gauge: '<span class="material-icons md-18">speed</span>',
        plot: '<span class="material-icons md-18">show_chart</span>'
    };

    const header = `
        <div class="widget-header">
            <span class="widget-title">${typeIcons[widget.type]} ${widget.variable}</span>
            <div class="widget-controls">
                <button class="btn btn-sm btn-danger" onclick="deleteDashboardWidget(${widget.id})">
                    <span class="material-icons md-18">delete</span>
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
            content = `
                ${header}
                <button class="btn btn-primary" onclick="triggerDashboardButton('${widget.variable}')">
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

        case 'gauge':
            content = `
                ${header}
                <div class="gauge-container" id="dashboard-gauge-${widget.id}"></div>
                </div>
            `;
            setTimeout(() => {
                const gaugeDiv = document.getElementById(`dashboard-gauge-${widget.id}`);
                if (gaugeDiv && typeof Plotly !== 'undefined') {
                    renderDashboardGauge(widget);
                }
            }, 100);
            break;

        case 'plot':
            content = `
                ${header}
                <div class="plot-container" id="dashboard-plot-${widget.id}"></div>
                </div>
            `;
            setTimeout(() => {
                const plotDiv = document.getElementById(`dashboard-plot-${widget.id}`);
                if (plotDiv && typeof Plotly !== 'undefined') {
                    renderDashboardPlot(widget);
                }
            }, 100);
            break;
    }

    widgetEl.innerHTML = content;
}

function renderDashboardGauge(widget) {
    const data = [{
        type: "indicator",
        mode: "gauge+number",
        value: widget.value,
        gauge: {
            axis: { range: [widget.min, widget.max] },
            bar: { color: "#0d6efd" },
            steps: [
                { range: [widget.min, widget.max], color: "#e9ecef" }
            ]
        }
    }];

    const layout = {
        margin: { t: 0, b: 0, l: 20, r: 20 },
        autosize: true
    };

    const config = {
        displayModeBar: false,
        responsive: true
    };

    Plotly.react(`dashboard-gauge-${widget.id}`, data, layout, config);
}

function renderDashboardPlot(widget) {
    if (!widget.data) widget.data = [];

    const plotDiv = document.getElementById(`dashboard-plot-${widget.id}`);
    if (!plotDiv) {
        console.error(`Plot div not found for widget ${widget.id}`);
        return;
    }

    const data = [{
        y: widget.data,
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#0d6efd', width: 2 },
        marker: { size: 4 }
    }];

    const layout = {
        margin: { t: 20, b: 40, l: 50, r: 20 },
        xaxis: { title: 'Time' },
        yaxis: { title: widget.variable },
        autosize: true
    };

    const config = {
        displayModeBar: false,
        responsive: true
    };

    Plotly.react(`dashboard-plot-${widget.id}`, data, layout, config);
}

function updateDashboardVariable(varName, value) {
    const widget = dashboardWidgets.find(w => w.variable === varName);
    if (widget) {
        widget.value = value;

        // Update plot data
        if (widget.type === 'plot') {
            if (!widget.data) widget.data = [];
            widget.data.push(value);
            if (widget.data.length > widget.maxPoints) {
                widget.data.shift();
            }
        }

        renderDashboardWidget(widget);

        // Send to server via Socket.IO or HTTP
        if (dashboardSocket && dashboardSocket.connected) {
            dashboardSocket.emit('widget_interaction', {
                variable: varName,
                value: value
            });
        } else {
            // Fallback to HTTP
            fetch('/dashboard-view/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ variable: varName, value: value })
            });
        }
    }
}

function updateDashboardWidgetValue(varName, value) {
    const widget = dashboardWidgets.find(w => w.variable === varName);
    if (widget) {
        widget.value = value;

        // Update plot data
        if (widget.type === 'plot') {
            if (!widget.data) widget.data = [];
            widget.data.push(value);
            if (widget.data.length > widget.maxPoints) {
                widget.data.shift();
            }
        }

        renderDashboardWidget(widget);
    }
}

function updateDashboardWidgetsFromData(data) {
    for (let varName in data) {
        updateDashboardWidgetValue(varName, data[varName]);
    }
}

function triggerDashboardButton(varName) {
    const timestamp = Date.now();
    updateDashboardVariable(varName, timestamp);
}

function deleteDashboardWidget(id) {
    if (confirm('Delete this widget?')) {
        const index = dashboardWidgets.findIndex(w => w.id === id);
        if (index > -1) {
            dashboardWidgets.splice(index, 1);
            const el = document.getElementById(`dashboard-widget-${id}`);
            if (el) el.remove();
        }
    }
}

function startDashboardDrag(e) {
    if (!isDashboardEditMode) return;

    draggedWidget = e.currentTarget;
    const rect = draggedWidget.getBoundingClientRect();
    const canvas = document.getElementById('dashboardCanvas').getBoundingClientRect();

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
            dashboardWidgets = data.layout;
            widgetIdCounter = Math.max(...dashboardWidgets.map(w => w.id), 0) + 1;
            document.getElementById('dashboardCanvas').innerHTML = '';
            dashboardWidgets.forEach(w => renderDashboardWidget(w));
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
                dashboardWidgets = JSON.parse(event.target.result);
                widgetIdCounter = Math.max(...dashboardWidgets.map(w => w.id), 0) + 1;
                document.getElementById('dashboardCanvas').innerHTML = '';
                dashboardWidgets.forEach(w => renderDashboardWidget(w));
                alert('Layout imported successfully');
            } catch (err) {
                console.error('Import error:', err);
                alert('Error importing layout: Invalid JSON file');
            }
        };
        reader.readAsText(file);
    }
}