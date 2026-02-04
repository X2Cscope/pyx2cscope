import socket


def tcp_echo_client(host='192.168.0.100', port=12666):
    # Create a TCP/IP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # Connect to the server
            print(f"Connecting to {host}:{port}...")
            sock.connect((host, port))
            print("Connected!")

            while True:
                # Get user input
                message = input("Enter message to send (or 'exit' to quit): ")
                if message.lower() == 'exit':
                    break

                # Send data
                print(f"Sending: {message}")
                sock.sendall(message.encode('utf-8'))

                # Receive response
                data = sock.recv(1024)
                print(f"Received: {data.decode('utf-8')}")

        except ConnectionRefusedError:
            print("Connection refused. Make sure the server is running.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            print("Closing connection")


if __name__ == "__main__":
    tcp_echo_client()