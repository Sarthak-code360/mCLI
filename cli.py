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
            
        elif choice == "2":
            print("\n Goodbye!! 👋 ")
            sys.exit(0)
        else:
            print("\n ❌ Invalid option")


if __name__ == "__main__":
    main()