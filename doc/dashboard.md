# Dashboards

Dashboards show variables of the target in gauges, graphs, LCD displays, progress bars and sliders. They are
built in the **Dashboard Creator** and used in the **Dashboard** tab.

## Dashboard tab

The tab loads a saved dashboard (`.dash.json`) and runs it live: **Open Dashboard...** loads a file,
**Reload** loads it again (for example after saving it in the Creator), **Stop / Run** pauses the updates.
The last file is remembered. A slider on the dashboard writes its variable when you move it.

## Dashboard Creator

Open it with the **Dashboard Creator...** button in the **Setup** tab. It is a separate window: drag widgets onto
a canvas, arrange them, set their properties and save the dashboard with **File > Save**. Press **F5** to try
it out in a run window.

## Connecting ELF variables to widgets

All widgets get their data from variables of the ELF file; there are no signal generators.

1. Connect to the target in the **Setup** tab, so the variables of the ELF file are known.
2. Select a widget in the Dashboard Creator. Gauges, LCD displays, progress bars, graphs (one source per
   series, or X and Y) and sliders have a *Data source* property.
3. Click **...** next to it and pick a variable (or an SFR) in the search dialog. **x** removes it again.
4. Press **F5**. The variables are read from the target in a background thread and shown in real units.

A **slider** also writes: moving it writes its value to the variable, and while it is not being moved it
follows the variable. Set its *Minimum*, *Maximum* and *Step* to the range of the variable.

A widget without a variable, or a variable that cannot be read, shows `0`. 
