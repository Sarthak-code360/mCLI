import datetime
import socket
import sys
import time
import select
import threading
import pandas as pd
import json
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import numpy as np

SERVER_IP = "13.232.19.209"
SERVER_PORT = 3050
CSV_FILE = "sensor_data.csv"

stop_listening = False  # Global flag to stop listening
stop_sending = False

PLOT_POINTS = 100  # Number of points to show in the plot
voltage_data = deque(maxlen=PLOT_POINTS)
current_data = deque(maxlen=PLOT_POINTS)
soc_data = deque(maxlen=PLOT_POINTS)
throttle_data = deque(maxlen=PLOT_POINTS)
rpm_data = deque(maxlen=PLOT_POINTS)
current_u_data = deque(maxlen=PLOT_POINTS)
current_v_data = deque(maxlen=PLOT_POINTS)
current_w_data = deque(maxlen=PLOT_POINTS)
timestamps = deque(maxlen=PLOT_POINTS)
plot_lock = threading.Lock()  # Thread safety for plotting

DATA_TYPES = {
    1: "immobilize",
    2: "rpmPreset",
    3: "gps",
    4: "busCurrent",
    5: "busVoltage",
    6: "rpm",
    7: "deviceTemperature",
    8: "networkStrength",
    9: "torque",
    10: "SOC",
    11: "throttle",
    12: "motorTemperature",
}

def connect_to_server():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_IP, SERVER_PORT))
        print(f"✅ Connected to server {SERVER_IP}:{SERVER_PORT}")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to server: {e}")
        sys.exit(1)

def encode_packet(index, payload):
    if isinstance(payload, str):
        payload_bytes = payload.encode()
    elif isinstance(payload, int):
        payload_bytes = payload.to_bytes(2, byteorder='big', signed=True)
    elif isinstance(payload, bytes):  # Handle bytes directly
        payload_bytes = payload
    else:
        raise ValueError("Payload must be int, str, or bytes")
    
    payload_length = len(payload_bytes)
    buffer = bytearray(5 + payload_length)
    buffer[0], buffer[1] = 0xAA, 0xBB
    buffer[2], buffer[3] = index, payload_length
    buffer[4:4+payload_length] = payload_bytes
    buffer[-1] = 0xCC
    
    checksum = 0
    for i in range(len(buffer) - 1):
        checksum ^= buffer[i]
    buffer.insert(-1, checksum)
    
    return bytes(buffer)

def decode_packet(buffer):
    if len(buffer) < 5 or buffer[0] != 0xAA or buffer[1] != 0xBB:
        print("❌ Invalid packet.")
        return None
    
    type_code, length = buffer[2], buffer[3]
    payload = buffer[4:4 + length]
    checksum = buffer[4 + length]
    calc_checksum = 0
    for i in range(4 + length):
        calc_checksum ^= buffer[i]
    
    if checksum != calc_checksum:
        print("❌ Checksum mismatch.")
        return None

    data_type = DATA_TYPES.get(type_code, "unknown")
    
    return {
        "dataType": data_type,
        "payload": payload.decode("utf-8") if type_code == 3 else int.from_bytes(payload, "big")
    }

def send_data(client):
    try:
        while True:
            print("\nChoose data type to send:")
            for k, v in DATA_TYPES.items():
                print(f"  {k}: {v}")
                
            choice = input("\nEnter data type index (or 'q' to stop): ").strip()
            if choice.lower() == 'q':
                break
            
            if not choice.isdigit():  # Ensure input is numeric
                print("❌ Invalid choice.")
                continue
            
            choice = int(choice)  # Convert to integer after validation
            
            if choice not in DATA_TYPES:
                print("❌ Invalid choice.")
                continue
            
            value = input(f"Enter value for {DATA_TYPES[choice]}: ")

            if choice == 3:  # GPS should be sent as a string
                encoded_value = value.encode()  
            elif choice in [4, 5, 10, 11]:  # Values that need to be split at decimal
                try:
                    # Split the input into whole number and decimal part
                    whole_part, decimal_part = value.split('.')
                    # Convert both parts to integers and then to hex
                    whole_part_hex = int(whole_part).to_bytes(1, 'big', signed=True)
                    decimal_part_hex = int(decimal_part).to_bytes(1, 'big', signed=True)
                    encoded_value = whole_part_hex + decimal_part_hex
                except ValueError:
                    print("❌ Invalid decimal input. Please enter a valid number in the format 'whole.decimal'.")
                    continue
            elif choice in [6, 7, 8, 9, 12]:  # Values that should be sent as integers (without decimal values)
                encoded_value = int(value).to_bytes(2, 'big', signed=True) # (working)
            else:
                print("❌ Unsupported data type.")
                continue

            packet = encode_packet(choice, encoded_value)
            client.sendall(packet)
            print(f"📤 Sent: {packet.hex()}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹ Stopped sending.")

def listen_for_stop():
    global stop_sending
    while True:
        user_input = input().strip()
        if user_input.lower() == 'q':
            stop_sending = True
            break  # Stop the thread

def init_plot():
    """Initialize the plotting window with six subplots including RPM and Phase Currents"""
    plt.ion()  # Enable interactive mode
    
    # Create a 3x2 grid (6 subplots)
    fig, axs = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle('Real-time Bus Data')
    
    # Get individual axes
    ax1 = axs[0, 0]  # Bus Voltage
    ax2 = axs[0, 1]  # Bus Current
    ax3 = axs[1, 0]  # SOC
    ax4 = axs[1, 1]  # Throttle
    ax5 = axs[2, 0]  # RPM
    ax6 = axs[2, 1]  # Phase Currents (U, V, W)
    
    # Set up voltage subplot
    ax1.set_ylabel('Bus Voltage (V)')
    ax1.set_ylim(80, 100)
    ax1.grid(True)
    
    # Set up current subplot
    ax2.set_ylabel('Bus Current (A)')
    ax2.set_ylim(-30, 130)
    ax2.grid(True)

    # Set up SOC subplot
    ax3.set_ylabel('SOC (%)')
    ax3.set_ylim(0, 100)
    ax3.grid(True)

    # Set up throttle subplot
    ax4.set_ylabel('Throttle (V)')
    ax4.set_ylim(0, 6)
    ax4.grid(True)
    
    # Set up RPM subplot
    ax5.set_ylabel('RPM')
    ax5.set_ylim(0, 4000)
    ax5.grid(True)
    
    # Set up Phase Currents subplot
    ax6.set_ylabel('Phase Currents (A)')
    ax6.set_ylim(-50, 150)  # Adjust based on your current range
    ax6.grid(True)
    
    return fig, axs

def update_plot(fig, axs):
    """Update the plot with new data including RPM and Phase Currents"""
    with plot_lock:
        # Only attempt to plot if we have data
        if not timestamps or len(timestamps) == 0:
            return
        
        # Get individual axes
        ax1 = axs[0, 0]  # Bus Voltage
        ax2 = axs[0, 1]  # Bus Current
        ax3 = axs[1, 0]  # SOC
        ax4 = axs[1, 1]  # Throttle
        ax5 = axs[2, 0]  # RPM
        ax6 = axs[2, 1]  # Phase Currents
        
        # Clear previous lines
        ax1.clear()
        ax2.clear()
        ax3.clear()
        ax4.clear()
        ax5.clear()
        ax6.clear()
        
        # Reset titles and grid
        ax1.set_ylabel('Bus Voltage (V)')
        ax2.set_ylabel('Bus Current (A)')
        ax3.set_ylabel('SOC (%)')
        ax4.set_ylabel('Throttle (V)')
        ax5.set_ylabel('RPM')
        ax6.set_ylabel('Phase Currents (A)')

        ax1.grid(True)
        ax2.grid(True)
        ax3.grid(True)
        ax4.grid(True)
        ax5.grid(True)
        ax6.grid(True)
        
        # Set y-axis limits
        ax1.set_ylim(80, 100)
        ax2.set_ylim(-30, 130)
        ax3.set_ylim(0, 100)
        ax4.set_ylim(0, 6)
        ax5.set_ylim(0, 4000)
        ax6.set_ylim(-50, 150)  # Adjust based on your current range

        # Convert timestamps to numeric format for plotting
        time_numbers = list(range(len(timestamps)))
        
        # Ensure all data lists have the same length as timestamps
        valid_len = len(time_numbers)
        
        if len(voltage_data) == valid_len:
            ax1.plot(time_numbers, list(voltage_data), 'b-', label='Voltage')
            ax1.legend(loc='upper right')
            
        if len(current_data) == valid_len:
            ax2.plot(time_numbers, list(current_data), 'r-', label='Current')
            ax2.legend(loc='upper right')
            
        if len(soc_data) == valid_len:
            ax3.plot(time_numbers, list(soc_data), 'g-', label='SOC')
            ax3.legend(loc='upper right')
            
        if len(throttle_data) == valid_len:
            ax4.plot(time_numbers, list(throttle_data), 'y-', label='Throttle')
            ax4.legend(loc='upper right')
            
        if len(rpm_data) == valid_len:
            ax5.plot(time_numbers, list(rpm_data), 'm-', label='RPM')
            ax5.legend(loc='upper right')
            
        # Plot all phase currents on the same subplot
        if len(current_u_data) == valid_len and len(current_v_data) == valid_len and len(current_w_data) == valid_len:
            ax6.plot(time_numbers, list(current_u_data), 'r-', label='Current U')
            ax6.plot(time_numbers, list(current_v_data), 'g-', label='Current V')
            ax6.plot(time_numbers, list(current_w_data), 'b-', label='Current W')
            ax6.legend(loc='upper right')
        
        # Set x-axis labels
        if len(timestamps) > 0:
            # Show fewer x-axis labels to prevent overcrowding
            n_labels = min(5, len(timestamps))
            if n_labels > 0:
                step = max(len(timestamps) // n_labels, 1)
                positions = list(range(0, len(timestamps), step))
                labels = [timestamps[i].split()[1] for i in positions if i < len(timestamps)]  # Only show time part

                # Set time labels only on bottom subplots
                ax1.set_xticks([])
                ax2.set_xticks([])
                ax3.set_xticks([])
                ax4.set_xticks([])
                if positions and labels:
                    ax5.set_xticks(positions)
                    ax5.set_xticklabels(labels, rotation=45)
                    ax6.set_xticks(positions)
                    ax6.set_xticklabels(labels, rotation=45)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)  # Make room for suptitle
        
        # Draw the update
        fig.canvas.draw()
        fig.canvas.flush_events()

def listen_for_stop():
    global stop_sending
    while True:
        user_input = input().strip()
        if user_input.lower() == 'q':
            stop_sending = True
            break  # Stop the thread

def send_file_data(client):
    global stop_sending, timestamps, voltage_data, current_data, soc_data, throttle_data, rpm_data
    global current_u_data, current_v_data, current_w_data
    stop_sending = False
    
    print("\nSending data from file... (Press 'q' to stop)")

    # Start a separate thread to listen for 'q' input
    listener_thread = threading.Thread(target=listen_for_stop, daemon=True)
    listener_thread.start()
    
    try:
        df = pd.read_csv(CSV_FILE)
        required_columns = ["Time", "Bus_Voltage", "Bus_Current", "RPM", "Torque", "Current_U", "Current_V", "Current_W", "Throttle_Voltage", "SOC"]
        
        # Check if all required columns are present
        for column in required_columns:
            if column not in df.columns:
                raise ValueError(f"Missing required column: {column}")

        row_count = 0

        # Clear old data if starting fresh
        with plot_lock:
            timestamps.clear()
            voltage_data.clear()
            current_data.clear()
            soc_data.clear()
            throttle_data.clear()
            rpm_data.clear()
            current_u_data.clear()
            current_v_data.clear()
            current_w_data.clear()

        # Get the figure and axes array
        fig, axs = init_plot()

        for _, row in df.iterrows():
            if stop_sending:
                break

            payload = {
                "time" : row["Time"],
                "motor_data" : {
                    "busVoltage" : float(row["Bus_Voltage"]),
                    "busCurrent" : float(row["Bus_Current"]),
                    "rpm" : float(row["RPM"]),
                    "torque" : float(row["Torque"]),
                },
                "phase_currents": {
                    "u": float(row["Current_U"]),
                    "v": float(row["Current_V"]),
                    "w": float(row["Current_W"])
                },
                "system_status": {
                    "throttle_voltage": float(row["Throttle_Voltage"]),
                    "soc": float(row["SOC"])
                }
            }

            # Update plotting data
            with plot_lock:
                timestamps.append(row["Time"])
                voltage_data.append(float(row["Bus_Voltage"]))
                current_data.append(float(row["Bus_Current"]))
                soc_data.append(float(row["SOC"]))
                throttle_data.append(float(row["Throttle_Voltage"]))
                rpm_data.append(float(row["RPM"]))
                current_u_data.append(float(row["Current_U"]))
                current_v_data.append(float(row["Current_V"]))
                current_w_data.append(float(row["Current_W"]))
            
            # Update plot every 5 data points to improve performance
            if row_count % 5 == 0:
                update_plot(fig, axs)

            json_data = json.dumps(payload) # Convert to JSON string
            client.sendall(json_data.encode()) # Send as bytes to server
            
            row_count += 1

            print(f"📤 Sent row {row_count}: {json_data}")
            print(f"⏱ Progress: {row_count}/{len(df)} rows sent", end='\r')
            
            time.sleep(0.1)  # Sending at 10Hz to match data generation rate

    except FileNotFoundError:
        print(f"❌ Error: CSV file not found at {CSV_FILE}")
    except pd.errors.EmptyDataError:
        print("❌ Error: The CSV file is empty")
    except ValueError as ve:
        print(f"❌ Error: {ve}")
    except Exception as e:
        print(f"❌ Error reading or sending data: {e}")
    
    finally:
        plt.ioff()
        plt.close('all')
    
    print("\n⏹ Stopped sending file data. Returning to menu.\n")

def receive_data(client):
    global stop_listening
    stop_listening = False
    print("\nListening for incoming data... (Press 'q' to stop)\n")

    def listen():
        global stop_listening
        while not stop_listening:
            ready, _, _ = select.select([client], [], [], 1)  # Check if data is available
            if ready:
                data = client.recv(1024)
                if not data:
                    print("❌ Disconnected.")
                    stop_listening = True
                    break
                decoded = decode_packet(data)
                if decoded:
                    print(f"📥 Received: {decoded}")
            time.sleep(0.1)  # Small delay to reduce CPU usage

    # Start listening thread
    listener_thread = threading.Thread(target=listen, daemon=True)
    listener_thread.start()

    # Wait for 'q' to stop listening
    while not stop_listening:
        user_input = input()
        if user_input.lower() == 'q':
            stop_listening = True

    print("\n⏹ Stopped receiving. Returning to menu.\n")

def main():
    while True:
        print("\n Welcome to Mazout CLI Tool")
        print("1. Connect")
        print("2. Quit")
        choice = input("\nEnter option: ")
        if choice == "1":
            client = connect_to_server()
            while True:
                print("\n Menu:")
                print("1. Send Data")
                print("2. Receive Data")
                print("3. Send Data from File")
                print("4. Disconnect")
                sub_choice = input("\nEnter option: ")
                if sub_choice == "1":
                    send_data(client)
                elif sub_choice == "2":
                    receive_data(client)
                elif sub_choice == "3":
                    send_file_data(client)
                elif sub_choice == "4":
                    client.close()
                    print("\n Disconnected!! 🔌 ")
                    break
                else:
                    print("\n ❌ Invalid option")
        elif choice == "2":
            print("\n Goodbye!! 👋 ")
            sys.exit(0)
        else:
            print("\n ❌ Invalid option")

if __name__ == "__main__":
    main()