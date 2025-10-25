import fitz
import re
from typing import Tuple, List


class PDFTextExtractor:
    def __init__(self, pdf_path: str, remove_chapter_titles: bool = True):
        self.pdf_path = pdf_path
        self.text = ""
        self.remove_chapter_titles = remove_chapter_titles

        # Tiêu đề chương
        self._chapter_pattern = re.compile(
            r'^\s*(?:CHƯƠNG|Chương|CHAP\.?|Chapter)\s+[\w\dIVXLCDM]+'
            r'(?:\s*[:\-–—.]\s*.*)?$'
        )

        # Regex tách câu tiếng Việt
        self._sentence_pattern = re.compile(
            r'([^.!?…]+[.!?…]+)(?=\s+|$)'
        )

    def extract_text(self) -> str:
        try:
            pages = []
            with fitz.open(self.pdf_path) as doc:
                for page in doc:
                    text = page.get_text("text").rstrip()
                    if self._is_trash_page(text):
                        continue
                    pages.append(text)

            merged = "\n".join(pages)
            merged = self._merge_broken_lines(merged)

            if self.remove_chapter_titles:
                merged = self._remove_chapter_titles(merged)

            self.text = merged.strip()
            return self.text
        except Exception as e:
            raise RuntimeError(f"Lỗi đọc PDF: {e}")

    def _is_trash_page(self, text: str) -> bool:
        if not text.strip():
            return True
        if len(text.strip().split()) <= 2 and text.strip().isdigit():
            return True
        return False

    def _merge_broken_lines(self, text: str) -> str:
        """Gom các dòng bị xuống dòng giữa câu."""
        lines = text.splitlines()
        fixed = []
        for ln in lines:
            ln = ln.strip()

            if not ln:
                fixed.append("\n")
                continue

            # Nếu dòng cũ chưa kết thúc bằng ., !, ? mà dòng mới viết thường → nối lại
            if fixed and \
               not re.search(r'[.!?…]$', fixed[-1].strip()) and \
               re.search(r'^[a-zàáạảãâầấậẩẫăằắặẳẵêềếệểễôồốộổỗơờớợởỡưừứựửữ]', ln):
                fixed[-1] = fixed[-1].rstrip() + " " + ln
            else:
                fixed.append(ln)

        return "\n".join(fixed)

    def _remove_chapter_titles(self, text: str) -> str:
        new_lines = []
        for ln in text.splitlines():
            clean_ln = ln.strip()
            if clean_ln and self._chapter_pattern.match(clean_ln):
                continue
            new_lines.append(ln)
        return "\n".join(new_lines)

    def get_sentences(self) -> List[str]:
        if not self.text:
            self.extract_text()
        matches = self._sentence_pattern.findall(self.text)
        return [s.strip() for s in matches if len(s.strip()) > 3]

    def run(self) -> Tuple[str, List[str]]:
        text = self.extract_text()
        return (text, self.get_sentences())
