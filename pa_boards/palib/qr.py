"""QR codes for the participant links, sized for slides (>= 1000 px)."""
from io import BytesIO

import qrcode
from PIL import Image

SLIDE_SIZE = 1200


def participant_url(base_url: str, key: str) -> str:
    return f"{base_url.rstrip('/')}/?board={key}"


def png(url: str, size: int = SLIDE_SIZE) -> bytes:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size, size), Image.NEAREST)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
