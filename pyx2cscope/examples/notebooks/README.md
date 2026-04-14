# pyX2Cscope — Jupyter Notebook Examples

Interactive notebooks for exploring and controlling Microchip embedded targets using pyX2Cscope.

## Available Notebooks

| Notebook | Description |
|---|---|
| [mcaf_hil_example.ipynb](mcaf_hil_example.ipynb) | Hardware-in-the-Loop test with MCAF motor firmware: ramp speed, capture phase currents, calculate RMS values |

---

## How to Run

### 1. Install pyX2Cscope

If you haven't already:

```bash
pip install pyx2cscope
```

### 2. Install Jupyter

```bash
pip install jupyterlab
```

### 3. Launch Jupyter

From this folder:

```bash
jupyter lab
```

A browser window will open. Click the notebook you want to run.

### 4. Configure the notebook

Each notebook has a **Configuration** cell near the top. At minimum you need to set:

- `SERIAL_PORT` — the COM port your board is connected to (e.g. `"COM3"` on Windows, `"/dev/ttyUSB0"` on Linux/macOS). Set to `"AUTO"` to let pyX2Cscope detect it automatically.
- `ELF_FILE` — the full path to the `.elf` file matching the firmware flashed on your board.

### 5. Run the cells

Use **Shift+Enter** to run one cell at a time, or **Run → Run All Cells** from the menu to execute the full notebook.

> **Tip:** Always run the final cleanup cell before closing the notebook. It stops the motor and restores the hardware UI.

---

## Requirements

- Python 3.10 or newer
- pyX2Cscope (`pip install pyx2cscope`)
- `notebook` or `jupyterlab`
- A Microchip board running compatible firmware, connected via USB/serial
- The matching `.elf` file for the firmware on your board
