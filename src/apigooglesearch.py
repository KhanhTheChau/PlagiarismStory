import requests
import re

# ====== CẤU HÌNH ======
GOOGLE_API_KEY = "xxxxxxxxxxxxxxxxxxxx"   # thay bằng key của bạn
CX = "xxxxxxxxxxxxx"       # thay bằng CX ID của bạn

# ====== HÀM TÁCH CÂU ======
def split_sentences(text):
    # Tách theo dấu chấm, chấm hỏi, chấm than
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

# ====== HÀM KIỂM TRA ĐẠO VĂN ======
def plagiarism_check_exact(text):
    sentences = split_sentences(text)
    total = len(sentences)
    copied = 0
    details = []

    for s in sentences:
        print(f"Đang kiểm tra: {s}")
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": GOOGLE_API_KEY, "cx": CX, "q": f'"{s}"'}  # tìm câu chính xác
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            items = data.get("items", [])

            if len(items) > 0:
                copied += 1
                # Lấy link đầu tiên (hoặc tất cả)
                sources = [item["link"] for item in items[:3]]  # lấy tối đa 3 nguồn
                details.append({
                    "sentence": s,
                    "plagiarized": True,
                    "sources": sources
                })
            else:
                details.append({
                    "sentence": s,
                    "plagiarized": False,
                    "sources": []
                })
        except Exception as e:
            print("Lỗi khi gọi API:", e)
            details.append({
                "sentence": s,
                "plagiarized": False,
                "sources": []
            })

    percent = (copied / total) * 100 if total else 0
    return percent, details

# ====== DEMO ======
if __name__ == "__main__":
    text = """Ngay từ nhỏ, chúng ta đã có khái niệm về tiền bạc.
    Tiền giúp ta mua những thứ cần thiết cho cuộc sống.
    Nhiều người sử dụng tiền một cách thiếu kiểm soát."""
    
    percent, details = plagiarism_check_exact(text)

    print("\n--- KẾT QUẢ ---")
    print(f"Tỉ lệ đạo văn: {percent:.2f}%\n")
    for d in details:
        print(f"- {d['sentence']}")
        if d['plagiarized']:
            print("  → Đạo văn từ các nguồn:")
            for src in d['sources']:
                print(f"     {src}")
        else:
            print("  → Không đạo văn")
        print("─" * 60)
