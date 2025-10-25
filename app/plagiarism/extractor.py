import fitz
import re
from typing import Tuple, List


class PDFTextExtractor:
    """
    Trích xuất nội dung PDF:
    - Giữ bố cục cơ bản nhưng xử lý xuống dòng thông minh
    - Loại tiêu đề chương
    - Tách câu chuẩn để gửi sang AI
    """

    def __init__(self, pdf_path: str, remove_chapter_titles: bool = True):
        self.pdf_path = pdf_path
        self.text = ""
        self.remove_chapter_titles = remove_chapter_titles

        # Mẫu nhận diện tiêu đề chương
        self._chapter_pattern = re.compile(
            r'^\s*(?:CHƯƠNG|Chương|CHAP\.?|Chapter)\s+[\w\dIVXLCDM]+'
            r'(?:\s*[:\-–—.]\s*.*)?$'
        )

    def extract_text(self) -> str:
        try:
            pages = []
            with fitz.open(self.pdf_path) as doc:
                for page in doc:
                    text = page.get_text("text").strip()
                    if self._is_trash_page(text):
                        continue
                    pages.append(text)

            raw = "\n".join(pages)

            # Xử lý layout PDF
            raw = self._fix_newlines(raw)

            # Loại tiêu đề chương
            if self.remove_chapter_titles:
                raw = self._remove_chapter_titles(raw)

            self.text = raw.strip()
            return self.text

        except Exception as e:
            raise RuntimeError(f"Lỗi khi đọc PDF: {e}")

    def _is_trash_page(self, text: str) -> bool:
        if not text.strip():
            return True
        if len(text.split()) <= 2 and text.strip().isdigit():
            return True
        return False

    def _fix_newlines(self, text: str) -> str:
        """Gom dòng thông minh để thành đoạn văn hoàn chỉnh"""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        merged = []
        buffer = ""

        end_sentence = re.compile(r'[.!?:…)\]]$')

        for ln in lines:

            # Nếu là tiêu đề ngắn
            if len(ln.split()) <= 5 and (ln.isupper() or ln.istitle()):
                if buffer:
                    merged.append(buffer)
                    buffer = ""
                merged.append(ln)
                continue

            if not buffer:
                buffer = ln
            else:
                if not end_sentence.search(buffer):
                    buffer += " " + ln
                else:
                    merged.append(buffer)
                    buffer = ln

        if buffer:
            merged.append(buffer)

        return "\n".join(merged)

    def _remove_chapter_titles(self, text: str) -> str:
        new_lines = []
        for ln in text.splitlines():
            cleaned = ln.strip()
            if cleaned and self._chapter_pattern.match(cleaned):
                continue
            new_lines.append(ln)
        return "\n".join(new_lines)

    def get_sentences(self) -> List[str]:
        """Trả danh sách câu đã xử lý sạch để gửi lên AI"""
        if not self.text:
            self.extract_text()

        return self._split_sentences(self.text)

    def _split_sentences(self, text: str) -> List[str]:
        """Tách câu bằng regex tiếng Việt chuẩn hơn"""
        # Ngắt câu theo dấu câu cơ bản
        parts = re.split(r'(?<=[.!?…])\s+', text)

        return [p.strip() for p in parts if p.strip()]

    def run(self) -> Tuple[str, List[str]]:
        text = self.extract_text()
        sentences = self.get_sentences()
        return text, sentences
