from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EngineInfo:
    key: str
    name: str
    available: bool
    detail: str
    purpose: str


def _first_existing(*candidates: str | None) -> str | None:
    for item in candidates:
        if item and Path(item).exists():
            return str(Path(item))
    return None


class EngineManager:
    def __init__(self, resource_dir: Path | None = None):
        self.resource_dir = resource_dir or Path(__file__).resolve().parent
        self.magick = shutil.which("magick")
        self.soffice = _first_existing(
            shutil.which("soffice"),
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        )
        self.seven_zip = _first_existing(
            shutil.which("7z"),
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        )
        self.ffmpeg = shutil.which("ffmpeg")
        self.pandoc = shutil.which("pandoc")
        self.ghostscript = _first_existing(
            shutil.which("gswin64c"),
            shutil.which("gs"),
            r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe",
        )
        self.ps32 = _first_existing(
            r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
            shutil.which("powershell"),
            shutil.which("pwsh"),
        )
        self.office_bridge = self.resource_dir / "office_bridge.ps1"
        self.hancom_exe = _first_existing(
            r"C:\Program Files (x86)\HNC\Office 2022\HOffice120\Bin\Hwp.exe",
            r"C:\Program Files\HNC\Office 2022\HOffice120\Bin\Hwp.exe",
        )
        self.ms_office = self._detect_ms_office()

    @staticmethod
    def has_module(name: str) -> bool:
        try:
            __import__(name)
            return True
        except Exception:
            return False

    def _detect_ms_office(self) -> bool:
        candidates = (
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE",
        )
        return any(Path(p).exists() for p in candidates)

    def reports(self) -> list[EngineInfo]:
        pillow_detail = "내장" if self.has_module("PIL") else "설치 필요"
        return [
            EngineInfo(
                "pillow", "이미지 엔진", self.has_module("PIL"), pillow_detail, "JPG, PNG, JP2, WebP, AVIF, TIFF 등"
            ),
            EngineInfo(
                "pymupdf",
                "PDF 렌더러",
                self.has_module("pymupdf") or self.has_module("fitz"),
                "내장" if (self.has_module("pymupdf") or self.has_module("fitz")) else "설치 필요",
                "PDF → 이미지/텍스트",
            ),
            EngineInfo(
                "pypdf",
                "PDF 병합 엔진",
                self.has_module("pypdf"),
                "내장" if self.has_module("pypdf") else "설치 필요",
                "PDF 병합 및 검증",
            ),
            EngineInfo(
                "ghostscript", "Ghostscript", bool(self.ghostscript), self.ghostscript or "미설치", "PDF 압축·최적화"
            ),
            EngineInfo(
                "office",
                "Microsoft Office",
                self.ms_office,
                "COM 자동화 가능" if self.ms_office else "미설치",
                "DOCX/XLSX/PPTX 변환",
            ),
            EngineInfo(
                "hancom",
                "한글 2022 (HWP)",
                bool(self.hancom_exe),
                (f"Hwp.exe Automation · {self.hancom_exe}" if self.hancom_exe else "미설치"),
                "HWP/HWPX 변환",
            ),
            EngineInfo(
                "libreoffice", "LibreOffice", bool(self.soffice), self.soffice or "선택 엔진", "ODF/Office 변환"
            ),
            EngineInfo(
                "py7zr",
                "7z 엔진",
                self.has_module("py7zr") or bool(self.seven_zip),
                "내장" if self.has_module("py7zr") else (self.seven_zip or "설치 필요"),
                "7z 압축·해제",
            ),
            EngineInfo(
                "svg",
                "SVG 엔진",
                self.has_module("pymupdf"),
                "MuPDF 내장" if self.has_module("pymupdf") else "설치 필요",
                "SVG → PNG/PDF/이미지",
            ),
            EngineInfo("ffmpeg", "FFmpeg", bool(self.ffmpeg), self.ffmpeg or "선택 엔진", "오디오·비디오 변환"),
            EngineInfo("pandoc", "Pandoc", bool(self.pandoc), self.pandoc or "선택 엔진", "전자책·마크다운 변환"),
        ]

    def office_convert(self, engine: str, source: Path, output: Path, timeout: int = 180) -> None:
        if not self.ps32 or not self.office_bridge.exists():
            raise RuntimeError("Office 자동화 브리지를 찾을 수 없습니다.")
        cmd = [
            self.ps32,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.office_bridge),
            "-Engine",
            engine,
            "-InputPath",
            str(source.resolve()),
            "-OutputPath",
            str(output.resolve()),
            "-TargetExt",
            output.suffix.lower(),
        ]
        startup = None
        creationflags = 0
        if os.name == "nt":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            startupinfo=startup,
            creationflags=creationflags,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0 or not output.exists():
            detail = (completed.stderr or completed.stdout or "출력 파일이 생성되지 않았습니다.").strip()
            raise RuntimeError(f"{engine} 변환 실패: {detail}")

    def ffmpeg_convert(self, source: Path, output: Path, quality: int = 85) -> None:
        if not self.ffmpeg:
            raise RuntimeError("FFmpeg가 설치되지 않아 미디어 변환을 사용할 수 없습니다.")
        crf = str(max(18, min(34, round(36 - quality * 0.18))))
        cmd = [self.ffmpeg, "-y", "-i", str(source), "-crf", crf, str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, check=False)
        if result.returncode != 0 or not output.exists():
            raise RuntimeError((result.stderr or "FFmpeg 변환 실패")[-1200:])

    def optimize_pdf(self, source: Path, output: Path, quality: str = "ebook") -> None:
        if not self.ghostscript:
            raise RuntimeError("PDF 최적화에는 Ghostscript가 필요합니다.")
        preset = {"화면": "screen", "전자책": "ebook", "인쇄": "printer", "원본 우선": "prepress"}.get(quality, quality)
        cmd = [
            self.ghostscript,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.6",
            f"-dPDFSETTINGS=/{preset}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output}",
            str(source),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
        if result.returncode != 0 or not output.exists():
            raise RuntimeError((result.stderr or "Ghostscript PDF 최적화 실패").strip())


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    nested = root / "formatbridge" / name
    return nested if nested.exists() else root / name
