from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader

from formatbridge.archive import create_archive, extract_archive, validate_archive
from formatbridge.converter import Converter, ConvertOptions, verify_output
from formatbridge.registry import category, full_suffix, target_formats


class RegistryTests(unittest.TestCase):
    def test_compound_suffix_and_categories(self):
        self.assertEqual(full_suffix("backup.tar.gz"), ".tar.gz")
        self.assertEqual(category("photo.jp2"), "이미지")
        self.assertEqual(category("report.hwp"), "한글 문서")
        self.assertEqual(category("slides.pptx"), "프레젠테이션")

    def test_mixed_documents_have_pdf_bridge(self):
        targets = target_formats(["a.png", "b.docx", "c.hwp", "d.pdf"])
        self.assertEqual(targets, [".pdf"])


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="formatbridge_test_")
        self.root = Path(self.temp.name)
        self.converter = Converter()
        self.options = ConvertOptions(quality=82, dpi=120)
        self.source = self.root / "투명 샘플.png"
        image = Image.new("RGBA", (320, 180), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 300, 160), fill=(36, 107, 253, 220))
        draw.ellipse((105, 35, 215, 145), fill=(255, 255, 255, 230))
        image.save(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def test_image_cross_format_roundtrip(self):
        for ext in (".jpg", ".webp", ".jp2", ".avif", ".tiff"):
            with self.subTest(ext=ext):
                output = self.converter.convert(self.source, ext, self.root / "out", self.options)[0]
                ok, detail = verify_output(output, ext)
                self.assertTrue(ok, detail)
                with Image.open(output) as decoded:
                    self.assertEqual(decoded.size, (320, 180))

    def test_image_to_pdf_and_back(self):
        pdf = self.converter.convert(self.source, ".pdf", self.root / "out", self.options)[0]
        ok, detail = verify_output(pdf, ".pdf")
        self.assertTrue(ok, detail)
        images = self.converter.convert(pdf, ".png", self.root / "rendered", self.options)
        self.assertEqual(len(images), 1)
        ok, detail = verify_output(images[0], ".png")
        self.assertTrue(ok, detail)

    def test_text_to_pdf_korean_and_structure(self):
        text = self.root / "문서.txt"
        text.write_text("포맷브릿지 교차 검증\n한글 문서와 PDF 변환 테스트입니다.\n" * 20, encoding="utf-8")
        pdf = self.converter.convert(text, ".pdf", self.root / "out", self.options)[0]
        reader = PdfReader(str(pdf))
        self.assertGreaterEqual(len(reader.pages), 1)
        self.assertGreater(pdf.stat().st_size, 1000)

    def test_merge_two_images_preserves_order_and_pages(self):
        second = self.root / "두번째.png"
        Image.new("RGB", (200, 300), "#EF4444").save(second)
        output = self.root / "merged.pdf"
        self.converter.merge_to_pdf([self.source, second], output, self.options)
        reader = PdfReader(str(output))
        self.assertEqual(len(reader.pages), 2)

    def test_svg_to_png_and_pdf(self):
        svg = self.root / "벡터.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="240" height="120">'
            '<rect width="240" height="120" rx="20" fill="#246bfd"/>'
            '<circle cx="120" cy="60" r="34" fill="white"/></svg>',
            encoding="utf-8",
        )
        for ext in (".png", ".pdf"):
            with self.subTest(ext=ext):
                output = self.converter.convert(svg, ext, self.root / "vector_out", self.options)[0]
                ok, detail = verify_output(output, ext)
                self.assertTrue(ok, detail)

    def test_ghostscript_pdf_optimization(self):
        if not self.converter.engines.ghostscript:
            self.skipTest("Ghostscript not detected")
        pdf = self.converter.convert(self.source, ".pdf", self.root / "out", self.options)[0]
        optimized = self.converter.convert(pdf, ".pdf", self.root / "optimized", self.options)[0]
        ok, detail = verify_output(optimized, ".pdf")
        self.assertTrue(ok, detail)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="formatbridge_archive_")
        self.root = Path(self.temp.name)
        self.data = self.root / "입력"
        (self.data / "하위").mkdir(parents=True)
        (self.data / "안녕.txt").write_text("안녕하세요", encoding="utf-8")
        (self.data / "하위" / "data.bin").write_bytes(bytes(range(256)) * 4)

    def tearDown(self):
        self.temp.cleanup()

    def _archive_roundtrip(self, ext: str, password: str | None = None):
        archive = self.root / f"bundle{ext}"
        create_archive([self.data], archive, level=7, password=password)
        valid, detail = validate_archive(archive, password)
        self.assertTrue(valid, detail)
        destination = self.root / f"extract_{ext.replace('.', '_')}"
        extract_archive(archive, destination, password=password)
        restored = destination / "입력" / "안녕.txt"
        self.assertEqual(restored.read_text(encoding="utf-8"), "안녕하세요")
        self.assertEqual((destination / "입력" / "하위" / "data.bin").read_bytes(), bytes(range(256)) * 4)

    def test_zip_tar_and_7z_roundtrips(self):
        for ext, password in ((".zip", None), (".tar.gz", None), (".7z", "안전한암호123!")):
            with self.subTest(ext=ext):
                self._archive_roundtrip(ext, password)

    def test_zip_slip_is_blocked(self):
        archive = self.root / "malicious.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("../escape.txt", "blocked")
        with self.assertRaises(ValueError):
            extract_archive(archive, self.root / "safe")
        self.assertFalse((self.root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
