import socket
import sys
import time
import select
import threading

SERVER_IP = "13.232.19.209"
SERVER_PORT = 3050

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

stop_listening = False  # Global flag to stop listening

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
            elif choice in [4, 5, 10, 11]:  # Values that need to be multiplied by 100
                encoded_value = int(float(value) * 100).to_bytes(2, 'big', signed=True)
            elif choice in [6, 7, 8, 9, 12]:  # Values that should be sent as integers (without decimal values)
                encoded_value = int(value).to_bytes(2, 'big', signed=True)
            else:
                print("❌ Unsupported data type.")
                continue

            packet = encode_packet(choice, encoded_value)
            client.sendall(packet)
            print(f"📤 Sent: {packet.hex()}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹ Stopped sending.")


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
                print("3. Disconnect")
                sub_choice = input("\nEnter option: ")
                if sub_choice == "1":
                    send_data(client)
                elif sub_choice == "2":
                    receive_data(client)
                elif sub_choice == "3":
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
