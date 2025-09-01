import socket
import time
from urllib.parse import urlparse

def _tcp_ping_once(host: str, port: int, timeout: float) -> float | None:
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        end = time.time()
        return (end - start) * 1000.0
    except Exception:
        return None

async def tcp_ping(url: str, count: int = 3, timeout: float = 0.75) -> dict:
    """Simple TCP ping to measure latency."""
    parsed = urlparse(url)
    host = parsed.hostname or url
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    
    samples = []
    for _ in range(count):
        result = _tcp_ping_once(host, port, timeout)
        samples.append(result)
    
    # Calculate average from valid samples
    valid_samples = [x for x in samples if x is not None]
    avg = sum(valid_samples) / len(valid_samples) if valid_samples else None
    
    return {"avg_ms": avg, "samples_ms": samples}
