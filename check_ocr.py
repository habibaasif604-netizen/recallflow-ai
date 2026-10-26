import sys
import os
from src.ocr import verify_tesseract

def main():
    print("=== Tesseract OCR Diagnostic ===")
    
    # Check 1: Package import check
    try:
        import pytesseract
        from PIL import Image
        print("[ok] Check 1: pytesseract and Pillow are importable")
    except ImportError as e:
        print(f"[fail] Check 1: Missing Python packages -> {e}")
        sys.exit(1)

    # Check 2: Shared verification & engine execution
    env_cmd = os.environ.get("TESSERACT_CMD", "(not set)")
    print(f"[info] TESSERACT_CMD env var: {env_cmd}")
    
    available, resolved_path, details = verify_tesseract()
    print(f"[info] pytesseract.tesseract_cmd = {resolved_path}")
    
    if available:
        print(f"[ok] Check 2: Tesseract engine responds — Tesseract {details}")
        print("========================================")
        print("OCR looks good. ✓")
    else:
        print(f"[fail] Check 2: Tesseract engine failed to respond.")
        print(f"       Path tried: {resolved_path}")
        print(f"       Error details: {details}")
        sys.exit(1)

if __name__ == "__main__":
    main()