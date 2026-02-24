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

// List of widgets to load
const widgetsList = [
    'button',
    'slider',
    'gauge',
    'number',
    'text',
    'label',
    'plot_logger',
    'plot_scope'
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
