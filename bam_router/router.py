import asyncio
from .regions import REGIONS, Region, FALLBACK_TESTNET_TX
from .latency import tcp_ping

async def probe_regions() -> list[tuple[Region, dict]]:
    # Create coroutines for all regions to run in parallel
    coros = []
    for region in REGIONS:
        target = region.tx_url or region.bam_url
        coros.append(tcp_ping(target))
    
    metrics_list = await asyncio.gather(*coros)
    results = list(zip(REGIONS, metrics_list))
    return results 

def _pick_fastest(results: list[tuple[Region, dict]]) -> Region:
    # Find regions with valid latency data
    valid_results = [(r, m["avg_ms"]) for r, m in results if m["avg_ms"] is not None]
    
    if not valid_results:
        # Default to New York if no regions are reachable
        return next(r for r in REGIONS if r.code == "ny")
    
    # Sort by latency and return fastest
    valid_results.sort(key=lambda x: x[1])
    return valid_results[0][0]

async def pick_fastest_region() -> Region:
    results = await probe_regions()
    return _pick_fastest(results)

def tx_endpoint_for(region: Region) -> str:
    return region.tx_url or FALLBACK_TESTNET_TX
