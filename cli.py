import socket
import argparse
import json
import sys
import time


SERVER_IP = "13.232.19.209"
SERVER_PORT = 3050

SEND_TYPES = {
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

RECEIVE_TYPES = {
    1: "immobilize",
    2: "rpmPreset",
}

# Connect to server
def connect_to_server():
    """Connect to the server"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_IP, SERVER_PORT))
        print(f"✅Connected to server {SERVER_IP}:{SERVER_PORT}")
        return client
    except Exception as e:
        print(f"❌Failed to connect to server: {e}")
        sys.exit(1)

# Encode Packet for Sending
def encode_packet(index, payload):
    """Encode a packet into HEX format before sending."""
    payload_bytes = payload.encode("utf-8") if isinstance(payload, str) else payload
    payload_length = len(payload_bytes)

    buffer_size = 4 + payload_length + 2  # Header(4) + Payload + Checksum(1) + End Flag(1)
    buffer = bytearray(buffer_size)

    # Fixed Header
    buffer[0] = 0xAA
    buffer[1] = 0xBB
    buffer[2] = index
    buffer[3] = payload_length

    # Payload
    buffer[4:4+payload_length] = payload_bytes

    # Calculate checksum (XOR of all bytes)
    checksum = 0
    for i in range(4 + payload_length):
        checksum ^= buffer[i]
    buffer[4 + payload_length] = checksum

    # End Flag
    buffer[5 + payload_length] = 0xCC

    return buffer

# Decode Packet for Receiving
def decode_packet(buffer):
    """Decode a received packet from HEX format."""
    if len(buffer) < 5:
        print("❌ Invalid packet: Too short.")
        return None

    if buffer[0] != 0xAA or buffer[1] != 0xBB:
        print("❌ Invalid header.")
        return None

    type_code = buffer[2]
    length = buffer[3]
    payload = buffer[4:4 + length]

    checksum = buffer[4 + length]

    # Verify Checksum
    calc_checksum = 0
    for i in range(4 + length):
        calc_checksum ^= buffer[i]

    if checksum != calc_checksum:
        print("❌ Checksum mismatch.")
        return None

    return {
        "dataType": SEND_TYPES.get(type_code, "unknown"),
        "payload": payload.decode("utf-8") if type_code in SEND_TYPES else int.from_bytes(payload, "big")
    }

# Send Data to Server
def send_data(client):
    """Let user choose data type and send it to the server repeatedly every 1 second."""
    try:
        while True:
            print("\nChoose data type to send:")
            for k, v in SEND_TYPES.items():
                print(f"  {k}: {v}")

            choice = int(input("\nEnter data type index (or 0 to stop): "))
            if choice == 0:
                break
            if choice not in SEND_TYPES:
                print("❌ Invalid choice.")
                continue

            value = input(f"Enter value for {SEND_TYPES[choice]}: ")

            packet = encode_packet(choice, value)
            client.sendall(packet)
            print(f"📤 Sent: {packet.hex()}")

            # Send every 1 sec until stopped
            for _ in range(5):  # Send 5 times for demo (change as needed)
                time.sleep(1)
                client.sendall(packet)
                print(f"📤 Re-sent: {packet.hex()}")

    except KeyboardInterrupt:
        print("\n⏹ Stopped sending.")
        return

# Receive Data from Server
def receive_data(client):
    """Continuously receive and decode data from server."""
    try:
        print("\nListening for incoming data...\n")
        while True:
            data = client.recv(1024)  # Adjust buffer size as needed
            if not data:
                print("❌ Disconnected.")
                break

            decoded = decode_packet(data)
            if decoded:
                print(f"📥 Received: {decoded}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹ Stopped receiving.")
        return
    
def main():
    """CLI Menu to intact with server"""

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