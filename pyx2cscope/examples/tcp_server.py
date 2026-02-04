import socket

def calc_checksum(frame_bytes):
    return sum(frame_bytes) & 0xFF

def make_deviceinfo_response(slave_id=0x01, device_id=0x8240):
    response = bytearray(b'U.\x01\x00\x00\x05\x00\x01\x00\xff@\x82Nov1920251028\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\xfcT\x00\x00\xcd')
    return bytes(response)

def make_loadparameter_response():
    # Your provided response
    resp = bytearray(b'U\x1f\x01\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1e@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x88\x13\x00\x00\x88\x13\x00\x00\x82\x9c')
    return resp

def is_deviceinfo_request(data, slave_id=0x01):
    return (
        len(data) == 5 and
        data[0] == 0x55 and
        data[1] == 0x01 and
        data[2] == slave_id and
        data[3] == 0x00
    )

def is_loadparameter_request(data, slave_id=0x01):
    return (
        len(data) == 7 and
        data[0] == 0x55 and
        data[1] == 0x03 and
        data[2] == slave_id and
        data[3] == 0x11
    )

def run_server(port=12666, slave_id=0x01, device_id=0x8240):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', port))
        s.listen(1)
        print(f"LNet TCP server running on port {port}...")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(64)
                    if not data:
                        break
                    if is_deviceinfo_request(data, slave_id):
                        resp = make_deviceinfo_response(slave_id, device_id)
                        conn.sendall(resp)
                    elif is_loadparameter_request(data, slave_id):
                        resp = make_loadparameter_response()
                        conn.sendall(resp)
                    else:
                        print(f"Unknown request: {data.hex()}")

if __name__ == "__main__":
    run_server()




