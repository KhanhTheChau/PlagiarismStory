import os
import time
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from plagiarism.extractor import PDFTextExtractor
from plagiarism.checker import GeminiPlagiarismChecker

# Cấu hình
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

from logger_config import setup_logging
setup_logging()  # Khởi tạo logging một lần

API_KEYS = [
        "AIzaSyASkCLE9cQdpT92Bh3ATNRbmVwMRfo5WVs",
        "AIzaSyAk4N7S067L5jcmr3kEfeTReA89XtFSJ4c",
    ]

MODELS = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-robotics-er-1.5-preview",
        "gemini-2.0-flash-lite"
    ]

ALLOWED_EXT = {"pdf"}

app = Flask(__name__)
app.secret_key = "change_this_secret_in_production"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Vui lòng chọn file PDF.")
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("Chỉ chấp nhận file PDF.")
            return redirect(request.url)

        filename = secure_filename(f"{int(time.time())}_{file.filename}")
        save_path = os.path.join(UPLOAD_DIR, filename)
        file.save(save_path)

        remove_chapters = bool(request.form.get("remove_chapters"))

        try:
            limit_lines = int(request.form.get("limit_lines", "30"))
        except ValueError:
            limit_lines = 30

        extractor = PDFTextExtractor(save_path, remove_chapter_titles=remove_chapters)
        full_text, lines = extractor.run()
        if not full_text.strip():
            flash("Không thể trích xuất nội dung từ file PDF.")
            return redirect(request.url)

        # Áp dụng limit trước khi gửi API
        limited_lines = lines[:limit_lines]

        checker = GeminiPlagiarismChecker(API_KEYS, MODELS)
        try:
            details = checker.check(limited_lines, batch_size=2)
        except Exception as e:
            flash(f"Lỗi kiểm tra đạo văn: {e}")
            return redirect(request.url)

        # Tính phần trăm câu bị trùng
        matched = sum(1 for r in details["results"] if r.get("exists"))
        percent = round((matched / max(1, len(details["results"]))) * 100, 2)

        # highlight HTML nội dung giới hạn
        # highlight_text phải trả về HTML an toàn
        highlighted_html = checker.highlight_text("\n".join(limited_lines), details)

        return render_template(
            "result.html",
            highlighted_text=highlighted_html,
            percent=percent,
            filename=filename,
            details=details,
            limit_lines=limit_lines
        )

    return render_template("index.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
