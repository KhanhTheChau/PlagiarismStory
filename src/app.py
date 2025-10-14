import os
import time
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from plagiarism.extractor import PDFTextExtractor
from plagiarism.checker import PlagiarismChecker

# Cấu hình
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Thay bằng API key thật và cx id của bạn. Nếu để rỗng, app sẽ không gọi Google API.
API_KEYS = [
    "",
    # "YOUR_GOOGLE_API_KEY_2",
]

CX_IDS = [
    "",
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

        # Option: bỏ các dòng tiêu đề như CHƯƠNG ... nếu người dùng tick
        remove_chapters = bool(request.form.get("remove_chapters"))
        # Số dòng tối đa sẽ kiểm tra (để demo/tiết kiệm quota)
        try:
            limit_lines = int(request.form.get("limit_lines", "30"))
        except ValueError:
            limit_lines = 30

        # 1) Extract text
        extractor = PDFTextExtractor(save_path, remove_chapter_titles=remove_chapters)
        full_text, lines = extractor.run()

        # 2) Check plagiarism
        checker = PlagiarismChecker(API_KEYS, CX_IDS)
        percent, details = checker.check_text(full_text, lines=lines, limit=limit_lines)

        # 3) Highlight (returns HTML-safe string with <br> preserved)
        highlighted_html = checker.highlight_text(full_text, details)

        # trả về view
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
