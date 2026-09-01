from __future__ import annotations

import os
import queue
import threading
import traceback
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    BooleanVar,
    DoubleVar,
    IntVar,
    StringVar,
    Tk,
    X,
    Y,
    filedialog,
    messagebox,
    ttk,
)
from tkinter.scrolledtext import ScrolledText
from typing import ClassVar

from .archive import create_archive, extract_archive, validate_archive
from .converter import Converter, ConvertOptions, unique_output, verify_output
from .engines import EngineManager
from .registry import ARCHIVE_TARGETS, category, human_size, target_formats

APP_NAME = "포맷브릿지"
APP_SUBTITLE = "이미지 · PDF · 문서 · HWP · Office · 압축 파일을 한곳에서"


class FormatBridgeApp:
    COLORS: ClassVar[dict[str, str]] = {
        "navy": "#102A43",
        "blue": "#246BFD",
        "blue_hover": "#1557D5",
        "sky": "#EAF2FF",
        "surface": "#FFFFFF",
        "canvas": "#F5F7FB",
        "text": "#172B4D",
        "muted": "#64748B",
        "line": "#DCE3EC",
        "green": "#137A55",
        "green_bg": "#E8F7F0",
        "red": "#B42318",
        "orange": "#B54708",
    }

    OPERATIONS: ClassVar[tuple[str, ...]] = (
        "개별 파일 변환",
        "PDF로 순서대로 합치기",
        "새 압축 파일 만들기",
        "압축 파일 풀기",
    )

    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"{APP_NAME} 1.0")
        self.root.geometry("1120x760")
        self.root.minsize(930, 650)
        self.root.configure(bg=self.COLORS["canvas"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.paths: list[Path] = []
        self.item_by_path: dict[Path, str] = {}
        self.events: queue.Queue[tuple] = queue.Queue()
        self.busy = False
        self.last_output_dir: Path | None = None
        self.engines = EngineManager()
        self.converter = Converter(self.engines)

        self.operation_var = StringVar(value=self.OPERATIONS[0])
        self.target_var = StringVar(value=".pdf")
        self.output_var = StringVar(value=str(Path.home() / "Documents" / "FormatBridge_Output"))
        self.quality_var = IntVar(value=88)
        self.dpi_var = IntVar(value=160)
        self.pdf_quality_var = StringVar(value="전자책")
        self.password_var = StringVar(value="")
        self.verify_var = BooleanVar(value=True)
        self.progress_var = DoubleVar(value=0)
        self.status_var = StringVar(value="파일을 추가해 시작하세요")
        self.summary_var = StringVar(value="0개 항목")

        self._configure_style()
        self._build_ui()
        self._refresh_targets()
        self._refresh_engine_table()
        self.root.after(120, self._drain_events)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=self.COLORS["canvas"])
        style.configure("Surface.TFrame", background=self.COLORS["surface"])
        style.configure("Header.TFrame", background=self.COLORS["navy"])
        style.configure(
            "TLabel", background=self.COLORS["canvas"], foreground=self.COLORS["text"], font=("맑은 고딕", 10)
        )
        style.configure(
            "Surface.TLabel", background=self.COLORS["surface"], foreground=self.COLORS["text"], font=("맑은 고딕", 10)
        )
        style.configure(
            "Muted.Surface.TLabel",
            background=self.COLORS["surface"],
            foreground=self.COLORS["muted"],
            font=("맑은 고딕", 9),
        )
        style.configure(
            "HeaderTitle.TLabel", background=self.COLORS["navy"], foreground="white", font=("맑은 고딕", 22, "bold")
        )
        style.configure(
            "HeaderSub.TLabel", background=self.COLORS["navy"], foreground="#BDD4F4", font=("맑은 고딕", 10)
        )
        style.configure(
            "Section.TLabel",
            background=self.COLORS["surface"],
            foreground=self.COLORS["text"],
            font=("맑은 고딕", 11, "bold"),
        )
        style.configure(
            "Primary.TButton",
            background=self.COLORS["blue"],
            foreground="white",
            borderwidth=0,
            padding=(18, 10),
            font=("맑은 고딕", 10, "bold"),
        )
        style.map("Primary.TButton", background=[("active", self.COLORS["blue_hover"]), ("disabled", "#AFC4E8")])
        style.configure(
            "Secondary.TButton",
            background=self.COLORS["surface"],
            foreground=self.COLORS["text"],
            bordercolor=self.COLORS["line"],
            padding=(12, 8),
            font=("맑은 고딕", 9),
        )
        style.map("Secondary.TButton", background=[("active", self.COLORS["sky"])])
        style.configure("Danger.TButton", background="#FFF2F0", foreground=self.COLORS["red"], padding=(10, 8))
        style.configure(
            "Treeview",
            background="white",
            fieldbackground="white",
            foreground=self.COLORS["text"],
            rowheight=34,
            bordercolor=self.COLORS["line"],
            font=("맑은 고딕", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#F1F5F9",
            foreground=self.COLORS["muted"],
            relief="flat",
            padding=(8, 8),
            font=("맑은 고딕", 9, "bold"),
        )
        style.map("Treeview", background=[("selected", "#DCE9FF")], foreground=[("selected", self.COLORS["text"])])
        style.configure("TNotebook", background=self.COLORS["canvas"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#E8EDF4",
            foreground=self.COLORS["muted"],
            padding=(18, 9),
            font=("맑은 고딕", 9, "bold"),
        )
        style.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", self.COLORS["blue"])])
        style.configure("Horizontal.TProgressbar", troughcolor="#DEE6F2", background=self.COLORS["blue"], borderwidth=0)

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(28, 18))
        header.pack(fill=X)
        title_area = ttk.Frame(header, style="Header.TFrame")
        title_area.pack(side=LEFT)
        ttk.Label(title_area, text=APP_NAME, style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(title_area, text=APP_SUBTITLE, style="HeaderSub.TLabel").pack(anchor="w", pady=(2, 0))
        privacy = ttk.Label(header, text="● 100% 로컬 처리", style="HeaderSub.TLabel")
        privacy.pack(side=RIGHT, padx=(0, 4))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=22, pady=(16, 18))
        self.work_tab = ttk.Frame(notebook, style="Surface.TFrame", padding=18)
        self.engine_tab = ttk.Frame(notebook, style="Surface.TFrame", padding=18)
        self.help_tab = ttk.Frame(notebook, style="Surface.TFrame", padding=22)
        self.log_tab = ttk.Frame(notebook, style="Surface.TFrame", padding=18)
        notebook.add(self.work_tab, text="  변환 작업  ")
        notebook.add(self.engine_tab, text="  엔진 상태  ")
        notebook.add(self.help_tab, text="  지원 형식 / 도움말  ")
        notebook.add(self.log_tab, text="  작업 로그  ")
        self._build_work_tab()
        self._build_engine_tab()
        self._build_help_tab()
        self._build_log_tab()

    def _build_work_tab(self) -> None:
        top = ttk.Frame(self.work_tab, style="Surface.TFrame")
        top.pack(fill=X)
        ttk.Label(top, text="작업 방식", style="Section.TLabel").pack(side=LEFT, padx=(0, 12))
        operation = ttk.Combobox(
            top,
            textvariable=self.operation_var,
            values=self.OPERATIONS,
            width=27,
            state="readonly",
            font=("맑은 고딕", 9),
        )
        operation.pack(side=LEFT)
        operation.bind("<<ComboboxSelected>>", lambda _e: self._refresh_targets())
        ttk.Button(top, text="＋ 파일 추가", style="Secondary.TButton", command=self._add_files).pack(
            side=RIGHT, padx=(8, 0)
        )
        ttk.Button(top, text="＋ 폴더 추가", style="Secondary.TButton", command=self._add_folder).pack(side=RIGHT)

        list_header = ttk.Frame(self.work_tab, style="Surface.TFrame")
        list_header.pack(fill=X, pady=(16, 6))
        ttk.Label(list_header, text="작업 목록", style="Section.TLabel").pack(side=LEFT)
        ttk.Label(list_header, textvariable=self.summary_var, style="Muted.Surface.TLabel").pack(side=LEFT, padx=10)
        ttk.Button(list_header, text="전체 비우기", style="Danger.TButton", command=self._clear_files).pack(side=RIGHT)
        ttk.Button(list_header, text="선택 제거", style="Secondary.TButton", command=self._remove_selected).pack(
            side=RIGHT, padx=8
        )
        ttk.Button(
            list_header, text="↓", width=3, style="Secondary.TButton", command=lambda: self._move_selected(1)
        ).pack(side=RIGHT, padx=(4, 0))
        ttk.Button(
            list_header, text="↑", width=3, style="Secondary.TButton", command=lambda: self._move_selected(-1)
        ).pack(side=RIGHT)

        tree_frame = ttk.Frame(self.work_tab, style="Surface.TFrame")
        tree_frame.pack(fill=BOTH, expand=True)
        columns = ("order", "name", "kind", "size", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("order", text="#")
        self.tree.heading("name", text="파일 / 폴더")
        self.tree.heading("kind", text="종류")
        self.tree.heading("size", text="크기")
        self.tree.heading("status", text="상태")
        self.tree.column("order", width=48, anchor="center", stretch=False)
        self.tree.column("name", width=430, anchor="w")
        self.tree.column("kind", width=120, anchor="center", stretch=False)
        self.tree.column("size", width=95, anchor="e", stretch=False)
        self.tree.column("status", width=150, anchor="center", stretch=False)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.bind("<Delete>", lambda _e: self._remove_selected())

        options = ttk.Frame(self.work_tab, style="Surface.TFrame")
        options.pack(fill=X, pady=(16, 0))
        options.columnconfigure(1, weight=2)
        options.columnconfigure(3, weight=1)
        options.columnconfigure(5, weight=1)

        ttk.Label(options, text="저장 폴더", style="Surface.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=4
        )
        output_entry = ttk.Entry(options, textvariable=self.output_var)
        output_entry.grid(row=0, column=1, columnspan=4, sticky="ew", pady=4)
        ttk.Button(options, text="찾아보기", style="Secondary.TButton", command=self._choose_output).grid(
            row=0, column=5, sticky="e", padx=(8, 0)
        )

        ttk.Label(options, text="대상 형식", style="Surface.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 4)
        )
        self.target_combo = ttk.Combobox(options, textvariable=self.target_var, width=15, state="readonly")
        self.target_combo.grid(row=1, column=1, sticky="w", pady=(8, 4))
        ttk.Label(options, text="품질", style="Surface.TLabel").grid(
            row=1, column=2, sticky="e", padx=(16, 8), pady=(8, 4)
        )
        quality = ttk.Scale(options, from_=30, to=100, variable=self.quality_var, orient="horizontal")
        quality.grid(row=1, column=3, sticky="ew", pady=(8, 4))
        self.quality_label = ttk.Label(
            options, text=f"{self.quality_var.get()}%", style="Muted.Surface.TLabel", width=5
        )
        self.quality_label.grid(row=1, column=4, sticky="w", padx=(6, 0), pady=(8, 4))
        quality.configure(command=lambda value: self.quality_label.configure(text=f"{int(float(value))}%"))
        self.verify_check = ttk.Checkbutton(options, text="완료 후 파일 구조 검증", variable=self.verify_var)
        self.verify_check.grid(row=1, column=5, sticky="e", pady=(8, 4))

        ttk.Label(options, text="PDF 화질", style="Surface.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=4
        )
        self.pdf_quality_combo = ttk.Combobox(
            options,
            textvariable=self.pdf_quality_var,
            values=("화면", "전자책", "인쇄", "원본 우선"),
            state="readonly",
            width=13,
        )
        self.pdf_quality_combo.grid(row=2, column=1, sticky="w", pady=4)
        ttk.Label(options, text="PDF→이미지 DPI", style="Surface.TLabel").grid(
            row=2, column=2, sticky="e", padx=(16, 8), pady=4
        )
        self.dpi_combo = ttk.Combobox(
            options, textvariable=self.dpi_var, values=(96, 120, 160, 200, 300, 600), state="readonly", width=8
        )
        self.dpi_combo.grid(row=2, column=3, sticky="w", pady=4)
        ttk.Label(options, text="7z 암호 (선택)", style="Surface.TLabel").grid(
            row=2, column=4, sticky="e", padx=(16, 8), pady=4
        )
        self.password_entry = ttk.Entry(options, textvariable=self.password_var, show="●", width=16)
        self.password_entry.grid(row=2, column=5, sticky="e", pady=4)

        footer = ttk.Frame(self.work_tab, style="Surface.TFrame")
        footer.pack(fill=X, pady=(16, 0))
        left = ttk.Frame(footer, style="Surface.TFrame")
        left.pack(side=LEFT, fill=X, expand=True, padx=(0, 16))
        ttk.Label(left, textvariable=self.status_var, style="Muted.Surface.TLabel").pack(anchor="w")
        self.progress = ttk.Progressbar(left, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=X, pady=(7, 0))
        self.open_button = ttk.Button(
            footer, text="결과 폴더 열기", style="Secondary.TButton", command=self._open_output, state="disabled"
        )
        self.open_button.pack(side=RIGHT, padx=(8, 0))
        self.start_button = ttk.Button(footer, text="변환 시작", style="Primary.TButton", command=self._start)
        self.start_button.pack(side=RIGHT)

    def _build_engine_tab(self) -> None:
        title = ttk.Frame(self.engine_tab, style="Surface.TFrame")
        title.pack(fill=X, pady=(0, 12))
        ttk.Label(title, text="설치된 변환 엔진", style="Section.TLabel").pack(side=LEFT)
        ttk.Label(title, text="사용 가능한 엔진은 자동으로 우선 선택됩니다.", style="Muted.Surface.TLabel").pack(
            side=LEFT, padx=12
        )
        ttk.Button(title, text="다시 검사", style="Secondary.TButton", command=self._refresh_engine_table).pack(
            side=RIGHT
        )
        self.engine_tree = ttk.Treeview(
            self.engine_tab, columns=("status", "name", "purpose", "detail"), show="headings"
        )
        for col, label, width in (
            ("status", "상태", 80),
            ("name", "엔진", 170),
            ("purpose", "담당 형식", 260),
            ("detail", "세부 정보", 430),
        ):
            self.engine_tree.heading(col, text=label)
            self.engine_tree.column(
                col, width=width, anchor="w" if col != "status" else "center", stretch=col == "detail"
            )
        self.engine_tree.pack(fill=BOTH, expand=True)
        note = (
            "선택 엔진(FFmpeg, LibreOffice, Pandoc 등)을 설치하면 프로그램을 수정하지 않아도 지원 형식이 늘어납니다. "
            "이 PC에서는 Microsoft Office와 한컴오피스를 통해 DOCX/XLSX/PPTX/HWP 변환을 처리합니다."
        )
        ttk.Label(self.engine_tab, text=note, style="Muted.Surface.TLabel", wraplength=980).pack(fill=X, pady=(12, 0))

    def _build_help_tab(self) -> None:
        sections = [
            (
                "이미지",
                "JPG/JPEG, PNG, JP2/J2K, WebP, AVIF, GIF, TIFF, BMP, ICO, PPM/PGM/PBM · 투명 이미지를 JPG로 바꿀 때 흰 배경 적용",
            ),
            ("문서", "PDF, DOC/DOCX, RTF, ODT, TXT, Markdown, HTML, XML · PDF 병합과 페이지별 이미지 변환"),
            (
                "한컴/Office",
                "HWP/HWPX, XLS/XLSX/XLSM/ODS/CSV, PPT/PPTX/ODP · 설치된 한컴오피스와 Microsoft Office 사용",
            ),
            ("압축", "ZIP, 7Z, TAR, TAR.GZ, TAR.BZ2, TAR.XZ, GZ, BZ2, XZ · 7z AES 암호 지원 · 경로 탈출 공격 차단"),
            (
                "미디어/확장",
                "FFmpeg가 있으면 MP3/WAV/FLAC/OGG/M4A/AAC/MP4/MKV/MOV/AVI/WebM 변환 · Pandoc 설치 시 전자책/문서 확장",
            ),
        ]
        ttk.Label(self.help_tab, text="지원 범위", style="Section.TLabel").pack(anchor="w", pady=(0, 12))
        for title, body in sections:
            row = ttk.Frame(self.help_tab, style="Surface.TFrame")
            row.pack(fill=X, pady=7)
            ttk.Label(row, text=title, style="Section.TLabel", width=14).pack(side=LEFT, anchor="n")
            ttk.Label(row, text=body, style="Muted.Surface.TLabel", wraplength=790, justify="left").pack(
                side=LEFT, fill=X, expand=True
            )
        ttk.Separator(self.help_tab).pack(fill=X, pady=18)
        ttk.Label(self.help_tab, text="안전한 사용법", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        safety = (
            "• 원본 파일은 수정하거나 삭제하지 않습니다. 결과는 지정한 폴더에 새 이름으로 저장됩니다.\n"
            "• 서로 다른 이미지·PDF·문서·HWP를 한 번에 선택하면 PDF로 합칠 수 있습니다. 목록 순서대로 페이지가 배치됩니다.\n"
            "• ZIP 암호화는 오래된 방식의 보안 문제가 있어 제공하지 않습니다. 암호 압축은 7z를 사용하세요.\n"
            "• HWP 최초 자동 변환 시 한컴오피스가 파일 접근 확인 창을 표시할 수 있습니다. 이는 한컴 보안 정책입니다."
        )
        ttk.Label(self.help_tab, text=safety, style="Surface.TLabel", justify="left", wraplength=900).pack(anchor="w")

    def _build_log_tab(self) -> None:
        row = ttk.Frame(self.log_tab, style="Surface.TFrame")
        row.pack(fill=X, pady=(0, 10))
        ttk.Label(row, text="상세 작업 로그", style="Section.TLabel").pack(side=LEFT)
        ttk.Label(row, text="오류가 발생하면 이 내용을 확인하세요.", style="Muted.Surface.TLabel").pack(
            side=LEFT, padx=12
        )
        ttk.Button(
            row, text="로그 지우기", style="Secondary.TButton", command=lambda: self.log_text.delete("1.0", END)
        ).pack(side=RIGHT)
        self.log_text = ScrolledText(
            self.log_tab,
            wrap="word",
            bg="#0F172A",
            fg="#D7E3F4",
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10),
            padx=14,
            pady=12,
        )
        self.log_text.pack(fill=BOTH, expand=True)

    def _add_files(self) -> None:
        filenames = filedialog.askopenfilenames(
            title="변환할 파일 선택", filetypes=(("모든 지원 파일", "*.*"), ("모든 파일", "*.*"))
        )
        self._append_paths([Path(name) for name in filenames])

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="추가할 폴더 선택")
        if folder:
            self._append_paths([Path(folder)])

    def _append_paths(self, paths: list[Path]) -> None:
        for path in paths:
            resolved = path.resolve()
            if resolved in self.item_by_path:
                continue
            self.paths.append(resolved)
            size = resolved.stat().st_size if resolved.is_file() else 0
            kind = "폴더" if resolved.is_dir() else category(resolved)
            iid = self.tree.insert(
                "", END, values=(len(self.paths), resolved.name, kind, human_size(size) if size else "—", "대기")
            )
            self.item_by_path[resolved] = iid
        self._renumber()
        self._refresh_targets()

    def _remove_selected(self) -> None:
        selected = set(self.tree.selection())
        if not selected:
            return
        removed = {path for path, iid in self.item_by_path.items() if iid in selected}
        for iid in selected:
            self.tree.delete(iid)
        self.paths = [path for path in self.paths if path not in removed]
        for path in removed:
            self.item_by_path.pop(path, None)
        self._renumber()
        self._refresh_targets()

    def _move_selected(self, delta: int) -> None:
        if self.busy:
            return
        selected = set(self.tree.selection())
        if not selected:
            return
        children = list(self.tree.get_children())
        indexes = [index for index, iid in enumerate(children) if iid in selected]
        sequence = indexes if delta < 0 else list(reversed(indexes))
        for index in sequence:
            new_index = index + delta
            if new_index < 0 or new_index >= len(children):
                continue
            if children[new_index] in selected:
                continue
            children[index], children[new_index] = children[new_index], children[index]
        inverse = {iid: path for path, iid in self.item_by_path.items()}
        self.paths = [inverse[iid] for iid in children]
        for index, iid in enumerate(children):
            self.tree.move(iid, "", index)
        self._renumber()

    def _clear_files(self) -> None:
        if self.busy:
            return
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.paths.clear()
        self.item_by_path.clear()
        self._renumber()
        self._refresh_targets()

    def _renumber(self) -> None:
        total_size = 0
        for index, path in enumerate(self.paths, 1):
            iid = self.item_by_path[path]
            values = list(self.tree.item(iid, "values"))
            values[0] = index
            self.tree.item(iid, values=values)
            if path.is_file():
                total_size += path.stat().st_size
        self.summary_var.set(f"{len(self.paths)}개 항목 · {human_size(total_size)}")

    def _refresh_targets(self) -> None:
        operation = self.operation_var.get()
        if operation == self.OPERATIONS[0]:
            values = target_formats(self.paths) or ["선택 파일 조합 미지원"]
            button_text = "변환 시작"
        elif operation == self.OPERATIONS[1]:
            values = [".pdf"]
            button_text = "PDF 합치기"
        elif operation == self.OPERATIONS[2]:
            values = ARCHIVE_TARGETS
            button_text = "압축 시작"
        else:
            values = ["자동 감지"]
            button_text = "압축 풀기"
        self.target_combo.configure(values=values)
        if self.target_var.get() not in values:
            self.target_var.set(values[0])
        self.start_button.configure(text=button_text)
        password_state = "normal" if operation in (self.OPERATIONS[2], self.OPERATIONS[3]) else "disabled"
        self.password_entry.configure(state=password_state)

    def _choose_output(self) -> None:
        folder = filedialog.askdirectory(title="결과 저장 폴더 선택", initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)

    def _refresh_engine_table(self) -> None:
        self.engines = EngineManager()
        self.converter.engines = self.engines
        for iid in self.engine_tree.get_children():
            self.engine_tree.delete(iid)
        for report in self.engines.reports():
            self.engine_tree.insert(
                "",
                END,
                values=("사용 가능" if report.available else "선택 설치", report.name, report.purpose, report.detail),
            )

    def _set_item_status(self, path: Path, status: str) -> None:
        iid = self.item_by_path.get(path)
        if iid and self.tree.exists(iid):
            values = list(self.tree.item(iid, "values"))
            values[4] = status
            self.tree.item(iid, values=values)

    def _start(self) -> None:
        if self.busy:
            return
        if not self.paths:
            messagebox.showinfo(APP_NAME, "먼저 파일이나 폴더를 추가하세요.")
            return
        output_dir = Path(self.output_var.get()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"저장 폴더를 만들 수 없습니다.\n{exc}")
            return
        if self.target_var.get().startswith("선택 파일"):
            messagebox.showerror(
                APP_NAME, "현재 작업에서는 선택한 파일 종류를 하나의 대상 형식으로 변환할 수 없습니다."
            )
            return
        self.busy = True
        self.last_output_dir = output_dir
        self.start_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.progress_var.set(0)
        for path in self.paths:
            self._set_item_status(path, "대기")
        snapshot = list(self.paths)
        config = {
            "operation": self.operation_var.get(),
            "target": self.target_var.get(),
            "quality": self.quality_var.get(),
            "dpi": self.dpi_var.get(),
            "pdf_quality": self.pdf_quality_var.get(),
            "password": self.password_var.get() or None,
            "verify": self.verify_var.get(),
        }
        self._write_log(f"시작 · {config['operation']} · {len(snapshot)}개 항목 · 대상 {config['target']}")
        threading.Thread(target=self._worker, args=(snapshot, output_dir, config), daemon=True).start()

    def _worker(self, paths: list[Path], output_dir: Path, config: dict) -> None:
        operation = config["operation"]
        target = config["target"]
        options = ConvertOptions(
            quality=config["quality"],
            dpi=config["dpi"],
            pdf_quality=config["pdf_quality"],
            overwrite=False,
        )
        password = config["password"]
        succeeded = 0
        failed = 0
        outputs: list[Path] = []
        try:
            if operation == self.OPERATIONS[0]:
                files = [p for p in paths if p.is_file()]
                for index, path in enumerate(files, 1):
                    self.events.put(("item", path, "변환 중"))
                    self.events.put(("status", f"{path.name} 변환 중 ({index}/{len(files)})"))
                    try:
                        made = self.converter.convert(path, target, output_dir, options)
                        if config["verify"]:
                            for result in made:
                                ok, detail = verify_output(result, target)
                                if not ok:
                                    raise RuntimeError(f"결과 검증 실패: {detail}")
                        outputs.extend(made)
                        succeeded += 1
                        self.events.put(("item", path, "완료 · 검증됨" if config["verify"] else "완료"))
                        self.events.put(("log", f"성공 · {path.name} → {', '.join(p.name for p in made)}"))
                    except Exception as exc:
                        failed += 1
                        self.events.put(("item", path, "실패"))
                        self.events.put(("log", f"{path.name}: {exc}"))
                    self.events.put(("progress", index / max(1, len(files)) * 100))
            elif operation == self.OPERATIONS[1]:
                for path in paths:
                    self.events.put(("item", path, "PDF 준비 중"))
                output = unique_output(output_dir, "합친문서", ".pdf")
                self.converter.merge_to_pdf(paths, output, options, lambda msg: self.events.put(("status", msg)))
                ok, detail = verify_output(output, ".pdf")
                if not ok:
                    raise RuntimeError(f"병합 PDF 검증 실패: {detail}")
                outputs.append(output)
                succeeded = len(paths)
                for path in paths:
                    self.events.put(("item", path, "병합 완료"))
                self.events.put(("progress", 100))
            elif operation == self.OPERATIONS[2]:
                name = "압축파일"
                output = unique_output(output_dir, name, target)
                for path in paths:
                    self.events.put(("item", path, "압축 중"))
                create_archive(
                    paths,
                    output,
                    level=round(self.quality_var.get() / 11),
                    password=password,
                    progress=lambda done, total, name: self.events.put(("progress", done / max(1, total) * 100)),
                )
                ok, detail = validate_archive(output, password)
                if not ok:
                    raise RuntimeError(f"압축 무결성 검사 실패: {detail}")
                outputs.append(output)
                succeeded = len(paths)
                for path in paths:
                    self.events.put(("item", path, "압축 완료"))
            else:
                archives = [p for p in paths if p.is_file()]
                for index, path in enumerate(archives, 1):
                    self.events.put(("item", path, "압축 해제 중"))
                    try:
                        destination = output_dir / f"{path.stem}_압축해제"
                        suffix = 2
                        while destination.exists():
                            destination = output_dir / f"{path.stem}_압축해제_{suffix}"
                            suffix += 1
                        extract_archive(path, destination, password=password)
                        if not any(destination.rglob("*")):
                            raise RuntimeError("압축 해제 결과가 비어 있습니다.")
                        outputs.append(destination)
                        succeeded += 1
                        self.events.put(("item", path, "해제 완료"))
                    except Exception as exc:
                        failed += 1
                        self.events.put(("item", path, "실패"))
                        self.events.put(("log", f"{path.name}: {exc}"))
                    self.events.put(("progress", index / max(1, len(archives)) * 100))
        except Exception as exc:
            failed += 1
            self.events.put(("log", f"작업 중단: {exc}\n{traceback.format_exc(limit=2)}"))
        finally:
            self.events.put(("done", succeeded, failed, outputs))

    def _drain_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "item":
                    self._set_item_status(event[1], event[2])
                elif kind == "status":
                    self.status_var.set(event[1])
                elif kind == "progress":
                    self.progress_var.set(event[1])
                elif kind == "log":
                    self.status_var.set(event[1].splitlines()[0])
                    self._write_log(event[1])
                elif kind == "done":
                    self._finish(event[1], event[2], event[3])
        except queue.Empty:
            pass
        self.root.after(120, self._drain_events)

    def _finish(self, succeeded: int, failed: int, outputs: list[Path]) -> None:
        self.busy = False
        self.start_button.configure(state="normal")
        self.open_button.configure(
            state="normal" if self.last_output_dir and self.last_output_dir.exists() else "disabled"
        )
        if failed:
            self._write_log(f"종료 · 성공 {succeeded} · 실패 {failed}")
            self.status_var.set(f"완료: 성공 {succeeded} · 실패 {failed} — 목록의 실패 항목을 확인하세요")
            messagebox.showwarning(
                APP_NAME,
                f"작업이 끝났습니다.\n성공: {succeeded}\n실패: {failed}\n\n상세 오류는 하단 상태와 실패 항목을 확인하세요.",
            )
        else:
            self._write_log(f"종료 · 성공 {succeeded} · 결과 {len(outputs)}개 · 검증 통과")
            self.progress_var.set(100)
            self.status_var.set(f"완료: {succeeded}개 처리 · 결과 {len(outputs)}개 생성 · 구조 검증 통과")
            messagebox.showinfo(
                APP_NAME,
                f"작업이 완료되었습니다.\n\n처리: {succeeded}개\n결과: {len(outputs)}개\n저장: {self.last_output_dir}",
            )

    def _open_output(self) -> None:
        if self.last_output_dir and self.last_output_dir.exists():
            os.startfile(self.last_output_dir)

    def _write_log(self, message: str) -> None:
        self.log_text.insert(END, message.rstrip() + "\n")
        self.log_text.see(END)

    def _on_close(self) -> None:
        if self.busy and not messagebox.askyesno(APP_NAME, "작업이 진행 중입니다. 정말 종료할까요?"):
            return
        self.root.destroy()


def run() -> None:
    root = Tk()
    FormatBridgeApp(root)
    root.mainloop()
