import os
import pytest
import time
from equipment import Equipment, Supervisor


@pytest.fixture
def mock_hardware():
    """Set up mock hardware environment variable for testing."""
    os.environ['MOCK_HARDWARE'] = 'True'
    yield
    os.environ.pop('MOCK_HARDWARE', None)


def test_equipment_creation():
    """Test that Equipment instance is created correctly."""
    eq = Equipment("test_device", "127.0.0.1", 1865)
    assert eq.name == "test_device"
    assert eq.address == "127.0.0.1"
    assert eq.port == 1865
    assert not eq.running
    assert not eq.stream_active


def test_supervisor_creation():
    """Test that Supervisor instance is created correctly."""
    supervisor = Supervisor()
    assert isinstance(supervisor.equipment, dict)
    assert len(supervisor.equipment) == 0


def test_equipment_added_to_supervisor():
    """Test that equipment is properly added to supervisor."""
    supervisor = Supervisor()
    eq = supervisor.add_equipment("test_device", "127.0.0.1", 1865)
    assert "test_device" in supervisor.equipment
    assert supervisor.equipment["test_device"] == eq


def test_pipe_communication(mock_hardware):
    """Test basic pipe communication between supervisor and equipment."""
    supervisor = Supervisor()
    eq = supervisor.add_equipment("test_device", "127.0.0.1", 1865)
    
    # Start the equipment process
    eq.start()
    
    try:
        # Verify pipe communication with ping
        eq.send_command("ping", {"id": "test-ping-1"})
        
        # Wait for response (with timeout)
        start_time = time.time()
        response = None
        while time.time() - start_time < 1.0:
            if eq.parent_conn.poll(0.1):
                response = eq.parent_conn.recv()
                break
            time.sleep(0.01)
        
        # Check response
        assert response is not None
        assert response.get("state") == "pong"
        assert response.get("data", {}).get("id") == "test-ping-1"
        assert response.get("data", {}).get("name") == "test_device"
    finally:
        # Clean up
        eq.stop()


def test_supervisor_ping_all(mock_hardware):
    """Test the ping_all method of Supervisor class."""
    supervisor = Supervisor()
    supervisor.add_equipment("device1", "127.0.0.1", 1865)
    supervisor.add_equipment("device2", "127.0.0.1", 1866)
    
    # Start all equipment
    supervisor.start_all()
    
    try:
        # Test ping_all functionality
        results = supervisor.ping_all()
        assert len(results) == 2
        assert results["device1"] is True
        assert results["device2"] is True
    finally:
        # Clean up
        supervisor.shutdown()


def test_equipment_configuration(mock_hardware):
    """Test equipment configuration through pipe."""
    supervisor = Supervisor()
    eq = supervisor.add_equipment("test_device", "127.0.0.1", 1865)
    
    # Start equipment
    eq.start()
    
    try:
        # Configure the equipment
        config = {"channels": "XY", "rate": 2000, "packet_size": 2}
        eq.send_command("configure", config)
        
        # Give some time for the equipment to process
        time.sleep(0.2)
        
        # Ping to verify it's still responsive after configuration
        eq.send_command("ping", {"id": "post-config"})
        
        # Wait for response
        start_time = time.time()
        response = None
        while time.time() - start_time < 1.0:
            if eq.parent_conn.poll(0.1):
                response = eq.parent_conn.recv()
                break
            time.sleep(0.01)
        
        assert response is not None
        assert response.get("state") == "pong"
    finally:
        # Clean up
        eq.stop()


def test_start_stop_collection(mock_hardware):
    """Test starting and stopping data collection."""
    supervisor = Supervisor()
    eq = supervisor.add_equipment("test_device", "127.0.0.1", 1865)
    
    # Start equipment
    eq.start()
    
    try:
        # Configure the equipment
        config = {"channels": "X", "rate": 1000, "packet_size": 0}
        eq.send_command("configure", config)
        time.sleep(0.1)
        
        # Start collection
        eq.send_command("start_collection", {"duration": 0.5})
        time.sleep(0.1)
        
        # Verify streaming is active with a ping
        eq.send_command("ping", {"id": "during-streaming"})
        
        # Wait for response
        start_time = time.time()
        response = None
        while time.time() - start_time < 1.0:
            if eq.parent_conn.poll(0.1):
                response = eq.parent_conn.recv()
                break
            time.sleep(0.01)
        
        assert response is not None
        
        # Stop collection
        eq.send_command("stop_collection", {})
        time.sleep(0.1)
        
        # Verify with another ping
        eq.send_command("ping", {"id": "after-streaming"})
        
        # Wait for response
        start_time = time.time()
        response = None
        while time.time() - start_time < 1.0:
            if eq.parent_conn.poll(0.1):
                response = eq.parent_conn.recv()
                break
            time.sleep(0.01)
        
        assert response is not None
    finally:
        # Clean up
        eq.stop()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])