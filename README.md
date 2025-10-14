# Hệ thống phát hiện đạo văn trong truyện.


## Cấu trúc hệ thống
plagiarism_app/
│
├── app.py                         # Flask web chính
├── plagiarism/
│   ├── __init__.py
│   ├── extractor.py               # Lớp PDFTextExtractor
│   └── checker.py                 # Lớp PlagiarismChecker (đa API key)
│
├── templates/
│   ├── index.html
│   └── result.html
│
├── static/
│   └── style.css
│
└── uploads/                       # nơi lưu file tạm khi người dùng upload
