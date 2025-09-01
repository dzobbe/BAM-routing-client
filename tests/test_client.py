import pytest
import base58
import base64
import json
from unittest.mock import AsyncMock, patch, MagicMock
from aioresponses import aioresponses
from bam_router.client import BamSmartClient

@pytest.fixture
def client():
    return BamSmartClient()

@pytest.fixture
def mock_signed_tx():
    # Create a mock signed transaction (just some bytes)
    return b"mock_signed_transaction_bytes_12345"

@pytest.fixture
def valid_jsonrpc_response():
    return {"jsonrpc": "2.0", "id": 1, "result": "mock_signature_123"}

@pytest.fixture
def error_jsonrpc_response():
    return {
        "jsonrpc": "2.0", 
        "id": 1, 
        "error": {"code": -32000, "message": "Transaction failed"}
    }

class TestBamSmartClient:
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_success(self, client, mock_signed_tx, valid_jsonrpc_response):
        """Test successful raw transaction sending."""
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=valid_jsonrpc_response, status=200)
                
                result = await client.send_transaction(mock_signed_tx)
                
                assert result == valid_jsonrpc_response
                assert result["result"] == "mock_signature_123"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_with_base58_encoding(self, client, mock_signed_tx):
        """Test transaction sending with base58 encoding."""
        mock_response = {"jsonrpc": "2.0", "id": 1, "result": "mock_signature_456"}
        
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=mock_response, status=200)
                
                result = await client.send_transaction(mock_signed_tx, encoding="base58")
                
                assert result == mock_response
                
                # Verify the request was made with base58 encoding
                # The actual encoding is handled in the client, but we can verify the request was made
                assert result["result"] == "mock_signature_456"
    
    @pytest.mark.asyncio
    async def test_send_transaction_with_base64_encoding(self, client, mock_signed_tx):
        """Test transaction sending with base64 encoding."""
        mock_response = {"jsonrpc": "2.0", "id": 1, "result": "mock_signature_789"}
        
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=mock_response, status=200)
                
                result = await client.send_transaction(mock_signed_tx, encoding="base64")
                
                assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_send_transaction_with_pre_encoded_string(self, client):
        """Test sending pre-encoded transaction string."""
        mock_response = {"jsonrpc": "2.0", "id": 1, "result": "mock_signature_string"}
        pre_encoded_tx = "pre_encoded_transaction_string"
        
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=mock_response, status=200)
                
                result = await client.send_transaction(pre_encoded_tx)
                
                assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_send_transaction_with_options(self, client, mock_signed_tx):
        """Test transaction sending with custom options."""
        mock_response = {"jsonrpc": "2.0", "id": 1, "result": "mock_signature_options"}
        
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=mock_response, status=200)
                
                result = await client.send_transaction(
                    mock_signed_tx,
                    skip_preflight=True,
                    preflight_commitment="processed",
                    max_retries=2
                )
                
                assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_send_transaction_invalid_encoding(self, client, mock_signed_tx):
        """Test that invalid encoding raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported encoding"):
            await client.send_transaction(mock_signed_tx, encoding="invalid")
    
    @pytest.mark.asyncio
    async def test_send_transaction_invalid_type(self, client):
        """Test that invalid transaction type raises ValueError."""
        with pytest.raises(ValueError, match="Transaction must be bytes or string"):
            await client.send_transaction(123)  # Invalid type
    
    @pytest.mark.asyncio
    async def test_send_transaction_rpc_error(self, client, mock_signed_tx):
        """Test handling of RPC error responses."""
        mock_error_response = {
            "jsonrpc": "2.0", 
            "id": 1, 
            "error": {"code": -32000, "message": "Transaction failed"}
        }
        
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=mock_error_response, status=200)
                
                with pytest.raises(ValueError, match="Transaction submission failed"):
                    await client.send_transaction(mock_signed_tx)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_invalid_response_format(self, client, mock_signed_tx):
        """Test handling of invalid response format."""
        mock_invalid_response = {"jsonrpc": "2.0", "id": 1}  # Missing result field
        
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=mock_invalid_response, status=200)
                
                with pytest.raises(ValueError, match="Invalid response format"):
                    await client.send_transaction(mock_signed_tx)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_with_pre_encoded_string(self, client, valid_jsonrpc_response):
        """Test sending pre-encoded transaction string."""
        pre_encoded_tx = "pre_encoded_transaction_string"
        
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=valid_jsonrpc_response, status=200)
                
                result = await client.send_transaction(pre_encoded_tx)
                
                assert result == valid_jsonrpc_response
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_with_options(self, client, mock_signed_tx, valid_jsonrpc_response):
        """Test transaction sending with custom options."""
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=valid_jsonrpc_response, status=200)
                
                result = await client.send_transaction(
                    mock_signed_tx,
                    skip_preflight=True,
                    preflight_commitment="processed",
                    max_retries=2
                )
                
                assert result == valid_jsonrpc_response
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_invalid_encoding(self, client, mock_signed_tx):
        """Test that invalid encoding raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported encoding"):
            await client.send_transaction(mock_signed_tx, encoding="invalid")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_invalid_type(self, client):
        """Test that invalid transaction type raises ValueError."""
        with pytest.raises(ValueError, match="Transaction must be bytes or string"):
            await client.send_transaction(123)  # Invalid type
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_transaction_rpc_error(self, client, mock_signed_tx, error_jsonrpc_response):
        """Test handling of RPC error responses."""
        with aioresponses() as m:
            # Mock the endpoint resolution to return a known URL
            with patch.object(client, '_resolve_endpoint', return_value="https://test.endpoint.com"):
                # Mock the HTTP POST request
                m.post("https://test.endpoint.com", payload=error_jsonrpc_response, status=200)
                
                with pytest.raises(ValueError, match="Transaction submission failed"):
                    await client.send_transaction(mock_signed_tx)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_region_resolution(self, client):
        """Test region resolution functionality."""
        # Test with specific region
        client_with_region = BamSmartClient(region_code="ny")
        
        with patch('bam_router.client.pick_fastest_region') as mock_pick:
            mock_pick.return_value = MagicMock(code="ny")
            
            # This should not call pick_fastest_region since we specified a region
            endpoint = await client_with_region._resolve_endpoint()
            mock_pick.assert_not_called()
            assert "ny.testnet.block-engine.jito.wtf" in endpoint
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_list_regions(self, client):
        """Test list_regions functionality."""
        with patch('bam_router.router.probe_regions') as mock_probe:
            mock_probe.return_value = [
                (MagicMock(code="ny", bam_url="https://ny.bam.com"), {"avg_ms": 50, "samples_ms": [45, 55]}),
                (MagicMock(code="dallas", bam_url="https://dallas.bam.com"), {"avg_ms": 100, "samples_ms": [95, 105]})
            ]
            
            with patch('bam_router.router._pick_fastest') as mock_pick:
                mock_pick.return_value = MagicMock(code="ny")
                
                regions = await client.list_regions()
                
                assert len(regions) == 2
                assert regions[0]["region"] == "ny"
                assert regions[0]["fastest"] == True
                assert regions[1]["region"] == "dallas"
                assert regions[1]["fastest"] == False
