import os
from PIL import Image

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

CONFIRMED_WINDOWS_PATH = r"D:\Program Files\Tesseract-OCR\tesseract.exe"

def find_tesseract_cmd() -> str:
    # 1. Check environment variable if set
    env_path = os.environ.get("TESSERACT_CMD")
    if env_path and os.path.exists(env_path):
        return env_path
    
    # 2. Check confirmed Windows paths
    windows_paths = [
        CONFIRMED_WINDOWS_PATH,
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for path in windows_paths:
        if os.path.exists(path):
            return path
            
    # 3. Fallback to default PATH
    return "tesseract"

def verify_tesseract() -> tuple[bool, str, str]:
    """
    Single shared helper to configure pytesseract and check if it responds.
    Returns: (is_available, resolved_path, message_or_version)
    """
    if not PYTESSERACT_AVAILABLE:
        return False, "", "pytesseract Python package is not installed."
    
    tess_path = find_tesseract_cmd()
    pytesseract.pytesseract.tesseract_cmd = tess_path
    
    try:
        version = pytesseract.get_tesseract_version()
        return True, tess_path, str(version)
    except Exception as e:
        return False, tess_path, str(e)

def is_tesseract_available() -> bool:
    available, _, _ = verify_tesseract()
    return available

def extract_text(image_path: str) -> str:
    available, tess_path, _ = verify_tesseract()
    if not available:
        return f"[OCR skipped: Tesseract engine not found or configured at {tess_path}.]"
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        return f"[OCR error: {str(e)}]"