from google import genai
from google.genai import types
import itertools
import time
import json
import random
import re
import logging
from typing import List, Dict
import re
from html import escape


class GeminiPlagiarismChecker:
    def __init__(self, api_keys: List[str], models: List[str]):
        self.api_keys = api_keys
        self.models = models
        self.api_cycle = itertools.cycle(api_keys)
        self.model_cycle = itertools.cycle(models)

    def _create_client(self):
        api_key = next(self.api_cycle)
        return genai.Client(api_key=api_key)

    @staticmethod
    def _safe_load_json(raw: str):
        if not raw or not isinstance(raw, str):
            return None
        
        cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE)
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            logging.info("Không tìm thấy JSON trong output.")
            return None

        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logging.info(f"JSONDecodeError: {e}")
            logging.info("----- RAW preview -----")
            logging.info(raw[:500])
            logging.info("-----------------------")
            return None

    def _check_batch(self, sentences: List[str]):
        client = self._create_client()
        model = next(self.model_cycle)
        start_time = time.time()

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

        config = types.GenerateContentConfig(
            tools=[
                types.Tool(
                    google_search=types.GoogleSearch()
                )
            ]
        )

        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            elapsed = time.time() - start_time
            logging.info(f"Model: {model}, Thời gian: {elapsed:.2f}s")
            return resp.text.strip()

        except Exception as e:
            logging.info(f"[Lỗi] {type(e).__name__}: {e}")
            time.sleep(random.uniform(2, 5))
            return self._check_batch(sentences)

    def check(self, all_sentences: List[str], batch_size=10) -> Dict:
        results = []
        for i in range(0, len(all_sentences), batch_size):
            batch = all_sentences[i:i+batch_size]
            logging.info(f"\nBatch {i//batch_size + 1} ({len(batch)} câu)...")

            raw = self._check_batch(batch)
            logging.info(f"Raw response:\n{raw}\n")

            data = self._safe_load_json(raw)

            if data and isinstance(data, dict) and "results" in data:
                results.extend(data["results"])
            else:
                logging.error("JSON lỗi hoặc không hợp lệ. Gắn dữ liệu mặc định False.")

                # Thêm từng câu trong batch với flag mặc định
                for line in batch:
                    results.append({
                        "line": line,
                        "plagiarized": False,
                        "sources": []
                    })

            time.sleep(random.uniform(3, 6))

        final = {"results": results}

        with open("log/check.json", "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)

        return final

    
    def highlight_text(self, original_text: str, details: list) -> str:
        """
        Tô màu các đoạn văn bị đạo văn dựa trên kết quả từ Gemini API.
        details: [{ "matched_text": "...", "source": "...", "score": float }]
        """
        details = [d for d in details if isinstance(d, dict)]
        html = escape(original_text)

        # Sắp xếp theo độ dài giảm dần để tránh overlap
        sorted_details = sorted(details, key=lambda d: len(d.get("matched_text", "")), reverse=True)

        for item in sorted_details:
            match = escape(item.get("matched_text", "").strip())
            if not match:
                continue

            score = item.get("score", 0)
            color = self._get_color(score)

            pattern = re.escape(match)
            html = re.sub(
                pattern,
                f'<span class="highlight" style="background-color:{color}" '
                f'data-score="{score}">{match}</span>',
                html,
                flags=re.IGNORECASE
            )

        return html

    def _get_color(self, score: float) -> str:
        """Tạo màu sắc highlight theo tỷ lệ trùng lặp."""
        if score >= 0.8:
            return "#ff6b6b"  # đỏ: trùng cao
        if score >= 0.5:
            return "#ffd93d"  # vàng: trùng trung bình
        return "#a0e7e5"  # xanh nhạt: trùng thấp

# ==========================================
if __name__ == "__main__":
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

    checker = GeminiPlagiarismChecker(API_KEYS, MODELS)

    sentences = [
        "Ngay từ nhỏ, chúng ta đã có khái niệm về tiền bạc.",
        "Đó là một cuộc chiến mà đồng tiền là súng đạn và mức sát thương thật là ghê gớm.",
        "Cuộc sống là chuỗi ngày học hỏi và trải nghiệm, vì vậy hãy biết ơn nó.",
        "Hạnh phúc không phải là đích đến mà là hành trình ta trải qua mỗi ngày.",
        "Thành công không đo bằng tiền bạc mà bằng sự hài lòng trong tâm hồn.",
        "Nếu tui là gia cát lượng thì tui đã không để cho ngươi làm việc này.",
    ]

    result = checker.check(sentences, batch_size=2)
    logging.info("\n✅ Kết quả cuối cùng:")
    logging.info(json.dumps(result, ensure_ascii=False, indent=2))
