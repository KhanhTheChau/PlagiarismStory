from google import genai
from google.genai import types
import json

# ==========================================
# 🔑 Cấu hình API key (bắt buộc)
# ==========================================
client = genai.Client(api_key="")

# ==========================================
# 🧠 Prompt yêu cầu
# ==========================================
data = """
Nhiệm vụ: Kiểm tra xem từng câu trong danh sách sau có tồn tại nguyên văn trên Google hay không.

Hướng dẫn thực hiện:
1. Với mỗi câu trong danh sách, thực hiện tìm kiếm chính xác trên Google bằng cách đặt câu trong dấu ngoặc kép.
2. Với mỗi câu, trả về kết quả gồm:
   - "query": câu gốc
   - "exists": true/false
   - "links": tối đa 5 liên kết đầu tiên nếu có, ngược lại để mảng rỗng []
3. Trả về **duy nhất một JSON hợp lệ**, không thêm bất kỳ văn bản, mô tả hay markdown nào khác.
4. Không dùng ```json``` hoặc ký tự đặc biệt bao quanh JSON.

Cấu trúc JSON mong muốn:

{
  "results": [
    {
      "query": "<câu 1>",
      "exists": true hoặc false,
      "links": ["https://...", "https://..."]
    },
    {
      "query": "<câu 2>",
      "exists": false,
      "links": []
    }
  ]
}

Danh sách câu cần kiểm tra:
1. "Ngay từ nhỏ, chúng ta đã có khái niệm về tiền bạc."
2. "Đó là một cuộc chiến mà đồng tiền là súng đạn và mức sát thương thật là ghê gớm."
3. "Cuộc sống là chuỗi ngày học hỏi và trải nghiệm, vì vậy hãy biết ơn nó."
"""

# ==========================================
# 🚀 Gọi mô hình với công cụ Google Search
# ==========================================
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=data,
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(
                google_search=types.GoogleSearch()
            )
        ]
    )
)

# ==========================================
# 🖨️ In kết quả JSON thuần
# ==========================================
try:
    result_json = json.loads(response.text)
    print(json.dumps(result_json, indent=2, ensure_ascii=False))
except json.JSONDecodeError:
    print(response.text)
