/**
 * Widget Loader - Dynamically loads modular widget definitions
 *
 * Add this script BEFORE your existing dashboard_view.js
 *
 * This loads widget files from /static/widgets/ folder structure:
 * widgets/
 *   button/
 *     widget.js
 *   slider/
 *     widget.js
 *   ...etc
 */

// Global registry for widget types
window.dashboardWidgetTypes = {};

// Track last update time per widget for update rate control
window.widgetLastUpdateTime = {};

/**
 * Update Rate Configuration Helper
 *
 * Update rate values:
 * - 0: Off (no automatic updates)
 * - > 0: Interval in seconds
 */

// Get update rate configuration HTML for widget config modal
// defaultRate: used when editWidget has no updateRate saved yet (0 = off, 1/2/5/... = interval)
function getUpdateRateConfigHTML(editWidget, defaultRate) {
    const fallback = defaultRate !== undefined ? defaultRate : 1;
    const currentRate = editWidget?.updateRate !== undefined ? editWidget.updateRate : fallback;
    return `
        <div class="mb-3">
            <label class="form-label">Update Rate</label>
            <select class="form-select" id="widgetUpdateRate">
                <option value="1" ${currentRate === 1 ? 'selected' : ''}>1 second</option>
                <option value="2" ${currentRate === 2 ? 'selected' : ''}>2 seconds</option>
                <option value="5" ${currentRate === 5 ? 'selected' : ''}>5 seconds</option>
                <option value="10" ${currentRate === 10 ? 'selected' : ''}>10 seconds</option>
                <option value="30" ${currentRate === 30 ? 'selected' : ''}>30 seconds</option>
                <option value="0" ${currentRate === 0 ? 'selected' : ''}>Off</option>
            </select>
            <div class="form-text">How often to read the variable value</div>
        </div>
    `;
}

// Save update rate from widget config modal
function saveUpdateRateConfig(widget) {
    const rateValue = document.getElementById('widgetUpdateRate')?.value;
    if (rateValue !== undefined) {
        widget.updateRate = parseFloat(rateValue);
    }
}

// Check if widget should be updated based on its update rate
function shouldUpdateWidget(widget) {
    // Update rate: 0 = off, > 0 = interval in seconds
    const updateRate = widget.updateRate !== undefined ? widget.updateRate : 1;

    // Off - never auto-update
    if (updateRate === 0) {
        return false;
    }

    // Interval-based update
    const now = Date.now();
    const lastUpdate = window.widgetLastUpdateTime[widget.id] || 0;
    const intervalMs = updateRate * 1000;

    if (now - lastUpdate >= intervalMs) {
        window.widgetLastUpdateTime[widget.id] = now;
        return true;
    }

    return false;
}

// Make helpers available globally
window.getUpdateRateConfigHTML = getUpdateRateConfigHTML;
window.saveUpdateRateConfig = saveUpdateRateConfig;
window.shouldUpdateWidget = shouldUpdateWidget;

// List of widgets to load
const widgetsList = [
    'button',
    'switch',
    'slider',
    'gauge',
    'number',
    'text',
    'label',
    'plot_logger',
    'plot_scope',
    'scope_control'
];

// Load all widgets on page load
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Loading modular widgets...');
    
    for (const widgetType of widgetsList) {
        try {
            // Load widget.js file
            await loadScript(`/static/widgets/${widgetType}/widget.js`);
            console.log(`Loaded widget: ${widgetType}`);
        } catch (error) {
            console.error(`Failed to load widget ${widgetType}:`, error);
        }
    }
    
    console.log('All widgets loaded:', Object.keys(window.dashboardWidgetTypes));
});

// Helper function to load script
function loadScript(url) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}
