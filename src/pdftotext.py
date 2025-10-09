import fitz
import re

class PDFTextExtractor:
    def __init__(self, pdf_path: str):
        """Khởi tạo với đường dẫn đến file PDF."""
        self.pdf_path = pdf_path
        self.text = ""

    def extract_text(self) -> str:
        """Đọc toàn bộ nội dung PDF và lưu vào self.text."""
        try:
            with fitz.open(self.pdf_path) as doc:
                self.text = " ".join(page.get_text().strip() for page in doc)
            # Gộp các dòng thành 1 chuỗi không xuống dòng
            self.text = re.sub(r'\s+', ' ', self.text).strip()
            return self.text
        except Exception as e:
            raise RuntimeError(f"Lỗi khi đọc PDF: {e}")

    def get_sentences(self) -> list[str]:
        """Trả về danh sách các câu (ngắt theo dấu chấm)."""
        if not self.text:
            self.extract_text()
        # Tách câu theo các dấu kết thúc thông thường (. ? !)
        sentences = re.split(r'(?<=[.!?])\s+', self.text)
        # Loại bỏ câu rỗng hoặc khoảng trắng thừa
        return [s.strip() for s in sentences if s.strip()]

    def save_to_file(self, output_path: str):
        """Lưu nội dung đã gộp vào file .txt"""
        if not self.text:
            self.extract_text()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.text)

    def run(self, output_path: str = None, return_sentences: bool = False):
        """
        Thực hiện toàn bộ quy trình:
        - Đọc PDF
        - Gộp nội dung thành 1 chuỗi
        - Ghi ra file nếu có output_path
        - Trả về kết quả (và mảng câu nếu cần)
        """
        text = self.extract_text()
        if output_path:
            self.save_to_file(output_path)
        if return_sentences:
            return text, self.get_sentences()
        return text


# ===============================
# 🚀 Ví dụ sử dụng
# ===============================


if __name__ == "__main__":
    extractor = PDFTextExtractor("./data/_chien-tranh-tien-te.pdf")
    text, sentences = extractor.run(output_path="output.txt", return_sentences=True)

    print("== Toàn bộ văn bản (rút gọn 300 ký tự) ==")
    print(text[:300] + "...")
    print("\n== Mảng câu mẫu ==")
    print(sentences[:5])
