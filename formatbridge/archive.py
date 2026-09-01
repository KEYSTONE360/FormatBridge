from __future__ import annotations

import bz2
import gzip
import lzma
import shutil
import tarfile
import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path

from .registry import full_suffix

ProgressCallback = Callable[[int, int, str], None]


def _iter_entries(paths: Iterable[Path]) -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    for source in paths:
        source = source.resolve()
        if source.is_dir():
            root_name = source.name
            for file in source.rglob("*"):
                if file.is_file():
                    items.append((file, str(Path(root_name) / file.relative_to(source))))
        elif source.is_file():
            items.append((source, source.name))
    return items


def create_archive(
    paths: list[Path],
    output: Path,
    *,
    level: int = 6,
    password: str | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    if not paths:
        raise ValueError("압축할 파일이나 폴더가 없습니다.")
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = _iter_entries(paths)
    if not entries:
        raise ValueError("압축할 수 있는 파일이 없습니다.")
    ext = full_suffix(output)

    if ext == ".zip":
        if password:
            raise ValueError("ZIP 암호화는 안전성 문제로 제공하지 않습니다. 암호가 필요하면 7z를 선택하세요.")
        compression = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(output, "w", compression=compression, compresslevel=max(0, min(9, level))) as archive:
            for index, (source, arcname) in enumerate(entries, 1):
                archive.write(source, arcname)
                if progress:
                    progress(index, len(entries), arcname)
    elif ext == ".7z":
        try:
            import py7zr
        except ImportError as exc:
            raise RuntimeError("7z 압축에는 py7zr 엔진이 필요합니다.") from exc
        filters = [{"id": py7zr.FILTER_LZMA2, "preset": max(0, min(9, level))}]
        with py7zr.SevenZipFile(output, "w", password=password or None, filters=filters) as archive:
            for index, (source, arcname) in enumerate(entries, 1):
                archive.write(source, arcname)
                if progress:
                    progress(index, len(entries), arcname)
    elif ext in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz"}:
        mode = {".tar": "w", ".tar.gz": "w:gz", ".tar.bz2": "w:bz2", ".tar.xz": "w:xz"}[ext]
        kwargs = {} if mode == "w" else {"compresslevel": max(0, min(9, level))}
        if mode == "w:xz":
            kwargs = {}
        with tarfile.open(output, mode, **kwargs) as archive:
            for index, (source, arcname) in enumerate(entries, 1):
                archive.add(source, arcname=arcname, recursive=False)
                if progress:
                    progress(index, len(entries), arcname)
    else:
        raise ValueError(f"지원하지 않는 압축 형식입니다: {ext}")
    return output


def _safe_destination(root: Path, member_name: str) -> Path:
    # Resolve and compare paths to prevent Zip Slip/Tar Slip traversal.
    destination = (root / member_name).resolve()
    root_resolved = root.resolve()
    try:
        destination.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"안전하지 않은 압축 항목을 차단했습니다: {member_name}") from exc
    return destination


def extract_archive(
    source: Path,
    output_dir: Path,
    *,
    password: str | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = full_suffix(source)

    if ext == ".zip":
        with zipfile.ZipFile(source) as archive:
            members = archive.infolist()
            for index, member in enumerate(members, 1):
                destination = _safe_destination(output_dir, member.filename)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with (
                        archive.open(member, pwd=password.encode() if password else None) as src,
                        destination.open("wb") as dst,
                    ):
                        shutil.copyfileobj(src, dst)
                if progress:
                    progress(index, len(members), member.filename)
    elif ext == ".7z":
        try:
            import py7zr
        except ImportError as exc:
            raise RuntimeError("7z 압축 해제에는 py7zr 엔진이 필요합니다.") from exc
        with py7zr.SevenZipFile(source, "r", password=password or None) as archive:
            names = archive.getnames()
            for name in names:
                _safe_destination(output_dir, name)
            archive.extractall(path=output_dir)
            if progress:
                progress(len(names), len(names), "7z 압축 해제 완료")
    elif ext in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz"}:
        with tarfile.open(source, "r:*") as archive:
            members = archive.getmembers()
            for member in members:
                _safe_destination(output_dir, member.name)
                if member.issym() or member.islnk():
                    raise ValueError(f"안전하지 않은 링크 항목을 차단했습니다: {member.name}")
            archive.extractall(output_dir, members=members, filter="data")
            if progress:
                progress(len(members), len(members), "TAR 압축 해제 완료")
    elif ext in {".gz", ".bz2", ".xz"}:
        opener = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}[ext]
        destination = output_dir / source.stem
        with opener(source, "rb") as src, destination.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        if progress:
            progress(1, 1, destination.name)
    else:
        raise ValueError(f"지원하지 않는 압축 형식입니다: {ext}")
    return output_dir


def validate_archive(path: Path, password: str | None = None) -> tuple[bool, str]:
    ext = full_suffix(path)
    try:
        if ext == ".zip":
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                return (bad is None, "정상" if bad is None else f"손상 항목: {bad}")
        if ext == ".7z":
            import py7zr

            with py7zr.SevenZipFile(path, "r", password=password or None) as archive:
                result = archive.test()
                # py7zr <=1.0 returned None on success; newer versions return True.
                passed = result is None or result is True
                return (passed, "정상" if passed else str(result))
        if ext.startswith(".tar") or ext in {".tgz", ".tbz2", ".txz"}:
            with tarfile.open(path, "r:*") as archive:
                archive.getmembers()
            return True, "정상"
    except Exception as exc:
        return False, str(exc)
    return path.exists() and path.stat().st_size > 0, "기본 검사"
