# --------------------------------
# Watermark algorithm configuration
# --------------------------------

from datetime import datetime, timezone

# Transform settings
DWT_WAVE = "haar"

# Fixed mid-frequency DCT coefficient positions
DCT_POS_A = (3, 3)
DCT_POS_B = (2, 4)

# Robust embedding parameters (industry-style)
STRENGTH = 24.0        # embedding amplitude
REPEAT = 20            # redundancy per bit
HASH_BITS = 64  # increase to 64 if needed

ALGORITHM_VERSION="v3-hmac"

# Performance / safety limits
MAX_CANDIDATES = 1000

def confidence_to_status(confidence: float) -> str:
    if confidence >= 0.75:
        return "verified"
    elif confidence >= 0.6:
        return "most"
    elif confidence >= 0.55:
        return "likely"
    else:
        return "not_verified"


# def interpret_verification_result(result: dict) -> dict:
#     if result is None:
#         raise ValueError("interpret_verification_result received None")

#     confidence = result["confidence"]
#     status = confidence_to_status(confidence)

#     if status == "verified":
#         label = "Verified Original"
#         message = (
#             "This image is verified as authentic and issued by Auroraa for this owner."
#         )
#     elif status == "most":
#         label = "Verified, but Modified"
#         message = (
#             "This image is verified as authentic and issued by Auroraa, "
#             "but it has been modified."
#         )
#     elif status == "likely":
#         label = "Likely Authentic"
#         message = (
#             "This image likely belongs to this owner, but it has been heavily modified."
#         )
#     else:
#         label = "Not Verified"
#         message = "This image could not be verified as authentic."

#     response = {
#         "verified": status != "not_verified",
#         "issued_by_auroraa": status != "not_verified",
#         "confidence": round(confidence, 3),
#         "status": status,
#         "message": {
#             "label": label,
#             "message": message
#         }
#     }

#     # ✅ ONLY expose identity on strong DB-scan verification
#     if status == "verified" and result.get("owner_id"):
#         response["owner"] = {
#             "id": result["owner_id"]
#         }

#     return response

def interpret_verification_result(result: dict) -> dict:
    if result is None:
        raise ValueError("interpret_verification_result received None")

    confidence = result["confidence"]
    status = confidence_to_status(confidence)

    if status == "verified":
        label = "Verified Original"
        message = (
            "This image is verified as authentic and issued by Auroraa for this owner."
        )
    elif status == "most":
        label = "Verified, but Modified"
        message = (
            "This image is verified as authentic and issued by Auroraa, "
            "but it has been modified."
        )
    elif status == "likely":
        label = "Likely Authentic"
        message = (
            "This image likely belongs to this owner, but it has been heavily modified."
        )
    else:
        label = "Not Verified"
        message = "This image could not be verified as authentic."

    issued_on = result.get("created_at")

    # ensure ISO 8601 if datetime object
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

    # ✅ ONLY expose identity on strong DB-scan verification
    if status == "verified" and result.get("owner_id"):
        response["owner"] = {
            "id": result["owner_id"]
        }

    return response
