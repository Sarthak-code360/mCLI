# Mazout CLI Tool

Mazout CLI Tool is a command-line interface for sending and receiving data between an embedded hardware system and a remote server using a custom TCP protocol. This tool is designed to interact with Mazout Electric's EV motor controller system.

## Features
- **Connect** to the server via TCP.
- **Send data** to the server based on predefined data types.
- **Receive real-time data** from the server.
- **Custom data encoding** with checksum validation.
- **Supports decimal values** by splitting them into two separate bytes before transmission.

## Installation
Ensure you have Python installed. Clone this repository and install dependencies:

```sh
# Clone the repository
git clone https://github.com/mazout-electric/cli-tool.git
cd cli-tool

# Install required dependencies
pip install -r requirements.txt
```

## Usage
Run the CLI tool by executing:

```sh
python cli.py
```

### Menu Options
- **1. Connect** – Establish a TCP connection with the server.
- **2. Quit** – Exit the CLI tool.

#### Inside the Connection Menu:
- **1. Send Data** – Select a data type and enter a value to send.
- **2. Receive Data** – Start listening for incoming data.
- **3. Disconnect** – Close the connection.

### Data Encoding
- Each packet follows a structured format including headers, payload, and checksum.
- Decimal values are split into two separate bytes (e.g., `12.13` is transmitted as `0x0C 0x0D`).

## License
This project is licensed under the **Mazout Electric Proprietary License**. See the [LICENSE](./LICENSE) file for details.

## Contact

For general inquiries or issues, contact our support team:

- **Support Email:** info@mazoutelectric.com
- **GitHub Issues:** [Mazout Vendor Application Issues](https://github.com/Mazout-Electric/vendor-application/issues)

For specific technical questions, you can also reach out to:

- **Developer:** [Sarthak Mishra](https://github.com/Sarthak-code360)

For any queries or contributions, contact: [info@mazoutelectric.com](mailto:info@mazoutelectric.com)

