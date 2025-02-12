import datetime
import socket
import sys
import time
import select
import threading
import pandas as pd
import json

SERVER_IP = "13.232.19.209"
SERVER_PORT = 3050
CSV_FILE = "sensor_data.csv"

stop_listening = False  # Global flag to stop listening
stop_sending = False

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

def send_file_data(client):
    global stop_sending
    stop_sending = False
    print("\nSending data from file... (Press 'q' to stop)")

    # Start a separate thread to listen for 'q' input
    listener_thread = threading.Thread(target=listen_for_stop, daemon=True)
    listener_thread.start()
    
    try:
        df = pd.read_csv(CSV_FILE)
        row_count = 0

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
    except Exception as e:
        print(f"❌ Error reading or sending data: {e}")
    
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
