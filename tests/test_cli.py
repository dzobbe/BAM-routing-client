import pytest
import base64
from unittest.mock import patch, AsyncMock
from bam_router.cli import _looks_b64

def test_looks_b64():
    """Test base64 detection."""
    valid_b64 = base64.b64encode(b"test data").decode()
    assert _looks_b64(valid_b64.encode()) is True
    
    invalid_data = b"not base64 data!"
    assert _looks_b64(invalid_data) is False    
    assert _looks_b64(b"") is True

def test_list_regions_command():
    """Test list regions command."""
    from bam_router.cli import list_regions
    
    mock_regions = [
        {
            "region": "ny",
            "bam_url": "http://ny.bam.jito.wtf",
            "tx_url": "https://ny.block-engine.jito.wtf/api/v1/transactions",
            "avg_ms": 100.0,
            "samples_ms": [100.0, 110.0, 90.0],
            "fastest": False
        },
        {
            "region": "dallas",
            "bam_url": "http://dallas.bam.jito.wtf",
            "tx_url": "https://dallas.block-engine.jito.wtf/api/v1/transactions",
            "avg_ms": 50.0,
            "samples_ms": [45.0, 55.0, 50.0],
            "fastest": True
        }
    ]
    
    with patch('bam_router.cli.BamSmartClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.list_regions.return_value = mock_regions
        
        list_regions()
        
        mock_client_class.assert_called_once()
        mock_client.list_regions.assert_called_once()

def test_send_raw_command():
    """Test send raw command."""
    from bam_router.cli import send_raw
    
    mock_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": "transaction_hash"
    }
    
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = b"test_transaction_data"
        
        with patch('bam_router.cli.BamSmartClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.send_transaction.return_value = mock_response
            
            send_raw("test_file.txt")
            
            mock_client_class.assert_called_once()
            mock_client.send_transaction.assert_called_once()
