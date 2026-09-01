# 포맷브릿지 1.0

포맷브릿지는 파일을 외부 서버에 올리지 않고 Windows PC 안에서 변환·PDF 병합·압축·압축 해제를 수행하는 데스크톱 프로그램입니다.

## 주요 기능

- JPG, PNG, JP2, WebP, AVIF, GIF, TIFF, BMP, ICO 등 이미지 상호 변환
- 이미지 및 문서를 PDF로 변환하고 서로 다른 파일을 목록 순서대로 PDF 병합
- PDF를 PNG/JPG/WebP/TIFF로 페이지별 렌더링하거나 텍스트/DOCX로 변환
- DOC/DOCX/RTF/ODT, XLS/XLSX/ODS/CSV, PPT/PPTX/ODP 변환
- 한컴오피스 자동화를 이용한 HWP/HWPX → PDF/DOCX/TXT/HTML 변환
- ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2, TAR.XZ 압축 및 안전한 압축 해제
- Ghostscript를 이용한 PDF 화면/전자책/인쇄/원본 우선 최적화
- 완료 파일의 이미지 디코딩, PDF 페이지, OOXML ZIP 구조, 압축 무결성 자동 검증

## 사용법

1. `FormatBridge.exe`를 실행합니다.
2. 작업 방식을 고른 뒤 파일 또는 폴더를 추가합니다.
3. 저장 폴더와 대상 형식을 선택합니다.
4. `변환 시작`을 누릅니다.

원본 파일은 수정하거나 삭제하지 않으며, 같은 이름의 결과가 있으면 `_2`, `_3`처럼 새 이름을 만듭니다.

## 엔진 안내

기본 실행본에는 이미지, PDF, SVG, DOCX 생성, 7z 처리용 엔진이 포함됩니다. Office 문서는 설치된 Microsoft Office를 사용하며, HWP/HWPX는 `HWPFrame.HwpObject → Hwp.exe -Automation`으로 등록된 실제 한글 2022 엔진을 사용합니다. 한워드(`Hword.exe`)는 HWP 변환 엔진으로 사용하지 않습니다. Ghostscript가 있으면 PDF 압축을 사용할 수 있습니다. FFmpeg, LibreOffice, Pandoc을 추가 설치하면 미디어·문서 지원 범위가 자동으로 확장됩니다.

PDF→DOCX는 멈출 수 있는 Word 변환 대화상자를 사용하지 않습니다. 텍스트가 있는 PDF는 편집 가능한 문단으로 추출하고, 텍스트가 없는 스캔 페이지는 페이지 이미지로 넣습니다.

한컴오피스는 보안 정책상 최초 자동화 시 파일 접근 확인 창을 표시할 수 있습니다.

프로그램은 폴더를 자동 검색하지 않습니다. 사용자가 작업 목록에 직접 추가한 파일만 읽으며 원본은 변경하지 않습니다.

## 개발 실행

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## 테스트

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
