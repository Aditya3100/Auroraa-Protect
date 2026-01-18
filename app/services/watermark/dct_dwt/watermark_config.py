import os
import hashlib
import numpy as np
import zlib
from reedsolo import RSCodec

AURORAA_SECRET = os.getenv("AURORAA_WATERMARK_SECRET", "auroraa-prod-secret")

# Transform config
DWT_WAVE = "haar"
DCT_POS_A = (3, 3)
DCT_POS_B = (2, 4)

STRENGTH = 6.0
REPEAT = 12

# Payload framing
MAGIC = 0xA3F1
VERSION = 1

# Reed–Solomon ECC (Python 3.13 safe)
RS_PARITY = 16
_rs = RSCodec(RS_PARITY)

# ---------------------------------------------------------
def bytes_to_bits(b: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8))

def bits_to_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits).tobytes()

def seeded_rng(owner_id: str) -> int:
    return int.from_bytes(
        hashlib.sha256((owner_id + AURORAA_SECRET).encode()).digest()[:8],
        "big"
    )

def generate_payload_bits(owner_id: str) -> np.ndarray:
    payload = f"{owner_id}:{AURORAA_SECRET}".encode()
    digest = hashlib.sha256(payload).digest()[:16]

    framed = (
        MAGIC.to_bytes(2, "big") +
        VERSION.to_bytes(1, "big") +
        digest
    )
    crc = zlib.crc32(framed).to_bytes(4, "big")

    return bytes_to_bits(framed + crc)

def ecc_encode(bits: np.ndarray) -> np.ndarray:
    data = bits_to_bytes(bits)
    encoded = _rs.encode(data)
    return bytes_to_bits(encoded)

def ecc_decode(bits: np.ndarray) -> bytes | None:
    try:
        raw = bits_to_bytes(bits)
        return _rs.decode(raw)[0]
    except Exception:
        return None
