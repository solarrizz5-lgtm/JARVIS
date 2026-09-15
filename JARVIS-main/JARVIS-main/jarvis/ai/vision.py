import base64
from io import BytesIO
from PIL import ImageGrab
from jarvis import config
from jarvis.utils.logger import log_error

def capture_screen_b64():
    """
    Captures the full screen, scales it down by 50% for payload efficiency, 
    converts to RGB (preventing JPEG save errors with RGBA/P modes), 
    and returns base64 encoding along with original native resolution dimensions.
    """
    try:
        raw_screenshot = ImageGrab.grab()
        
        # Ensure image mode is RGB before saving as JPEG (fixes RGBA/palette errors on some OSs)
        if raw_screenshot.mode in ("RGBA", "P"):
            raw_screenshot = raw_screenshot.convert("RGB")
            
        native_width, native_height = raw_screenshot.size
        
        # Scale to half resolution for faster token processing while preserving aspect ratio
        resized_width = max(1, native_width // 2)
        resized_height = max(1, native_height // 2)

        resized_screenshot = raw_screenshot.resize((resized_width, resized_height))
        memory_buffer = BytesIO()

        resized_screenshot.save(
            memory_buffer,
            format="JPEG",
            quality=80,
            optimize=True
        )

        b64_data = base64.b64encode(memory_buffer.getvalue()).decode("utf-8")
        return b64_data, native_width, native_height, raw_screenshot

    except Exception as e:
        log_error(f"Failed to capture screen state: {e}")
        raise e