import logging

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from pyx2cscope.xc2scope import X2CScope

# Set up logging This sets up the logging system to capture information and errors, storing them in a log file with
# the same name as this script.
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# X2C Scope Setup Initialize the X2C Scope for real-time data acquisition from a microcontroller. Specify the COM
# port and path to the ELF file.
elf_file = (
    r"C:\_DESKTOP\_Projects\Motorbench_Projects\motorbench_FOC_PLL_PIC33CK256mp508_MCLV2"
    r"\ZSMT_dsPIC33CK_MCLV_48_300.X\dist\default\production\ZSMT_dsPIC33CK_MCLV_48_300_Future.X.production.elf"
)
x2cScope = X2CScope(port="COM16", elf_file=elf_file)

# Initialize Variables for Monitoring
# Define the variables that will be monitored and visualized in real-time.
variables = [
    x2cScope.get_variable("motor.idq.q"),
    x2cScope.get_variable("motor.vabc.a"),
    x2cScope.get_variable("motor.vabc.b"),
    x2cScope.get_variable("motor.vabc.c"),
    x2cScope.get_variable("motor.apiData.velocityMeasured"),
]

# Adding variables to scope's monitoring channels
for variable in variables:
    x2cScope.add_scope_channel(variable)

# Initialize Data Storage
# A dictionary to store the incoming data for each variable.
data_storage = {var: [] for var in variables}

# Window Size for Live Plot
# Specifies the number of data points to display in the live plot at any given time.
window_size = 250


def update_plot(frame):
    """
    Update Plot Function
    This function is called periodically by the animation framework.
    It fetches new data from the scope and updates the live plot.
    """
    try:
        # Check if new scope data is available
        if x2cScope.is_scope_data_ready():
            logging.info("Scope data is ready.")

            # Process and store new data
            scope_data = x2cScope.get_scope_channel_data(valid_data=False)
            for variable, data in scope_data.items():
                variable_name = str(variable)  # Convert variable to a string identifier
                data_storage[variable_name].extend(data)

            # Request new data from the scope
            x2cScope.request_scope_data()

    except Exception as e:
        logging.error(f"Error in update_plot: {str(e)}")

    # Clear the current plot for fresh drawing
    plt.clf()

    # Determine the current maximum index for x-axis
    current_index = max(len(data) for data in data_storage.values())

    # Plot data for each channel within the moving window
    for variable_name, data in data_storage.items():
        if data:
            start_index = max(0, current_index - window_size)
            end_index = current_index
            plt.plot(
                range(start_index, end_index), data[-window_size:], label=variable_name
            )

    # Adjust plot settings for the moving window effect
    plt.xlim(current_index - window_size, current_index)
    plt.xlabel("Data Index")
    plt.ylabel("Value")
    plt.title("Live Plot of Byte Data")
    plt.legend(loc="upper right")
    plt.draw()


# Live Plot Setup
# Initialize interactive mode for live updating and create a figure for the plot.
plt.ion()
fig = plt.figure()
ani = FuncAnimation(fig, update_plot, interval=100, cache_frame_data=False)

# Display the live plot
plt.show(block=True)
