from __future__ import annotations

from pathlib import Path

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".ico",
    ".avif",
    ".jp2",
    ".j2k",
    ".ppm",
    ".pgm",
    ".pbm",
    ".pcx",
}
VECTOR_EXTENSIONS = {".svg", ".eps", ".ps"}
PDF_EXTENSIONS = {".pdf"}
WORD_EXTENSIONS = {
    ".doc",
    ".docx",
    ".docm",
    ".odt",
    ".rtf",
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".xml",
    ".mht",
    ".mhtml",
}
HWP_EXTENSIONS = {".hwp", ".hwpx"}
SHEET_EXTENSIONS = {".xls", ".xlsx", ".xlsm", ".xlsb", ".ods", ".csv", ".tsv"}
SLIDE_EXTENSIONS = {".ppt", ".pptx", ".pptm", ".odp"}
ARCHIVE_EXTENSIONS = {
    ".zip",
    ".7z",
    ".tar",
    ".tgz",
    ".tbz2",
    ".txz",
    ".gz",
    ".bz2",
    ".xz",
}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".m4v"}
EBOOK_EXTENSIONS = {".epub", ".mobi", ".azw3"}
TEXT_EXTENSIONS = {".txt", ".md", ".json", ".xml", ".csv", ".tsv", ".log"}

ALL_EXTENSIONS = set().union(
    IMAGE_EXTENSIONS,
    VECTOR_EXTENSIONS,
    PDF_EXTENSIONS,
    WORD_EXTENSIONS,
    HWP_EXTENSIONS,
    SHEET_EXTENSIONS,
    SLIDE_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    AUDIO_EXTENSIONS,
    VIDEO_EXTENSIONS,
    EBOOK_EXTENSIONS,
    TEXT_EXTENSIONS,
)

IMAGE_TARGETS = [".jpg", ".png", ".webp", ".avif", ".jp2", ".bmp", ".gif", ".tiff", ".ico", ".pdf"]
WORD_TARGETS = [".pdf", ".docx", ".rtf", ".txt", ".html"]
HWP_TARGETS = [".pdf", ".hwp", ".hwpx", ".docx", ".txt", ".html"]
SHEET_TARGETS = [".pdf", ".xlsx", ".xls", ".csv", ".ods"]
SLIDE_TARGETS = [".pdf", ".pptx", ".odp"]
PDF_TARGETS = [".pdf", ".png", ".jpg", ".webp", ".tiff", ".txt", ".docx"]
AUDIO_TARGETS = [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus"]
VIDEO_TARGETS = [".mp4", ".mkv", ".mov", ".avi", ".webm", ".mp3", ".wav"]
ARCHIVE_TARGETS = [".zip", ".7z", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz"]


def full_suffix(path: str | Path) -> str:
    """Return a compound suffix for archive types and a normal suffix otherwise."""
    name = Path(path).name.lower()
    for ext in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if name.endswith(ext):
            return ext
    return Path(name).suffix


def category(path: str | Path) -> str:
    ext = full_suffix(path)
    if ext in IMAGE_EXTENSIONS:
        return "이미지"
    if ext in VECTOR_EXTENSIONS:
        return "벡터"
    if ext in PDF_EXTENSIONS:
        return "PDF"
    if ext in HWP_EXTENSIONS:
        return "한글 문서"
    if ext in SHEET_EXTENSIONS:
        return "스프레드시트"
    if ext in SLIDE_EXTENSIONS:
        return "프레젠테이션"
    if ext in WORD_EXTENSIONS or ext in TEXT_EXTENSIONS:
        return "문서"
    if ext in ARCHIVE_EXTENSIONS or ext.startswith(".tar."):
        return "압축 파일"
    if ext in AUDIO_EXTENSIONS:
        return "오디오"
    if ext in VIDEO_EXTENSIONS:
        return "비디오"
    if ext in EBOOK_EXTENSIONS:
        return "전자책"
    return "기타"


def target_formats(paths: list[str | Path]) -> list[str]:
    if not paths:
        return IMAGE_TARGETS + WORD_TARGETS[1:]
    categories = {category(p) for p in paths if not Path(p).is_dir()}
    if not categories:
        return ARCHIVE_TARGETS
    if len(categories) > 1:
        # PDF is the common interchange format for images and documents.
        if categories <= {"이미지", "벡터", "PDF", "문서", "한글 문서", "스프레드시트", "프레젠테이션"}:
            return [".pdf"]
        return []
    kind = next(iter(categories))
    return {
        "이미지": IMAGE_TARGETS,
        "벡터": IMAGE_TARGETS,
        "PDF": PDF_TARGETS,
        "문서": WORD_TARGETS,
        "한글 문서": HWP_TARGETS,
        "스프레드시트": SHEET_TARGETS,
        "프레젠테이션": SLIDE_TARGETS,
        "오디오": AUDIO_TARGETS,
        "비디오": VIDEO_TARGETS,
        "압축 파일": ARCHIVE_TARGETS,
    }.get(kind, [".pdf", ".txt"])


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"
