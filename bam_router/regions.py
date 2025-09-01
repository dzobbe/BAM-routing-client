from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Region:
    code: str         # "ny", "dallas", "slc"
    bam_url: str      # Scheduler URL from BAM docs
    tx_url: Optional[str]  # Client TX submission URL 

REGIONS: list[Region] = [
    Region(
        code="ny",
        bam_url="http://ny.testnet.bam.jito.wtf",
        tx_url="https://ny.testnet.block-engine.jito.wtf/api/v1/transactions",
    ),
    Region(
        code="dallas",
        bam_url="http://dallas.testnet.bam.jito.wtf",
        tx_url="https://dallas.testnet.block-engine.jito.wtf/api/v1/transactions",
    ),
    Region(
        code="slc",
        bam_url="http://slc.testnet.bam.jito.wtf",
        tx_url=None,  # add when exposed; router will fallback
    ),
]

# Fallback catch-all testnet endpoint (routes to a region chosen by provider)
FALLBACK_TESTNET_TX = "https://testnet.block-engine.jito.wtf/api/v1/transactions"
