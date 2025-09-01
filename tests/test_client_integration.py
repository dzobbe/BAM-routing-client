import pytest
import asyncio
import base58
import base64
import json
import subprocess
import time
import signal
import os
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, patch, MagicMock
from aioresponses import aioresponses

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.system_program import TransferParams, transfer
from solders.pubkey import Pubkey

from bam_router.client import BamSmartClient


class LocalSolanaValidator:
    """Manages a local Solana test validator for integration testing."""
    
    def __init__(self, rpc_port: int = 8899, faucet_port: int = 9900):
        self.rpc_port = rpc_port
        self.faucet_port = faucet_port
        self.process: Optional[subprocess.Popen] = None
        self.rpc_url = f"http://localhost:{rpc_port}"
        self.faucet_url = f"http://localhost:{faucet_port}"
        
    async def start(self):
        """Start the local Solana test validator."""
        if self.process is not None:
            return
            
        cmd = [
            "solana-test-validator",
            "--rpc-port", str(self.rpc_port),
            "--faucet-port", str(self.faucet_port),
            "--reset",  # Start fresh each time
            "--quiet"   # Reduce output noise
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # Wait for validator to start
            await self._wait_for_validator()
            print(f"✅ Local Solana validator started on {self.rpc_url}")
            
        except FileNotFoundError:
            pytest.skip("solana-test-validator not found. Install Solana CLI tools.")
        except Exception as e:
            print(f"❌ Failed to start validator: {e}")
            raise
    
    async def stop(self):
        """Stop the local Solana test validator."""
        if self.process is None:
            return
            
        try:
            if os.name != 'nt':
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            else:
                self.process.terminate()
            
            self.process.wait(timeout=10)
            print("✅ Local Solana validator stopped")
        except subprocess.TimeoutExpired:
            self.process.kill()
        except Exception as e:
            print(f"Warning: Error stopping validator: {e}")
        finally:
            self.process = None
    
    async def _wait_for_validator(self, timeout: int = 30):
        """Wait for the validator to be ready."""
        start_time = time.time()
        async with AsyncClient(self.rpc_url) as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get_health()
                    if response.value == "ok":
                        return
                except Exception:
                    pass
                await asyncio.sleep(1)
        
        raise TimeoutError("Validator failed to start within timeout")


@pytest.fixture(scope="session")
async def local_validator():
    """Session-scoped fixture for local Solana validator."""
    validator = LocalSolanaValidator()
    await validator.start()
    yield validator
    await validator.stop()


@pytest.fixture
async def solana_client(local_validator):
    """Async Solana client connected to local validator."""
    async with AsyncClient(local_validator.rpc_url) as client:
        yield client


@pytest.fixture
def test_keypair():
    """Generate a test keypair for transactions."""
    return Keypair()


@pytest.fixture
async def funded_keypair(solana_client, test_keypair):
    """Keypair with SOL balance for testing."""
    # Request airdrop
    airdrop_sig = await solana_client.request_airdrop(
        test_keypair.pubkey(), 
        1_000_000_000  # 1 SOL
    )
    await solana_client.confirm_transaction(airdrop_sig.value)
    
    # Verify balance
    balance = await solana_client.get_balance(test_keypair.pubkey())
    assert balance.value > 0
    
    return test_keypair


@pytest.fixture
def bam_client():
    """BAM client instance for testing."""
    return BamSmartClient()


class TestBamClientIntegration:
    """Integration tests using local Solana validator."""
    
    pytestmark = pytest.mark.integration
    
    @pytest.mark.asyncio
    async def test_send_real_transaction_success(
        self, 
        bam_client, 
        solana_client, 
        funded_keypair,
        local_validator
    ):
        """Test sending a real transaction through BAM client."""
        # Create a real transfer transaction
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=1_000_000  # 0.001 SOL
            )
        )
        
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        # Get recent blockhash
        recent_blockhash = await solana_client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        
        # Sign transaction
        transaction.sign([funded_keypair])
        
        # Mock BAM client to use local validator
        with patch.object(bam_client, '_resolve_endpoint', return_value=local_validator.rpc_url):
            # Send through BAM client
            result = await bam_client.send_transaction(
                transaction.serialize(),
                encoding="base64"
            )
            
            assert "result" in result
            assert result["result"] is not None
            
            # Verify transaction was processed
            tx_sig = result["result"]
            confirmation = await solana_client.confirm_transaction(tx_sig)
            assert confirmation.value.err is None
    
    @pytest.mark.asyncio
    async def test_send_transaction_with_base58_encoding(
        self, 
        bam_client, 
        solana_client, 
        funded_keypair,
        local_validator
    ):
        """Test sending transaction with base58 encoding."""
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=500_000
            )
        )
        
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        recent_blockhash = await solana_client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        transaction.sign([funded_keypair])
        
        with patch.object(bam_client, '_resolve_endpoint', return_value=local_validator.rpc_url):
            result = await bam_client.send_transaction(
                transaction.serialize(),
                encoding="base58"
            )
            
            assert "result" in result
            tx_sig = result["result"]
            confirmation = await solana_client.confirm_transaction(tx_sig)
            assert confirmation.value.err is None
    
    @pytest.mark.asyncio
    async def test_send_transaction_with_options(
        self, 
        bam_client, 
        solana_client, 
        funded_keypair,
        local_validator
    ):
        """Test sending transaction with custom options."""
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=250_000
            )
        )
        
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        recent_blockhash = await solana_client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        transaction.sign([funded_keypair])
        
        with patch.object(bam_client, '_resolve_endpoint', return_value=local_validator.rpc_url):
            result = await bam_client.send_transaction(
                transaction.serialize(),
                encoding="base64",
                skip_preflight=True,
                preflight_commitment="processed",
                max_retries=2
            )
            
            assert "result" in result
            tx_sig = result["result"]
            confirmation = await solana_client.confirm_transaction(tx_sig)
            assert confirmation.value.err is None
    
    @pytest.mark.asyncio
    async def test_send_invalid_transaction_handling(
        self, 
        bam_client, 
        local_validator
    ):
        """Test handling of invalid transaction data."""
        invalid_tx_data = b"invalid_transaction_data"
        
        with patch.object(bam_client, '_resolve_endpoint', return_value=local_validator.rpc_url):
            with pytest.raises(ValueError, match="Transaction submission failed"):
                await bam_client.send_transaction(invalid_tx_data, encoding="base64")
    
    @pytest.mark.asyncio
    async def test_send_transaction_insufficient_funds(
        self, 
        bam_client, 
        solana_client, 
        local_validator
    ):
        """Test handling of insufficient funds error."""
        # Create keypair without funds
        poor_keypair = Keypair()
        recipient = Keypair()
        
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=poor_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=1_000_000
            )
        )
        
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        recent_blockhash = await solana_client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        transaction.sign([poor_keypair])
        
        with patch.object(bam_client, '_resolve_endpoint', return_value=local_validator.rpc_url):
            with pytest.raises(ValueError, match="Transaction submission failed"):
                await bam_client.send_transaction(transaction.serialize(), encoding="base64")
    
    @pytest.mark.asyncio
    async def test_send_transaction_network_failure(
        self, 
        bam_client, 
        funded_keypair
    ):
        """Test handling of network failures."""
        transaction_data = b"some_transaction_data"
        
        # Mock network failure
        with patch.object(bam_client, '_resolve_endpoint', return_value="http://invalid-endpoint:9999"):
            with pytest.raises(Exception):  # Should raise aiohttp.ClientError or similar
                await bam_client.send_transaction(transaction_data, encoding="base64")
    
    @pytest.mark.asyncio
    async def test_send_transaction_retry_logic(
        self, 
        bam_client, 
        solana_client, 
        funded_keypair,
        local_validator
    ):
        """Test retry logic with intermittent failures."""
        # This test is simplified to avoid circular mocking
        # The actual retry logic is tested in the error conditions test file
        
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=100_000
            )
        )
        
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        recent_blockhash = await solana_client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        transaction.sign([funded_keypair])
        
        # Test that the transaction can be sent successfully
        with patch.object(bam_client, '_resolve_endpoint', return_value=local_validator.rpc_url):
            result = await bam_client.send_transaction(
                transaction.serialize(),
                encoding="base64",
                max_retries=3
            )
            
            assert "result" in result
            tx_sig = result["result"]
            confirmation = await solana_client.confirm_transaction(tx_sig)
            assert confirmation.value.err is None
    
    @pytest.mark.asyncio
    async def test_concurrent_transactions(
        self, 
        bam_client, 
        solana_client, 
        funded_keypair,
        local_validator
    ):
        """Test sending multiple transactions concurrently."""
        recipients = [Keypair() for _ in range(3)]
        
        async def send_transfer(recipient):
            transfer_ix = transfer(
                TransferParams(
                    from_pubkey=funded_keypair.pubkey(),
                    to_pubkey=recipient.pubkey(),
                    lamports=50_000
                )
            )
            
            transaction = Transaction()
            transaction.add(transfer_ix)
            
            recent_blockhash = await solana_client.get_latest_blockhash()
            transaction.recent_blockhash = recent_blockhash.value.blockhash
            transaction.sign([funded_keypair])
            
            with patch.object(bam_client, '_resolve_endpoint', return_value=local_validator.rpc_url):
                return await bam_client.send_transaction(
                    transaction.serialize(),
                    encoding="base64"
                )
        
        # Send transactions concurrently
        tasks = [send_transfer(recipient) for recipient in recipients]
        results = await asyncio.gather(*tasks)
        
        # Verify all transactions succeeded
        for result in results:
            assert "result" in result
            tx_sig = result["result"]
            confirmation = await solana_client.confirm_transaction(tx_sig)
            assert confirmation.value.err is None
    
    @pytest.mark.asyncio
    async def test_transaction_encoding_validation(
        self, 
        bam_client
    ):
        """Test validation of transaction encoding formats."""
        tx_data = b"test_transaction_data"
        
        # Test valid encodings
        with patch.object(bam_client, '_resolve_endpoint', return_value="http://test.com"):
            with aioresponses() as m:
                m.post("http://test.com", payload={"jsonrpc": "2.0", "id": 1, "result": "sig"})
                
                # Should work with base58
                result1 = await bam_client.send_transaction(tx_data, encoding="base58")
                assert "result" in result1
                
                
        # Test invalid encoding
        with pytest.raises(ValueError, match="Unsupported encoding"):
            await bam_client.send_transaction(tx_data, encoding="invalid")
        
        # Test invalid transaction type
        with pytest.raises(ValueError, match="Transaction must be bytes or string"):
            await bam_client.send_transaction(123)
    
    @pytest.mark.asyncio
    async def test_region_resolution_integration(
        self, 
        bam_client, 
        solana_client, 
        funded_keypair,
        local_validator
    ):
        """Test region resolution with real endpoint."""
        recipient = Keypair()
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=funded_keypair.pubkey(),
                to_pubkey=recipient.pubkey(),
                lamports=75_000
            )
        )
        
        transaction = Transaction()
        transaction.add(transfer_ix)
        
        recent_blockhash = await solana_client.get_latest_blockhash()
        transaction.recent_blockhash = recent_blockhash.value.blockhash
        transaction.sign([funded_keypair])
        
        # Test with specific region (mocked to local validator)
        client_with_region = BamSmartClient(region_code="test")
        
        with patch.object(client_with_region, '_resolve_endpoint', return_value=local_validator.rpc_url):
            result = await client_with_region.send_transaction(
                transaction.serialize(),
                encoding="base64"
            )
            
            assert "result" in result
            tx_sig = result["result"]
            confirmation = await solana_client.confirm_transaction(tx_sig)
            assert confirmation.value.err is None
