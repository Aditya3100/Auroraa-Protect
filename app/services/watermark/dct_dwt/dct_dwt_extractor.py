import cv2
import numpy as np
import pywt

def extract_confidence(
    image_bytes: bytes,
    bits: np.ndarray,
    repeat: int = 20
) -> float:

    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    y = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32)

    LL, _ = pywt.dwt2(y, "haar")

    votes = [[] for _ in range(len(bits))]
    bit_idx = 0
    rep = 0

    for i in range(0, LL.shape[0] - 8, 8):
        for j in range(0, LL.shape[1] - 8, 8):
            if bit_idx >= len(bits):
                break

            dct = cv2.dct(LL[i:i+8, j:j+8])
            bit = 1 if dct[3, 3] > dct[2, 4] else 0
            votes[bit_idx].append(bit)

            rep += 1
            if rep >= repeat:
                rep = 0
                bit_idx += 1

        if bit_idx >= len(bits):
            break

    extracted = np.array([
        1 if np.mean(v) > 0.5 else 0 for v in votes
    ])

    return float(np.mean(extracted == bits))
