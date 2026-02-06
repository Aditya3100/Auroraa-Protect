# --------------------------------
# Watermark algorithm configuration
# --------------------------------

from datetime import datetime, timezone


# -------------------------------
# Transform settings
# -------------------------------

DWT_WAVE = "haar"

DCT_POS_A = (3, 3)
DCT_POS_B = (2, 4)


# -------------------------------
# Embedding parameters
# -------------------------------

STRENGTH = 50
REPEAT = 40

# Length of signal
SIGNAL_LENGTH = 128

# -------------------------------
# Versioning
# -------------------------------

ALGORITHM_VERSION = "v3-continousid"


# -------------------------------
# Performance
# -------------------------------

MAX_CANDIDATES = 1000


# -------------------------------
# Confidence policy (correlation)
# -------------------------------

def confidence_to_status(score: float) -> str:

    if score >= 0.85:
        return "verified"

    elif score >= 0.70:
        return "most"

    elif score >= 0.55:
        return "likely"

    else:
        return "not_verified"


# -------------------------------
# Epoch helpers
# -------------------------------

def current_epoch() -> str:

    now = datetime.now(timezone.utc)

    quarter = (now.month - 1) // 3 + 1

    return f"{now.year}-Q{quarter}"


def previous_epochs(n: int = 4) -> list[str]:

    epochs = []

    now = datetime.now(timezone.utc)

    year = now.year
    quarter = (now.month - 1) // 3 + 1

    for _ in range(n):

        epochs.append(f"{year}-Q{quarter}")

        quarter -= 1

        if quarter == 0:
            quarter = 4
            year -= 1

    return epochs

# -------------------------------
# Result formatting
# -------------------------------

def interpret_verification_result(result: dict) -> dict:

    if result is None:
        raise ValueError("interpret_verification_result received None")

    confidence = result["confidence"]

    status = confidence_to_status(confidence)

    if status == "verified":
        label = "Strong Watermark Match"
        message = (
            "This image contains a strong Auroraa watermark "
            "matching this owner."
        )

    elif status == "most":
        label = "Moderate Watermark Match"
        message = (
            "This image contains a detectable Auroraa watermark, "
            "but has been modified."
        )

    elif status == "likely":
        label = "Weak Watermark Match"
        message = "A weak Auroraa watermark signal was detected."

    else:
        label = "Not Verified"
        message = "No reliable Auroraa watermark was detected."

    issued_on = result.get("created_at")

    if isinstance(issued_on, datetime):
        issued_on = issued_on.astimezone(timezone.utc).isoformat()

    response = {
        "verified": status != "not_verified",
        "issued_by_auroraa": status != "not_verified",
        "confidence": round(confidence, 3),
        "status": status,
        "message": {
            "label": label,
            "message": message,
        },
        "issued_on": issued_on,
    }

    if status == "verified" and result.get("owner_id"):

        response["owner"] = {
            "id": result["owner_id"]
        }

    return response
