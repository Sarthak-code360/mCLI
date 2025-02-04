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
