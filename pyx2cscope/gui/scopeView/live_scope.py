"""
This example can be used to visualize live scope data, for the predefined variables.
"""


import logging
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from xc2scope import X2CScope

# logging setup
logging.basicConfig(
    level=logging.INFO,
    filename=__file__ + ".log",
)

# Set up X2C Scope
elf_file = "C:\\_DESKTOP\\_Projects\\Motorbench_Projects\\ACT57BLF02_MCLV2.X\\dist\\default\\production\\ACT57BLF02_MCLV2.X.production.elf"
x2cScope = X2CScope(port="COM9", elf_file=elf_file)

scopeArray = x2cScope.get_variable("Scope_Array")
# Set up scope configuration and channels
variables = [
    x2cScope.get_variable("motor.idq.q"),
    x2cScope.get_variable("motor.vabc.a"),
    x2cScope.get_variable("motor.vabc.b"),
    x2cScope.get_variable("motor.vabc.c"),
    x2cScope.get_variable("motor.apiData.velocityMeasured"),
]
x2cScope.set_scope_state(2)
for variable in variables:
    x2cScope.add_scope_channel(variable)

# x2cScope.set_scope_trigger(
#     variables[1],
#     trigger_level=500,
#     trigger_mode=1,
#     trigger_delay=-50,
#     trigger_edge=1,
# )

# Initialize data storage
data_storage = {var: [] for var in variables}

# number of data points to display at once
window_size = 250


def update_plot(frame):
    try:
        if x2cScope.is_scope_data_ready():
            print("Scope finished")

            # Read array chunks and store data
            scope_data = x2cScope.get_scope_channel_data(valid_data=False)
            for variable, data in scope_data.items():
                variable_name = str(variable)  # Or another way to get a unique identifier for the variable
                if variable_name not in data_storage:
                    data_storage[variable_name] = []

                data_storage[variable_name].extend(data)

            # Request new scope data
            x2cScope.request_scope_data()

    except Exception as e:
        logging.error(f"Error in main loop: {str(e)}")

    # Clear the current plot
    plt.clf()

    # Get the current max index for x-axis
    current_index = max(len(data) for data in data_storage.values())

    # Plot the data for each channel within the moving window
    for variable_name, data in data_storage.items():
        if data:
            # Determine the range of indices to plot
            start_index = max(0, current_index - window_size)
            end_index = current_index

            # Plot the data within the window range
            plt.plot(range(start_index, end_index), data[-window_size:], label=variable_name)

    # Set the x-axis limits to create the moving window effect
    plt.xlim(current_index - window_size, current_index)

    plt.xlabel("Data Index")
    plt.ylabel("Value")
    plt.title("Live Plot of Byte Data")
    plt.legend()
    plt.legend(loc='upper right')
    plt.draw()


# Set up the live plot
plt.ion()
fig = plt.figure()
ani = FuncAnimation(fig, update_plot, interval=100, cache_frame_data=False)

# Show the plot
plt.show(block=True)