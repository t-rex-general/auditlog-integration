#!/usr/bin/env python3
"""
Mock syslog server for testing.

This script creates a simple UDP syslog server that receives and displays
incoming syslog messages. Use this to verify your WazuhSyslogTransport is working.
"""
import socket
import sys


def run_mock_syslog_server(host="0.0.0.0", port=514):
    """
    Run a simple UDP syslog server that prints received messages.

    Args:
        host: Host to bind to (default: 0.0.0.0 - all interfaces)
        port: Port to listen on (default: 514)
    """
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind((host, port))
        print("=" * 60)
        print(f"Mock Syslog Server started on {host}:{port}")
        print("=" * 60)
        print("Waiting for messages... (Press Ctrl+C to stop)")
        print("")

        message_count = 0

        while True:
            # Receive data
            data, addr = sock.recvfrom(65535)  # Max UDP packet size
            message_count += 1

            # Decode and display
            try:
                message = data.decode('utf-8')
                print(f"[{message_count}] From {addr[0]}:{addr[1]}")
                print(f"    {message}")
                print("")
            except UnicodeDecodeError:
                print(f"[{message_count}] From {addr[0]}:{addr[1]}")
                print(f"    [Binary data: {len(data)} bytes]")
                print("")

    except PermissionError:
        print(f"Error: Permission denied to bind to port {port}")
        print(f"Ports below 1024 require root/admin privileges.")
        print(f"Try using a higher port (e.g., 5514) or run with sudo/admin rights")
        return 1
    except KeyboardInterrupt:
        print("")
        print("=" * 60)
        print(f"Server stopped. Received {message_count} messages.")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        sock.close()


def main():
    # Default port 5514 to avoid needing root privileges
    # Change to 514 if you want standard syslog port (requires sudo)
    port = 5514

    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Usage: {sys.argv[0]} [port]")
            print(f"Example: {sys.argv[0]} 5514")
            sys.exit(1)

    exit_code = run_mock_syslog_server(port=port)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
