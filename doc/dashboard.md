# Dashboard tab

The **Dashboard** tab of the Qt GUI is a visual editor for dashboards: drag widgets (gauges, Y-T and X-Y
graphs, LCD displays, progress bars, sliders, labels, a data logger and more) onto a canvas, arrange them and
press **F5** (Run) to open the dashboard in its own window.

## Connecting ELF variables to widgets

All widgets get their data from variables of the ELF file; there are no signal generators.

1. Connect to the target in the **Setup** tab, so the variables of the ELF file are known.
2. Select a widget in the Dashboard tab. Gauges, LCD displays, progress bars, graphs (one source per
   series, or X and Y) and sliders have a *Data source* property.
3. Click **...** next to it and pick a variable (or an SFR) in the search dialog. **x** removes it again.
4. Press **F5**. The variables are read from the target in a background thread and shown in real units.

A **slider** also writes: moving it writes its value to the variable, and while it is not being moved it
follows the variable. Set its *Minimum*, *Maximum* and *Step* to the range of the variable.

A widget without a variable, or a variable that cannot be read, shows `0`. Dashboards are saved as
`.dash.json` files with the Dashboard tab's own **File** menu.
