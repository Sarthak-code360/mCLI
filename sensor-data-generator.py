import csv
import math
from datetime import datetime, timedelta
import random

def generate_sine_wave(min_val, max_val, time_step, frequency=0.1, phase=0):
    """Generate a sine wave between min and max values."""
    mid = (max_val + min_val) / 2
    amplitude = (max_val - min_val) / 2
    return mid + amplitude * math.sin(2 * math.pi * frequency * time_step + phase)

def add_noise(value, noise_factor=0.02):
    """Add random noise to a value."""
    noise = random.uniform(-noise_factor, noise_factor) * value
    return value + noise

def generate_sensor_data(duration_seconds=1000, sample_rate_hz=10):
    """Generate sensor data for the specified duration."""
    data = []
    start_time = datetime.now()
    
    # Different frequencies for various parameters to create realistic variations
    rpm_freq = 0.05
    current_freq = 0.08
    voltage_freq = 0.03
    torque_freq = 0.06
    
    # Generate data points
    for i in range(duration_seconds * sample_rate_hz):
        time_step = i / sample_rate_hz
        current_time = start_time + timedelta(seconds=time_step)
        
        # Generate base values using sine waves for smooth transitions
        rpm = generate_sine_wave(0, 2500, time_step, rpm_freq)
        bus_voltage = generate_sine_wave(85, 95, time_step, voltage_freq)  # Centered around 90V
        bus_current = generate_sine_wave(-20, 120, time_step, current_freq)
        torque = generate_sine_wave(0, 190, time_step, torque_freq)
        
        # Generate phase-shifted currents for U, V, W (120° apart)
        current_u = generate_sine_wave(-20, 120, time_step, current_freq, 0)
        current_v = generate_sine_wave(-20, 120, time_step, current_freq, 2*math.pi/3)
        current_w = generate_sine_wave(-20, 120, time_step, current_freq, 4*math.pi/3)
        
        # Generate throttle voltage and SOC with slower variations
        throttle = generate_sine_wave(0, 5, time_step, 0.02)
        soc = generate_sine_wave(20, 100, time_step, 0.01)  # Starting from 20% to be realistic
        
        # Add some noise to make data more realistic
        row = {
            'Time': current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'Bus_Voltage': round(add_noise(bus_voltage), 2),
            'Bus_Current': round(add_noise(bus_current), 2),
            'RPM': round(add_noise(rpm)),
            'Torque': round(add_noise(torque), 2),
            'Current_U': round(add_noise(current_u), 2),
            'Current_V': round(add_noise(current_v), 2),
            'Current_W': round(add_noise(current_w), 2),
            'Throttle_Voltage': round(add_noise(throttle), 2),
            'SOC': round(add_noise(soc), 1)
        }
        data.append(row)
    
    return data

def save_to_csv(data, filename='sensor_data.csv'):
    """Save the generated data to a CSV file."""
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['Time', 'Bus_Voltage', 'Bus_Current', 'RPM', 'Torque', 
                     'Current_U', 'Current_V', 'Current_W', 'Throttle_Voltage', 'SOC']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(data)

if __name__ == "__main__":
    # Generate data for 1000 seconds at 10Hz sample rate
    sensor_data = generate_sensor_data(duration_seconds=1000, sample_rate_hz=10)
    save_to_csv(sensor_data)
    print(f"Generated {len(sensor_data)} data points")
