import typer
import asyncio
import sys
import base64
from .client import BamSmartClient

app = typer.Typer(help="BAM Smart Routing Client")

def list_regions():
    """Show latency to all regions and highlight the fastest."""
    async def run():
        client = BamSmartClient()
        regions = await client.list_regions()
        
        # Sort by latency
        regions.sort(key=lambda x: (x["avg_ms"] is None, x["avg_ms"] or 999999))
        
        for region in regions:
            mark = "★" if region["fastest"] else " "
            avg = "n/a" if region["avg_ms"] is None else f"{region['avg_ms']:.1f} ms"
            print(f"{mark} {region['region']:6}  avg={avg:8}  tx={region['tx_url']}")
    
    asyncio.run(run())

def send_raw(
    tx_path: str = typer.Argument(..., help="Path to signed transaction file"),
    region: str = typer.Option(None, help="Region code: ny|dallas|slc"),
    encoding: str = typer.Option("auto", help="auto|base64|raw"),
):
    """Submit a signed transaction."""
    async def run():
        # Read transaction data
        with open(tx_path, "rb") as f:
            data = f.read()
        
        # Handle encoding
        if encoding == "base64" or (encoding == "auto" and _looks_b64(data)):
            data = base64.b64decode(data)
        
        # Send transaction
        client = BamSmartClient(region_code=region)
        result = await client.send_transaction(data)
        print(result)
    
    asyncio.run(run())

def _looks_b64(data: bytes) -> bool:
    """Check if data looks like base64."""
    try:
        base64.b64decode(data, validate=True)
        return True
    except:
        return False

app.command()(list_regions)
app.command()(send_raw)

if __name__ == "__main__":
    app()
