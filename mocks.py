import struct
import time
import socket

class MockVXI11Instrument:
    def __init__(self, ip):
        self.ip = ip
        self.responses = {
            'STREAMRATEMAX?': '100000.0',
        }

    def write(self, command):
        print(f"Mock VXI-11 write: {command}")

    def ask(self, command):
        return self.responses.get(command, "0")

    def close(self):
        pass

class MockUDPSocket:    
    def __init__(self, *args, **kwargs):
        self.packet_count = 0
        self.max_packets = 10

    def bind(self, address):
        pass

    def recvfrom(self, bufsize):
        if self.packet_count < self.max_packets:
            header = struct.pack('>I', self.packet_count & 0xFF)
            data = struct.pack('>256f', *[1.0] * 256)
            packet = header + data
            self.packet_count += 1
            time.sleep(0.01)
            return packet, ('127.0.0.1', 12345)
        else:
            raise socket.timeout("No more data")

    def close(self):
        pass