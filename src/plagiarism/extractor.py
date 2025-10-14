import fitz
import re
from typing import Tuple, List

class PDFTextExtractor:
    """
    Đọc file PDF và giữ nguyên bố cục gốc (xuống dòng, bullet...). 
    Có tuỳ chọn loại bỏ các tiêu đề dạng "CHƯƠNG ..." trước khi trả về text/lines.
    """
    def __init__(self, pdf_path: str, remove_chapter_titles: bool = True):
        self.pdf_path = pdf_path
        self.text = ""
        self.remove_chapter_titles = remove_chapter_titles

        # pattern để bắt các tiêu đề CHƯƠNG I / CHƯƠNG 1 / CHƯƠNG MỘT (cơ bản)
        self._chapter_pattern = re.compile(
            r'^\s*(CHƯƠNG\s+[\w\dIVXLCDM\-]+|CHAP\.\s*[\w\d]+)\s*[:\-–—]?\s*$', re.IGNORECASE
        )

    def extract_text(self) -> str:
        """Đọc toàn bộ nội dung PDF, giữ nguyên layout (dạng text per line)."""
        try:
            with fitz.open(self.pdf_path) as doc:
                pages = []
                for page in doc:
                    # "text" giữ layout thô theo dòng
                    page_text = page.get_text("text")
                    # một số PDF có trailing whitespaces
                    pages.append(page_text.rstrip())
                # ngắt giữa các trang bằng 2 dòng trống để dễ phân biệt
                self.text = "\n\n".join(pages).strip()
            if self.remove_chapter_titles:
                self.text = self._remove_chapter_titles(self.text)
            return self.text
        except Exception as e:
            raise RuntimeError(f"Lỗi khi đọc PDF: {e}")

    def _remove_chapter_titles(self, text: str) -> str:
        """Xoá các dòng chỉ chứa 'CHƯƠNG ...' để loại bỏ tiêu đề chương."""
        lines = text.splitlines()
        filtered = []
        for ln in lines:
            if ln.strip() == "":
                filtered.append(ln)
                continue
            # nếu dòng khớp pattern thì bỏ qua
            if self._chapter_pattern.match(ln.strip()):
                # bỏ dòng
                continue
            filtered.append(ln)
        return "\n".join(filtered)

    def get_lines(self) -> List[str]:
        """Trả về list các dòng (giữ format), loại bỏ dòng trắng thừa."""
        if not self.text:
            self.extract_text()
        # giữ nguyên thứ tự và format per-line
        lines = [ln.rstrip() for ln in self.text.splitlines()]
        # loại bỏ những dòng chỉ chứa spaces
        return [ln for ln in lines if ln.strip()]

    def run(self, return_lines: bool = True) -> Tuple[str, List[str] or str]:
        text = self.extract_text()
        if return_lines:
            return text, self.get_lines()
        return text
