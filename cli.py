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
                print("\n\n Menu:")
                print("1. Send Data")
                print("2. Receive Data")
                print("3. Disconnect")

                # sub_choice = input("\nEnter option: ")

                # if sub_choice == "1":
                #     send_data(client)
                # elif sub_choice == "2":
                #     receive_data(client)
                # elif sub_choice == "3":
                #     client.close()
                #     print("\n Disconnected!! 🔌 ")
                #     break
                # else:
                #     print("\n ❌ Invalid option")

        elif choice == "2":
            print("\n Goodbye!! 👋 ")
            sys.exit(0)
        else:
            print("\n ❌ Invalid option")


if __name__ == "__main__":
    main()