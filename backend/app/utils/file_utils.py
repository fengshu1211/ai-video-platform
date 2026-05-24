"""文件处理工具"""
import uuid
from pathlib import Path


def generate_filename(original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def get_file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)
