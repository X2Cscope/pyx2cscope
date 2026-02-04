import socket

def main():
    UDP_IP = ""          # empty = listen on all interfaces
    UDP_PORT = 5150

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind the socket to the port
    sock.bind((UDP_IP, UDP_PORT))

    print(f"UDP server listening on port {UDP_PORT}...")

    while True:
        data, addr = sock.recvfrom(4096)  # buffer size
        print(f"Received from {addr}: {data}")

if __name__ == "__main__":
    main()
