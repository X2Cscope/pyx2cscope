"""exampleMCAF.py.

This example demonstrate a HiL (Hardware-in-the-Loop) script using motorBench (MCAF).
The script assumes the control of MCAF disabling the hardware UI, stop the motor if
it is running. Then it sets the velocity reference to 500 RPM and starts the motor.
After that it measures the time to reach the speed, waits 2 seconds and calculates
the RMS current using the scope functionality. After that it increases the velocity
reference to 1500 RPM and measures the time to reach the speed. Waits 2 seconds and
calculates the RMS current at this speed. The script stops the motor and gives the
control back to hardware UI.
"""

import time

import numpy as np

from pyx2cscope.utils import get_com_port, get_elf_file_path
from pyx2cscope.x2cscope import X2CScope

# Configuration for serial port communication
serial_port = get_com_port()  # Get the COM port from the utility function
elf_file = get_elf_file_path()  # Get the path to the ELF file from the utility function

# Initialize the X2CScope with the specified serial port and ELF file
x2c_scope = X2CScope(port=serial_port, elf_file=elf_file)

# Set hardware UI enabled to 0
# doing this we enable external control of the motor
hardware_ui_enabled = x2c_scope.get_variable("app.hardwareUiEnabled")
hardware_ui_enabled.set_value(0)

# Ensure the motor is stopped
stop_motor_request = x2c_scope.get_variable("motor.apiData.stopMotorRequest")
stop_motor_request.set_value(1)

# define target speeds
# Speed threshold in RPM (5000 = 500.0 RPM)
TARGET_SPEED_1_RPM = 5000
TARGET_SPEED_2_RPM = 15000

# Set the speed to TARGET_SPEED_1_RPM
velocity_reference = x2c_scope.get_variable("motor.apiData.velocityReference")
velocity_reference.set_value(TARGET_SPEED_1_RPM)

# Start the motor
run_motor_request = x2c_scope.get_variable("motor.apiData.runMotorRequest")
run_motor_request.set_value(1)

# Measure the time to reach the speed
start_time = time.time()
while True:
    speed_measured = x2c_scope.get_variable("motor.apiData.velocityMeasured")
    if speed_measured.get_value() >= TARGET_SPEED_1_RPM:
        break
end_time = time.time()
time_to_reach_speed_1 = end_time - start_time
print(f"Time to reach {TARGET_SPEED_1_RPM/10} RPM: {time_to_reach_speed_1:.2f} seconds")

# Wait for 2 seconds
time.sleep(2)

# Add current variables to the scope
phase_current_a = x2c_scope.get_variable("motor.iabc.a")
phase_current_b = x2c_scope.get_variable("motor.iabc.b")
x2c_scope.add_scope_channel(phase_current_a)
x2c_scope.add_scope_channel(phase_current_b)

# Request scope data
x2c_scope.request_scope_data()

# Wait until the scope data is ready
while not x2c_scope.is_scope_data_ready():
    time.sleep(0.1)

# Get the scope channel data
scope_data = x2c_scope.get_scope_channel_data()
current_a = scope_data["motor.iabc.a"]
current_b = scope_data["motor.iabc.b"]

# Calculate the RMS current
rms_current_a = np.sqrt(np.mean(np.square(current_a))) * 0.1  # Convert to Amps
rms_current_b = np.sqrt(np.mean(np.square(current_b))) * 0.1  # Convert to Amps
average_current_speed_1 = (rms_current_a + rms_current_b) / 2
print(f"Average current at {TARGET_SPEED_1_RPM/10} RPM: {average_current_speed_1:.2f} A")

# Increase the speed to TARGET_SPEED_2_RPM
velocity_reference.set_value(TARGET_SPEED_2_RPM)

# Measure the time to reach the new speed
start_time = time.time()
while True:
    speed_measured = x2c_scope.get_variable("motor.apiData.velocityMeasured")
    if speed_measured.get_value() >= TARGET_SPEED_2_RPM:
        break
end_time = time.time()
time_to_reach_speed_2 = end_time - start_time
print(f"Time to reach {TARGET_SPEED_2_RPM/10} RPM: {time_to_reach_speed_2:.2f} seconds")

# Wait for 2 seconds
time.sleep(2)

# Request scope data again
x2c_scope.request_scope_data()

# Wait until the scope data is ready
while not x2c_scope.is_scope_data_ready():
    time.sleep(0.1)

# Get the scope channel data again
scope_data = x2c_scope.get_scope_channel_data()
current_a = scope_data["motor.iabc.a"]
current_b = scope_data["motor.iabc.b"]

# Calculate the RMS current for the new speed
rms_current_a = np.sqrt(np.mean(np.square(current_a))) * 0.1  # Convert to Amps
rms_current_b = np.sqrt(np.mean(np.square(current_b))) * 0.1  # Convert to Amps
average_current_speed_2 = (rms_current_a + rms_current_b) / 2
print(f"Average current at {TARGET_SPEED_2_RPM/10} RPM: {average_current_speed_2:.2f} A")

# Stop the motor
stop_motor_request.set_value(1)

# Set hardware UI enabled to 1. Doing this we give the control back to the hardware UI.
hardware_ui_enabled.set_value(1)