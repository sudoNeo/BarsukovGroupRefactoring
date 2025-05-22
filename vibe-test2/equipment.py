import multiprocessing
import time
import os
import socket
import struct
from typing import Dict, Any, Optional


class Equipment:
    def __init__(self, name: str, address: str, port: int):
        self.name = name
        self.address = address
        self.port = port
        self.parent_conn, self.child_conn = multiprocessing.Pipe()
        self.process = None
        self.running = False
        self.data_buffer = []
        self.udp_socket = None
        self.stream_active = False

    def start(self):
        self.running = True
        self.process = multiprocessing.Process(
            target=self._data_collection_loop,
            args=(self.child_conn,)
        )
        self.process.daemon = True
        self.process.start()
        return self.process

    def stop(self):
        if self.running:
            self.running = False
            self.send_command("shutdown", {})
            if self.process and self.process.is_alive():
                self.process.join(timeout=1.0)
                if self.process.is_alive():
                    self.process.terminate()
            self.parent_conn.close()
            self.child_conn.close()

    def send_command(self, state: str, data: Dict[str, Any]) -> None:
        command = {"state": state, "data": data}
        self.parent_conn.send(command)

    def _data_collection_loop(self, conn):
        try:
            while self.running:
                if conn.poll(0.1):
                    message = conn.recv()
                    self._process_message(message)
                
                if self.stream_active and self.udp_socket:
                    try:
                        # Non-blocking receive with timeout
                        self.udp_socket.settimeout(0.01)
                        buf, _ = self.udp_socket.recvfrom(1024 + 4)  # Default buffer size
                        
                        # Process data (simplified example)
                        header = struct.unpack_from('>I', buf)[0]
                        counter = header & 0xff
                        data = list(struct.unpack_from('>256f', buf, 4))
                        
                        # Add timestamp
                        timestamp = time.time_ns()
                        sample = [timestamp] + data
                        
                        # Add to buffer
                        self.data_buffer.append(sample)
                        
                    except socket.timeout:
                        pass  # No data available
                else:
                    time.sleep(0.01)  # Prevent CPU hogging when not streaming
                    
        except KeyboardInterrupt:
            pass
        finally:
            if self.udp_socket:
                self.udp_socket.close()
            conn.close()

    def _process_message(self, message: Dict[str, Any]):
        state = message.get("state")
        data = message.get("data", {})
        
        if state == "configure":
            self._configure_equipment(data)
        elif state == "start_collection":
            self._start_collection(data)
        elif state == "stop_collection":
            self._stop_collection()
        elif state == "get_data":
            self._send_data_to_supervisor()
        elif state == "ping":
            self._respond_to_ping(data)
        elif state == "shutdown":
            self._shutdown()

    def _configure_equipment(self, config_data: Dict[str, Any]):
        # Setup equipment configuration
        if os.environ.get('MOCK_HARDWARE') == 'True':
            print(f"Equipment {self.name}: Mocking configuration with {config_data}")
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # For mock hardware, we would initialize a mock UDP socket here
            from mocks import MockUDPSocket
            self.udp_socket = MockUDPSocket()
        else:
            print(f"Equipment {self.name}: Configuring with {config_data}")
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('', self.port))
            
        # Extract configuration parameters
        self.channels = config_data.get('channels', 'X')
        self.sample_rate = config_data.get('rate', 1000)
        self.packet_size = config_data.get('packet_size', 0)  # Default to 1024 bytes

    def _start_collection(self, params: Dict[str, Any]):
        print(f"Equipment {self.name}: Starting collection with {params}")
        self.stream_active = True
        self.data_buffer = []  # Clear previous data
        
        # Start parameters
        self.duration = params.get('duration', 10)  # Default 10 seconds
        self.file_output = params.get('file', None)
        
        # In a real implementation, we would send commands to the actual hardware
        # to start streaming data, for example:
        # self.vxi_interface.write('STREAM ON')

    def _stop_collection(self):
        print(f"Equipment {self.name}: Stopping collection")
        self.stream_active = False
        
        # In a real implementation, we would send commands to the actual hardware
        # to stop streaming data, for example:
        # self.vxi_interface.write('STREAM OFF')

    def _send_data_to_supervisor(self):
        # Send collected data back to the supervisor
        if self.data_buffer:
            self.child_conn.send({"state": "data", "data": {"buffer": self.data_buffer}})
            self.data_buffer = []  # Clear after sending

    def _respond_to_ping(self, data):
        # Echo back the ping data to confirm pipe is working
        ping_id = data.get("id", "unknown")
        self.child_conn.send({"state": "pong", "data": {"id": ping_id, "name": self.name}})

    def _shutdown(self):
        print(f"Equipment {self.name}: Shutting down")
        self.stream_active = False
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()


class Supervisor:
    def __init__(self):
        self.equipment = {}
        
    def add_equipment(self, name: str, address: str, port: int) -> Equipment:
        equipment = Equipment(name, address, port)
        self.equipment[name] = equipment
        return equipment
        
    def configure_all(self, config: Dict[str, Any]):
        for name, equip in self.equipment.items():
            equip.send_command("configure", config.get(name, {}))
            
    def start_all(self, params: Dict[str, Any] = None):
        if params is None:
            params = {}
            
        for name, equip in self.equipment.items():
            equip.start()
            equip.send_command("start_collection", params.get(name, {}))
            
    def stop_all(self):
        for equip in self.equipment.values():
            equip.send_command("stop_collection", {})
            
    def get_data_from_all(self):
        for equip in self.equipment.values():
            equip.send_command("get_data", {})
    
    def ping_all(self, timeout=1.0):
        results = {}
        for name, equip in self.equipment.items():
            # Send ping with unique ID to each equipment
            ping_id = f"ping-{time.time()}"
            equip.send_command("ping", {"id": ping_id})
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < timeout:
                if equip.parent_conn.poll(0.1):
                    response = equip.parent_conn.recv()
                    if response.get("state") == "pong" and response.get("data", {}).get("id") == ping_id:
                        results[name] = True
                        break
                time.sleep(0.01)
            
            if name not in results:
                results[name] = False
                
        return results
    
    def shutdown(self):
        for equip in self.equipment.values():
            equip.stop()


if __name__ == "__main__":
    # Example usage
    supervisor = Supervisor()
    
    # Add equipment
    supervisor.add_equipment("oscilloscope1", "10.0.0.3", 1865)
    supervisor.add_equipment("oscilloscope2", "10.0.0.4", 1866)
    
    # Configure equipment
    config = {
        "oscilloscope1": {"channels": "XY", "rate": 1000, "packet_size": 3},
        "oscilloscope2": {"channels": "XY", "rate": 1000, "packet_size": 3}
    }
    supervisor.configure_all(config)
    
    # Start data collection
    collection_params = {
        "oscilloscope1": {"duration": 12, "file": "thread1.csv"},
        "oscilloscope2": {"duration": 12, "file": "thread2.csv"}
    }
    supervisor.start_all(collection_params)
    
    # Let it run for a few seconds
    try:
        time.sleep(5)
        supervisor.get_data_from_all()
        time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop and shutdown
        supervisor.stop_all()
        supervisor.shutdown()