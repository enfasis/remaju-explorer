import base64
from io import BytesIO
from pathlib import Path

from PIL import Image

from remaju.source_media import thumbnail_from_card


def test_thumbnail_is_bounded_and_does_not_fetch_remote_images(tmp_path: Path) -> None:
    image = BytesIO()
    Image.new("RGB", (800, 600)).save(image, format="PNG")
    encoded = base64.b64encode(image.getvalue()).decode()
    target = tmp_path / "thumbnail.webp"
    assert thumbnail_from_card(f'<img src="data:image/png;base64,{encoded}">', target)
    with Image.open(target) as output:
        assert output.width <= 480
        assert output.height <= 320
    assert not thumbnail_from_card('<img src="https://example.com/image.jpg">', target)
