# 포맷브릿지 1.0 검증 보고서

- 검증일: 2026-08-10
- 환경: Windows 11, Python 3.14.2, Microsoft Office, 한글 2022(Hwp.exe), Ghostscript 10.07
- 개인정보 원칙: 개인 HWP 파일은 검색·열기·복사·변환하지 않았습니다. 모든 HWP 검증은 테스트가 임시 폴더에 새로 생성한 인공 샘플로만 수행했으며 테스트 종료 시 삭제했습니다.

## 통과한 검사

1. Python 전체 문법 검사
2. Ruff 정적 검사 및 코드 포맷 검사
3. GUI 비표시 스모크 테스트: 11개 엔진 상태와 전체 위젯 생성
4. JPG, WebP, JP2, AVIF, TIFF 이미지 왕복 변환 및 재디코딩
5. 투명 PNG→PDF→PNG 재렌더링
6. SVG→PNG/PDF MuPDF 렌더링
7. 이미지 2개 PDF 병합 및 페이지 수/순서 검사
8. 한글 텍스트→PDF 변환 및 PDF 페이지 구조 검사
9. Ghostscript PDF 최적화 후 재검사
10. ZIP, TAR.GZ, 암호화 7z 생성→무결성 검사→압축 해제→바이트 단위 원본 비교
11. 악성 `../` ZIP 항목의 경로 탈출 차단
12. DOCX/XLSX/PPTX→PDF 실제 Office 변환
13. PDF→DOCX 무인 변환 및 OOXML 내부 구조 검사
14. 한글 2022로 네이티브 HWP 생성 후 OLE 시그니처 검사
15. HWP→PDF/HWPX/DOCX/Unicode TXT 변환 및 각 형식 구조 검사
16. 생성한 HWPX를 다시 PDF로 변환
17. PyInstaller 단일 EXE 빌드 시 핵심 모듈 누락 경고 없음
18. 빌드된 EXE 직접 실행: `포맷브릿지 1.0` 창 응답 확인 후 정상 종료
19. 바탕화면 바로가기 실행: 2단계 one-file 프로세스 생성, `포맷브릿지 1.0` 창 응답 확인, 잔여 프로세스 없음

## 최종 자동 테스트 결과

`Ran 12 tests in 92.547s — OK`

- 최종 EXE 크기: 49,750,394 bytes
- SHA-256: `2DFA271382D8AD09C12004469BD0F104FE0DF973E3E84E12CD6F6AE927CE6DA2`

원본 파일은 삭제하거나 덮어쓰지 않으며, 같은 이름이 있으면 `_2`, `_3`과 같이 새 파일명을 사용합니다.
