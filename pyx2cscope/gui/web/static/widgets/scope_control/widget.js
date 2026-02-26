/**
 * Scope Control Widget - Full scope control panel
 *
 * Features:
 * - Sample/Stop/Burst buttons
 * - Sample time and frequency settings
 * - Trigger configuration (enable, edge, level, delay)
 * - Trigger variable selection
 * - Status indicator
 */

let scopeControlState = 'off'; // 'on', 'off', 'shot'

function handleScopeControlAction(action) {
    if (isDashboardEditMode) return;

    scopeControlState = action;

    // Get current settings from the widget
    const sampleTime = document.getElementById('scopeCtrlSampleTime')?.value || 1;
    const sampleFreq = document.getElementById('scopeCtrlSampleFreq')?.value || 20;

    // Send to scope-view namespace
    if (scopeSocket && scopeSocket.connected) {
        const formData = `triggerAction=${action}&sampleTime=${sampleTime}&sampleFreq=${sampleFreq}`;
        scopeSocket.emit('update_sample_control', formData);
    }

    // Update button states and store values in widget objects
    dashboardWidgets
        .filter(w => w.type === 'scope_control')
        .forEach(w => {
            // Store current values in widget for persistence
            w.sampleTime = parseInt(sampleTime);
            w.sampleFreq = parseInt(sampleFreq);

            const widgetEl = document.getElementById(`dashboard-widget-${w.id}`);
            if (widgetEl) {
                refreshScopeControlWidget(w, widgetEl);
            }
        });
}

function updateScopeControlTrigger(widgetId) {
    if (isDashboardEditMode) return;

    const widget = dashboardWidgets.find(w => w.id === widgetId);
    if (!widget || !scopeSocket || !scopeSocket.connected) return;

    const triggerMode = document.querySelector(`input[name="scopeCtrlTriggerMode-${widgetId}"]:checked`)?.value || '0';
    const triggerEdge = document.querySelector(`input[name="scopeCtrlTriggerEdge-${widgetId}"]:checked`)?.value || '1';
    const triggerLevel = document.getElementById(`scopeCtrlTriggerLevel-${widgetId}`)?.value || 0;
    const triggerDelay = document.getElementById(`scopeCtrlTriggerDelay-${widgetId}`)?.value || 0;
    const triggerVar = document.getElementById(`scopeCtrlTriggerVar-${widgetId}`)?.value || '';

    // Store values in widget for persistence
    widget.triggerMode = triggerMode;
    widget.triggerEdge = triggerEdge;
    widget.triggerLevel = parseFloat(triggerLevel);
    widget.triggerDelay = parseInt(triggerDelay);
    widget.triggerVar = triggerVar;

    // Update trigger variable selection on scope variables
    const scopeVars = window.scopeVariablesList || [];
    if (triggerVar && scopeVars.length > 0) {
        scopeVars.forEach(varName => {
            scopeSocket.emit('update_scope_var', {
                param: varName,
                field: 'trigger',
                value: varName === triggerVar ? '1' : '0'
            });
        });
    }

    // Send trigger control settings (use snake_case to match backend)
    const formData = `trigger_mode=${triggerMode}&trigger_edge=${triggerEdge}&trigger_level=${triggerLevel}&trigger_delay=${triggerDelay}`;
    scopeSocket.emit('update_trigger_control', formData);
}

function updateScopeSampleSettings(widgetId) {
    if (isDashboardEditMode) return;

    const sampleTime = document.getElementById('scopeCtrlSampleTime')?.value || 1;
    const sampleFreq = document.getElementById('scopeCtrlSampleFreq')?.value || 20;

    // Store values in all scope_control widgets for persistence
    dashboardWidgets
        .filter(w => w.type === 'scope_control')
        .forEach(w => {
            w.sampleTime = parseInt(sampleTime);
            w.sampleFreq = parseInt(sampleFreq);
        });

    if (scopeSocket && scopeSocket.connected) {
        const formData = `triggerAction=${scopeControlState}&sampleTime=${sampleTime}&sampleFreq=${sampleFreq}`;
        scopeSocket.emit('update_sample_control', formData);
    }
}

function createScopeControlWidget(widget) {
    const isRunning = scopeControlState === 'on';
    const isBurst = scopeControlState === 'shot';
    const isStopped = scopeControlState === 'off';

    const triggerMode = widget.triggerMode || '0';
    const triggerEdge = widget.triggerEdge || '1';
    const triggerLevel = widget.triggerLevel || 0;
    const triggerDelay = widget.triggerDelay || 0;
    const triggerVar = widget.triggerVar || '';
    const sampleTime = widget.sampleTime || 1;
    const sampleFreq = widget.sampleFreq || 20;

    // Build trigger variable options from scope-view variables
    let triggerVarOptions = '<option value="">None</option>';
    const scopeVars = window.scopeVariablesList || [];
    scopeVars.forEach(v => {
        triggerVarOptions += `<option value="${v}" ${v === triggerVar ? 'selected' : ''}>${v}</option>`;
    });

    return `
        <div class="scope-control-widget">
            <!-- Sample Control -->
            <div class="mb-2">
                <small class="text-muted fw-bold">Sample Control</small>
                <div class="btn-group w-100 btn-group-sm mt-1" role="group">
                    <button class="btn btn-${isRunning ? 'success' : 'outline-success'}"
                            onclick="handleScopeControlAction('on')"
                            ${isDashboardEditMode ? 'disabled' : ''}>
                        <span class="material-icons md-18">play_arrow</span>
                    </button>
                    <button class="btn btn-${isStopped ? 'danger' : 'outline-danger'}"
                            onclick="handleScopeControlAction('off')"
                            ${isDashboardEditMode ? 'disabled' : ''}>
                        <span class="material-icons md-18">stop</span>
                    </button>
                    <button class="btn btn-${isBurst ? 'primary' : 'outline-primary'}"
                            onclick="handleScopeControlAction('shot')"
                            ${isDashboardEditMode ? 'disabled' : ''}>
                        <span class="material-icons md-18">flash_on</span>
                    </button>
                </div>
            </div>

            <div class="row g-1 mb-2">
                <div class="col-6">
                    <label class="form-label mb-0" style="font-size: 0.75rem;">Time</label>
                    <input type="number" class="form-control form-control-sm" id="scopeCtrlSampleTime"
                           value="${sampleTime}" min="1" max="30"
                           onchange="updateScopeSampleSettings(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                </div>
                <div class="col-6">
                    <label class="form-label mb-0" style="font-size: 0.75rem;">Freq (KHz)</label>
                    <input type="number" class="form-control form-control-sm" id="scopeCtrlSampleFreq"
                           value="${sampleFreq}" min="1" max="30"
                           onchange="updateScopeSampleSettings(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                </div>
            </div>

            <!-- Trigger Control -->
            <div class="mb-2">
                <small class="text-muted fw-bold">Trigger Control</small>
                <div class="btn-group w-100 btn-group-sm mt-1" role="group">
                    <input type="radio" class="btn-check" name="scopeCtrlTriggerMode-${widget.id}"
                           id="scopeCtrlTriggerEnable-${widget.id}" value="1"
                           ${triggerMode === '1' ? 'checked' : ''}
                           onchange="updateScopeControlTrigger(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                    <label class="btn btn-outline-success" for="scopeCtrlTriggerEnable-${widget.id}">Enable</label>
                    <input type="radio" class="btn-check" name="scopeCtrlTriggerMode-${widget.id}"
                           id="scopeCtrlTriggerDisable-${widget.id}" value="0"
                           ${triggerMode === '0' ? 'checked' : ''}
                           onchange="updateScopeControlTrigger(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                    <label class="btn btn-outline-danger" for="scopeCtrlTriggerDisable-${widget.id}">Disable</label>
                </div>
            </div>

            <div class="mb-2">
                <label class="form-label mb-0" style="font-size: 0.75rem;">Trigger Variable</label>
                <select class="form-select form-select-sm" id="scopeCtrlTriggerVar-${widget.id}"
                        onchange="updateScopeControlTrigger(${widget.id})"
                        ${isDashboardEditMode ? 'disabled' : ''}>
                    ${triggerVarOptions}
                </select>
            </div>

            <div class="mb-2">
                <small class="text-muted">Edge</small>
                <div class="btn-group w-100 btn-group-sm" role="group">
                    <input type="radio" class="btn-check" name="scopeCtrlTriggerEdge-${widget.id}"
                           id="scopeCtrlEdgeRising-${widget.id}" value="1"
                           ${triggerEdge === '1' ? 'checked' : ''}
                           onchange="updateScopeControlTrigger(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                    <label class="btn btn-outline-primary" for="scopeCtrlEdgeRising-${widget.id}">Rising</label>
                    <input type="radio" class="btn-check" name="scopeCtrlTriggerEdge-${widget.id}"
                           id="scopeCtrlEdgeFalling-${widget.id}" value="0"
                           ${triggerEdge === '0' ? 'checked' : ''}
                           onchange="updateScopeControlTrigger(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                    <label class="btn btn-outline-primary" for="scopeCtrlEdgeFalling-${widget.id}">Falling</label>
                </div>
            </div>

            <div class="row g-1 mb-2">
                <div class="col-6">
                    <label class="form-label mb-0" style="font-size: 0.75rem;">Level</label>
                    <input type="number" class="form-control form-control-sm" id="scopeCtrlTriggerLevel-${widget.id}"
                           value="${triggerLevel}" step="1"
                           onchange="updateScopeControlTrigger(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                </div>
                <div class="col-6">
                    <label class="form-label mb-0" style="font-size: 0.75rem;">Delay (%)</label>
                    <input type="number" class="form-control form-control-sm" id="scopeCtrlTriggerDelay-${widget.id}"
                           value="${triggerDelay}" min="-50" max="50" step="10"
                           onchange="updateScopeControlTrigger(${widget.id})"
                           ${isDashboardEditMode ? 'disabled' : ''}>
                </div>
            </div>

            <!-- Status -->
            <div class="text-center">
                <small class="text-muted">
                    <span class="badge ${isRunning ? 'bg-success' : isBurst ? 'bg-primary' : 'bg-secondary'}">
                        ${isRunning ? 'Running' : isBurst ? 'Burst' : 'Stopped'}
                    </span>
                </small>
            </div>
        </div>
    `;
}

function getScopeControlConfig(editWidget) {
    return `
        <div class="alert alert-info mb-0">
            <small>
                <strong>Note:</strong> This widget controls scope sampling and displays variables
                configured in the Scope View page. Add variables there first, then use this
                widget to control sampling and select which variable to trigger on.
            </small>
        </div>
    `;
}

function saveScopeControlConfig(widget) {
    widget.sampleTime = widget.sampleTime || 1;
    widget.sampleFreq = widget.sampleFreq || 20;
    widget.triggerMode = widget.triggerMode || '0';
    widget.triggerEdge = widget.triggerEdge || '1';
    widget.triggerLevel = widget.triggerLevel || 0;
    widget.triggerDelay = widget.triggerDelay || 0;
    widget.triggerVar = widget.triggerVar || '';
    return true;
}

function refreshScopeControlWidget(widget, widgetEl) {
    // Update button states only, preserve input values
    const btns = widgetEl.querySelectorAll('.btn-group button');
    if (btns.length >= 3) {
        const isRunning = scopeControlState === 'on';
        const isStopped = scopeControlState === 'off';
        const isBurst = scopeControlState === 'shot';

        btns[0].className = `btn btn-${isRunning ? 'success' : 'outline-success'}`;
        btns[1].className = `btn btn-${isStopped ? 'danger' : 'outline-danger'}`;
        btns[2].className = `btn btn-${isBurst ? 'primary' : 'outline-primary'}`;
    }

    // Update status badge
    const badge = widgetEl.querySelector('.badge');
    if (badge) {
        const isRunning = scopeControlState === 'on';
        const isBurst = scopeControlState === 'shot';
        badge.className = `badge ${isRunning ? 'bg-success' : isBurst ? 'bg-primary' : 'bg-secondary'}`;
        badge.textContent = isRunning ? 'Running' : isBurst ? 'Burst' : 'Stopped';
    }
}

// Register widget type
if (typeof window.dashboardWidgetTypes === 'undefined') {
    window.dashboardWidgetTypes = {};
}

window.dashboardWidgetTypes.scope_control = {
    icon: 'settings_remote',
    create: createScopeControlWidget,
    getConfig: getScopeControlConfig,
    saveConfig: saveScopeControlConfig,
    refresh: refreshScopeControlWidget,
    requiresVariable: false,
    supportsGainOffset: false
};
