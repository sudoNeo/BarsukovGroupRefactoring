import os
import pytest
import multiprocessing
from src.main import test

@pytest.fixture
def mock_hardware():
    os.environ['MOCK_HARDWARE'] = 'True'
    yield
    os.environ.pop('MOCK_HARDWARE', None)

@pytest.fixture
def test_options():
    return {
        '--address': '127.0.0.1',
        '--duration': 1,
        '--file': 'test_output.csv',
        '--ints': False,
        '--length': 0,
        '--port': 1865,
        '--rate': 1000,
        '--silent': True,
        '--thread': False,
        '--vars': 'XY'
    }

def test_streaming(mock_hardware, test_options):
    p = multiprocessing.Process(target=test, args=(test_options,))
    p.start()
    p.join()
    assert os.path.exists('test_output.csv')
    with open('test_output.csv', 'r') as f:
        lines = f.readlines()
        assert len(lines) > 1
        assert lines[0].strip() == 'timestamp,X,Y'