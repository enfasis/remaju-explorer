import base64
from io import BytesIO
from pathlib import Path

from PIL import Image
from selectolax.parser import HTMLParser


def thumbnail_from_card(html: str, destination: Path) -> bool:
    tree = HTMLParser(html)
    image = tree.css_first("img")
    if image is None:
        return False
    source = image.attributes.get("src", "")
    if not source.startswith(("data:image/jpeg;base64,", "data:image/jpg;base64,", "data:image/png;base64,")):
        return False
    encoded = source.split(",", 1)[1]
    if len(encoded) > 8_000_000:
        raise ValueError("Source image exceeds thumbnail budget")
    content = base64.b64decode(encoded, validate=True)
    with Image.open(BytesIO(content)) as original:
        if original.width * original.height > 16_000_000:
            raise ValueError("Source image dimensions exceed thumbnail budget")
        image_data = original.convert("RGB")
        image_data.thumbnail((480, 320))
        image_data.save(destination, format="WEBP", quality=70)
    return True
