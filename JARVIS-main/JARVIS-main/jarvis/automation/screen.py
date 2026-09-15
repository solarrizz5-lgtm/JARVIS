import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import mss
from jarvis import config
from jarvis.utils.logger import log_error

def draw_grid_overlay(image: Image.Image, step: int = 100) -> Image.Image:
    """Draws a coordinate grid over a PIL Image to help models click precisely."""
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    width, height = img_copy.size
    
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Draw vertical grid lines and X-axis labels
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=(255, 0, 0), width=1)
        draw.text((x + 2, 2), str(x), fill=(255, 0, 0), font=font)

    # Draw horizontal grid lines and Y-axis labels
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=1)
        draw.text((2, y + 2), str(y), fill=(255, 0, 0), font=font)
        
    return img_copy

def capture_screen() -> Image.Image:
    """Captures the primary screen, applying a coordinate grid overlay if configured."""
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            image = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
        # Check if the selected model or config requests grid overlay
        model_name = getattr(config, "MODEL_NAME", "").lower()
        if "flash-lite" in model_name or getattr(config, "ENABLE_GRID_OVERLAY", False):
            image = draw_grid_overlay(image, step=100)
            
        return image
    except Exception as error:
        log_error(f"Screen capture error: {error}")
        return Image.new("RGB", (1920, 1080), color="black")