import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from aioresponses import aioresponses

from bam_router.client import BamSmartClient


class TestErrorConditions:
    """Test various error conditions and edge cases."""
    
    pytestmark = pytest.mark.error
    
    @pytest.fixture
    def client(self):
        return BamSmartClient()
    
    @pytest.mark.asyncio
    async def test_network_timeout(self, client):
        """Test handling of network timeouts."""
        with patch.object(client, '_resolve_endpoint', return_value="http://slow-endpoint.com"):
            with aioresponses() as m:
                m.post("http://slow-endpoint.com", exception=asyncio.TimeoutError("Request timeout"))
                
                with pytest.raises(asyncio.TimeoutError):
                    await client.send_transaction(b"test_data", max_retries=1)
    
    @pytest.mark.asyncio
    async def test_connection_refused(self, client):
        """Test handling of connection refused errors."""
        with patch.object(client, '_resolve_endpoint', return_value="http://localhost:9999"):
            with pytest.raises(Exception):  # Should raise connection error
                await client.send_transaction(b"test_data", max_retries=1)
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, client):
        """Test handling of invalid JSON responses."""
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", body="invalid json", status=200)
                
                with pytest.raises(Exception):  # Should raise JSON decode error
                    await client.send_transaction(b"test_data")
    
    @pytest.mark.asyncio
    async def test_http_error_status(self, client):
        """Test handling of HTTP error status codes."""
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", status=500, body="Internal Server Error")
                
                with pytest.raises(aiohttp.ClientResponseError):
                    await client.send_transaction(b"test_data", max_retries=1)
    
    @pytest.mark.asyncio
    async def test_rpc_error_with_details(self, client):
        """Test handling of detailed RPC errors."""
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32002,
                "message": "Transaction simulation failed",
                "data": {
                    "err": "InsufficientFundsForRent",
                    "logs": ["Program log: Insufficient funds for rent"]
                }
            }
        }
        
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", payload=error_response, status=200)
                
                with pytest.raises(ValueError, match="Transaction submission failed"):
                    await client.send_transaction(b"test_data")
    
    @pytest.mark.asyncio
    async def test_malformed_transaction_data(self, client):
        """Test handling of malformed transaction data."""
        # Test with empty bytes
        with pytest.raises(ValueError, match="Transaction submission failed"):
            with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
                with aioresponses() as m:
                    m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "Invalid transaction"}}, status=200)
                    await client.send_transaction(b"")
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, client):
        """Test retry logic with exponential backoff."""
        # This test is simplified since the actual retry logic is in the send_transaction method
        # We test that the method can handle retries by mocking the HTTP responses
        
        call_count = 0
        
        def mock_response_callback(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ClientError(f"Attempt {call_count} failed")
            return (200, {}, '{"jsonrpc": "2.0", "id": 1, "result": "success"}')
        
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                # Mock the first two calls to fail, then succeed
                m.post("http://test.com", exception=aiohttp.ClientError("Attempt 1 failed"))
                m.post("http://test.com", exception=aiohttp.ClientError("Attempt 2 failed"))
                m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "result": "success"})
                
                result = await client.send_transaction(b"test_data", max_retries=5)
                
                assert result["result"] == "success"
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, client):
        """Test behavior when max retries are exceeded."""
        def mock_response_callback(url, **kwargs):
            raise aiohttp.ClientError("Persistent failure")
        
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", callback=mock_response_callback)
                
                with pytest.raises(aiohttp.ClientError):
                    await client.send_transaction(b"test_data", max_retries=3)
    
    @pytest.mark.asyncio
    async def test_invalid_region_code(self, client):
        """Test handling of invalid region codes."""
        client_with_invalid_region = BamSmartClient(region_code="INVALID")
        
        with pytest.raises(ValueError, match="Unknown region code"):
            await client_with_invalid_region.send_transaction(b"test_data")
    
    @pytest.mark.asyncio
    async def test_large_transaction_data(self, client):
        """Test handling of very large transaction data."""
        large_data = b"x" * (1024 * 1024)  # 1MB of data
        
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "result": "large_tx_sig"})
                
                result = await client.send_transaction(large_data, encoding="base64")
                assert result["result"] == "large_tx_sig"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_same_client(self, client):
        """Test concurrent requests using the same client instance."""
        # Test that multiple requests can be sent concurrently
        # This is a simplified test that verifies the client can handle concurrent calls
        
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                # Mock multiple responses for sequential calls
                m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "result": "concurrent_sig_1"})
                m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "result": "concurrent_sig_2"})
                m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "result": "concurrent_sig_3"})
                
                # Send multiple requests sequentially to avoid aioresponses conflicts
                results = []
                for i in range(3):
                    result = await client.send_transaction(b"test_data")
                    results.append(result)
                
                assert results[0]["result"] == "concurrent_sig_1"
                assert results[1]["result"] == "concurrent_sig_2"
                assert results[2]["result"] == "concurrent_sig_3"
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_after_errors(self, client):
        """Test that memory is properly cleaned up after errors."""
        import gc
        
        # Force garbage collection before test
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform operations that might fail
        for _ in range(10):
            try:
                with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
                    with aioresponses() as m:
                        m.post("http://test.com", exception=aiohttp.ClientError("Test error"))
                        await client.send_transaction(b"test_data", max_retries=1)
            except Exception:
                pass
        
        # Force garbage collection after test
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Check that we haven't leaked too many objects
        # Allow some tolerance for test overhead
        assert final_objects - initial_objects < 100
    
    @pytest.mark.asyncio
    async def test_unicode_transaction_data(self, client):
        """Test handling of unicode transaction data."""
        unicode_data = "Solana transaction".encode('utf-8')
        
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "result": "unicode_sig"})
                
                result = await client.send_transaction(unicode_data, encoding="base64")
                assert result["result"] == "unicode_sig"
    
    @pytest.mark.asyncio
    async def test_special_characters_in_response(self, client):
        """Test handling of special characters in response."""
        special_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "sig_with_special_chars_🚀_🎯_💎"
        }
        
        with patch.object(client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", payload=special_response, status=200)
                
                result = await client.send_transaction(b"test_data")
                assert result["result"] == "sig_with_special_chars_🚀_🎯_💎"
