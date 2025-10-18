from google import genai
from google.genai import types
import itertools
import time
import json
import random
import logging

# ==========================================
logging.basicConfig(
    filename="check.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

# ==========================================
API_KEYS = [

]

# ==========================================
MODELS = [
    "gemini-2.0-flash",       
    "gemini-2.5-flash",  
    "gemini-robotics-er-1.5-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "learnlm-2.0-flash-experimental",
]

# ==========================================
api_cycle = itertools.cycle(API_KEYS)
model_cycle = itertools.cycle(MODELS)


def create_client():
    """Tạo client mới với API key kế tiếp"""
    api_key = next(api_cycle)
    return genai.Client(api_key=api_key)


# ==========================================
import json
import re

def extract_json_safe(response_text: str):
    """
    Tự động tìm và parse JSON từ chuỗi, bỏ qua text thừa, markdown, v.v.
    """
    try:
        # 1️⃣ Thử parse trực tiếp
        return json.loads(response_text)
    except json.JSONDecodeError:
        # 2️⃣ Nếu lỗi — cố tách phần JSON bằng regex
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # 3️⃣ Nếu vẫn lỗi — cố loại bỏ ký tự đặc biệt rồi parse lại
        cleaned = response_text.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print("⚠️ Không thể parse JSON:", e)
            print("Đoạn trả về bị lỗi:\n", response_text)
            return None
        
# ==========================================
def check_sentences(sentences):

    client = create_client()
    model = next(model_cycle)

    prompt = f"""
            Nhiệm vụ: Kiểm tra xem từng câu trong danh sách sau có tồn tại nguyên văn trên Google hay không.

            Yêu cầu:
            1. Tìm kiếm chính xác trên Google và trả về tối đa 5 url.
            2. Trả JSON duy nhất, không kèm văn bản hay markdown.
            3. Cấu trúc JSON:
            {{
            "results": [
                {{
                "query": "<câu 1>",
                "exists": true hoặc false,
                "links": ["https://...", ...]
                }},
                ...
            ]
            }}

            Danh sách câu cần kiểm tra:
            {chr(10).join([f'{i+1}. "{s}"' for i, s in enumerate(sentences)])}
        """
    logging.info(f"🔍 Batch bắt đầu | Model={model} | {len(sentences)} câu")
    
    config = types.GenerateContentConfig(
        tools=[
            types.Tool(
                google_search=types.GoogleSearch()
            )
        ]
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        
        return response.text.strip()

    except Exception as e:
        logging.warning("[⚠️ Lỗi]" +  {type(e).__name__} + ":" + {e})
        # Nếu lỗi quota hoặc rate limit, thử lại với model khác và key khác
        time.sleep(random.uniform(2, 5))
        return check_sentences(sentences)


# ==========================================
def batch_check(all_sentences, batch_size=10):
    results = []
    for i in range(0, len(all_sentences), batch_size):
        batch = all_sentences[i:i + batch_size]
        # print(f"\n🔍 Kiểm tra batch {i//batch_size + 1} ({len(batch)} câu)...")
        logging.info(f"🔍 Kiểm tra batch {i//batch_size + 1} ({len(batch)} câu)")

        raw_response = check_sentences(batch)
        # print(f"📄 Raw response:\n{raw_response}\n")
        logging.info(f"📄 Raw response:\n{raw_response}\n")
        raw = extract_json_safe(raw_response)
        logging.info(f"✅ raw: {raw}")
        try:
            data = json.loads(raw)
            results.extend(data.get("results", []))
        except json.JSONDecodeError:
            # print("⚠️ JSON lỗi hoặc không hợp lệ, bỏ qua batch này.")
            logging.warning("⚠️ JSON lỗi hoặc không hợp lệ, bỏ qua batch này.")

        time.sleep(random.uniform(3, 6))  # tránh giới hạn RPM
    
    with open("check_results.json", "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, ensure_ascii=False, indent=2)
        
    return {"results": results}



# ==========================================
if __name__ == "__main__":
    sentences = [
        "Ngay từ nhỏ, chúng ta đã có khái niệm về tiền bạc.",
        "Đó là một cuộc chiến mà đồng tiền là súng đạn và mức sát thương thật là ghê gớm.",
        "Cuộc sống là chuỗi ngày học hỏi và trải nghiệm, vì vậy hãy biết ơn nó.",
        "Hạnh phúc không phải là đích đến mà là hành trình ta trải qua mỗi ngày.",
        "Thành công không đo bằng tiền bạc mà bằng sự hài lòng trong tâm hồn.",
        "Nếu tui là gia cát lượng thì tui đã không để cho ngươi làm việc này.",
    ]

    final_result = batch_check(sentences, batch_size=2)
    # print("\n✅ Kết quả cuối cùng:")
    logging.info("\n✅ Kết quả cuối cùng:")
    # print(json.dumps(final_result, ensure_ascii=False, indent=2))
    logging.info(json.dumps(final_result, ensure_ascii=False, indent=2))
