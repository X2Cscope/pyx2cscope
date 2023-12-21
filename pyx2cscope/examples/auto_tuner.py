import matplotlib.pyplot as plt
import numpy as np

# Define the reference waveform (desired setpoint)
reference_waveform = np.sin(np.linspace(0, 10, 100))

# Define initial Kp and Ki values
Kp = 10.0
Ki = 1.10

# Define simulation parameters
dt = 0.1  # Time step
num_iterations = 100

# Initialize variables
integral = 0
history = np.zeros_like(reference_waveform)  # Initialize history with zeros
errors = []  # To store error over time

# Gradient descent parameters
learning_rate = 0.01

# Simulation loop
for _ in range(num_iterations):
    error = reference_waveform - history  # Calculate the error
    integral += np.sum(error) * dt  # Accumulate error for integral control
    Kp += learning_rate * np.sum(error)  # Update Kp
    Ki += learning_rate * integral  # Update Ki

    # Simulate the control system with the updated gains
    control_output = Kp * error + Ki * integral

    # In a real system, you would apply 'control_output' to your system and collect data.
    # For this example, we'll simulate it by updating the history.
    history += control_output

    # Store the error at each iteration
    errors.append(np.sum(error))

# At this point, Kp and Ki have been adjusted to minimize the error.

# Plot the reference waveform, system response, and error
plt.figure(figsize=(12, 6))
plt.subplot(3, 1, 1)
plt.plot(reference_waveform, label="Reference Waveform")
plt.legend()
plt.title("Auto-Tuning of Kp and Ki")

plt.subplot(3, 1, 2)
plt.plot(history, label="System Response")
plt.legend()

plt.subplot(3, 1, 3)
plt.plot(errors, label="Error")
plt.legend()

plt.tight_layout()
plt.show()

print(f"Optimal Kp: {Kp}")
print(f"Optimal Ki: {Ki}")
