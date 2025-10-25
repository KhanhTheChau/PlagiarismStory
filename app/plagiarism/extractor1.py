import fitz
import re
import logging
from google import genai
from itertools import product
import logging

class PDFTextExtractor:
    def __init__(self, pdf_path: str, remove_chapter_titles: bool = True):
        self.pdf_path = pdf_path
        self.text = ""
        self.remove_chapter_titles = remove_chapter_titles

        self._chapter_pattern = re.compile(
            r'^\s*(?:CHƯƠNG|Chương|CHAP\.?|Chapter)\s+[\w\dIVXLCDM]+'
            r'(?:\s*[:\-–—.]\s*.*)?$'
        )

        # Hardcode key lưu trong code
        self._api_keys = [
            "AIzaSyAk4N7S067L5jcmr3kEfeTReA89XtFSJ4c",
        ]
        self._models = [
            "gemini-2.0-flash-lite"
        ]

        self._current_key = None
        self._current_model = None
        self._gen_clients_combo = product(self._api_keys, self._models)
        self._gem_client = None

        self._rotate_client()

    def _rotate_client(self):
        try:
            key, model = next(self._gen_clients_combo)
        except StopIteration:
            raise RuntimeError("Hết API key hoặc model để thử")
        self._current_key = key
        self._current_model = model
        self._gem_client = genai.Client(api_key=key)
        logging.info(f"Dùng key: {self._mask(key)}, model: {model}")

    def _mask(self, key: str):
        return key[:6] + "..." + key[-4:]

    def extract_text(self) -> str:
        pages = []
        with fitz.open(self.pdf_path) as doc:
            for page in doc:
                text = page.get_text("text").rstrip()
                if self._is_trash_page(text):
                    continue
                pages.append(text)
        raw = "\n\n".join(pages).strip()

        if self.remove_chapter_titles:
            raw = self._remove_chapter_titles(raw)

        self.text = raw
        return raw

    def _is_trash_page(self, text: str) -> bool:
        if not text.strip():
            return True
        if len(text.split()) <= 2 and text.strip().isdigit():
            return True
        return False

    def _remove_chapter_titles(self, text: str) -> str:
        lines = []
        for ln in text.splitlines():
            s = ln.strip()
            if s and self._chapter_pattern.match(s):
                continue
            lines.append(ln)
        return "\n".join(lines)

    def _ask_gemini(self, prompt: str) -> list:
        # auto retry khi lỗi với key/model khác
        for _ in range(len(self._api_keys) * len(self._models)):
            try:
                res = self._gem_client.models.generate_content(
                    model=self._current_model,
                    contents=prompt,
                    generation_config={"response_mime_type": "application/json"},
                )
                data = res.parsed
                logging.info(f"Response từ model {self._current_model} với key {self._mask(self._current_key)} nhận được.")
                logging.info(f"Raw response:\n{data}\n")
                if isinstance(data, dict) and "sentences" in data:
                    return data["sentences"]
                return []
            except Exception as e:
                logging.error(f"Lỗi key {self._mask(self._current_key)}: {e}")
                self._rotate_client()

        return []

    def _fix_format(self, text: str) -> list:
        prompt = f"""
            Bạn là chuyên gia xử lý PDF tiếng Việt.
            Yêu cầu:
            1) Ghép từ bị tách (v ì -> vì, s ựnh ư ý -> sự như ý)
            2) Gom câu thành câu văn hoàn chỉnh, đúng ngữ pháp
            3) Loại bỏ tiêu đề chương, header/footer, số trang
            4) Không bịa nội dung
            5) Trả về JSON chuẩn:
            {{
            "sentences": [
                "Câu 1",
                "Câu 2"
            ]
            }}


            Nội dung:
            {text}
            """
        return self._ask_gemini(prompt)

    def get_lines(self) -> list:
        if not self.text:
            self.extract_text()
        return [ln.rstrip() for ln in self.text.splitlines() if ln.strip()]

    def run(self, return_lines: bool = True):
        raw = self.extract_text()
        fixed_sentences = self._fix_format(raw)
        return (raw, fixed_sentences) if return_lines else raw
