"""
Backward-compatibility adapter for Assisting_Scripts/load_file.py
Delegates to app.services.file_service.
"""
from pathlib import Path
from app.services.file_service import file_service

def load_file_ext(filepath: str) -> str:
    """Extract plain text from any supported file format."""
    return file_service.extract_text(Path(filepath))
