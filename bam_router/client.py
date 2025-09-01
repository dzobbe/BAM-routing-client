import aiohttp
import base58
from typing import Any, Union
from .router import pick_fastest_region, tx_endpoint_for
import asyncio

class BamSmartClient:
    def __init__(self, region_code: str | None = None):
        self.region_code = region_code

    async def _resolve_endpoint(self) -> str:
        from .regions import REGIONS
        
        if self.region_code:
            for region in REGIONS:
                if region.code == self.region_code:
                    return tx_endpoint_for(region)
            raise ValueError(f"Unknown region code: {self.region_code}")
        
        # Pick fastest region automatically
        fastest = await pick_fastest_region()
        return tx_endpoint_for(fastest)

    async def send_transaction(
        self, 
        transaction: Union[bytes, str], 
        encoding: str = "base58",
        skip_preflight: bool = False,
        preflight_commitment: str = "confirmed",
        max_retries: int = 3
    ) -> dict[str, Any]:
        """
        Submit a signed transaction using JSON-RPC.
        
        Args:
            transaction: The signed transaction as bytes or base58-encoded string
            encoding: Encoding format for the transaction ("base58" or "base64")
            skip_preflight: Whether to skip preflight checks
            preflight_commitment: Commitment level for preflight checks
            max_retries: Maximum number of retry attempts
            
        Returns:
            JSON-RPC response from the transaction submission
            
        Raises:
            ValueError: If transaction format is invalid
            aiohttp.ClientError: If network request fails
        """
        endpoint = await self._resolve_endpoint()
        
        if isinstance(transaction, str):
            # Assume it's already base58 encoded
            tx_encoded = transaction
        elif isinstance(transaction, bytes):
            if encoding == "base58":
                tx_encoded = base58.b58encode(transaction).decode("ascii")
            elif encoding == "base64":
                import base64
                tx_encoded = base64.b64encode(transaction).decode("ascii")
            else:
                raise ValueError(f"Unsupported encoding: {encoding}")
        else:
            raise ValueError("Transaction must be bytes or string")
        
        print(f"Sending transaction ({len(tx_encoded)} chars) to {endpoint}")
        
        params = [tx_encoded]
        
        options = {}
        if skip_preflight:
            options["skipPreflight"] = skip_preflight
        if preflight_commitment:
            options["preflightCommitment"] = preflight_commitment
            
        if options:
            params.append(options)
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": params,
        }
        
        # Retry logic
        last_error = None
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(endpoint, json=payload, timeout=30) as response:
                        response.raise_for_status()
                        result = await response.json()
                        
                        # Validate response
                        if "error" in result:
                            error_msg = result["error"].get("message", "Unknown error")
                            raise ValueError(f"Transaction submission failed: {error_msg}")
                        
                        if "result" not in result:
                            raise ValueError("Invalid response format: missing 'result' field")
                        
                        return result
                        
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed, retrying... ({e})")
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                else:
                    raise e
            except Exception as e:
                # For non-network errors, don't retry
                raise e
        
        # This should never be reached, but just in case
        raise last_error or RuntimeError("Unexpected error in send_transaction")


    async def list_regions(self) -> list[dict]:
        """Get latency information for all regions."""
        from .router import probe_regions, _pick_fastest, tx_endpoint_for
        
        results = await probe_regions()
        fastest = _pick_fastest(results)
        
        regions_info = []
        for region, metrics in results:
            regions_info.append({
                "region": region.code,
                "bam_url": region.bam_url,
                "tx_url": tx_endpoint_for(region),
                "avg_ms": metrics["avg_ms"],
                "samples_ms": metrics["samples_ms"],
                "fastest": region.code == fastest.code,
            })
        
        return regions_info
