import google.generativeai as genai
import re
import json
import time
import random

GEMINI_API_KEY = "AIzaSyAv42WYzIpmW-ZChqMkX_b0Q4_PjZGkPKw"  


def split_sentences(text):
    sentences = re.split(r'(?<=\.)\s+', text.strip())
    result = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        while len(sentence) > 2048:
            result.append(sentence[:2048])
            sentence = sentence[2048:].strip()
        if sentence:
            result.append(sentence)
    
    return result

def search_sentence(sentence):
    results = []
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
Search for the exact sentence: "{sentence}".
Return exactly 2 search results as a JSON list, each with keys: "title", "link", "snippet". 
Only return JSON, no extra text. Links must start with http status 200 and now is accessible and active, can find. If no results are found, return [].
Example:[
  {{
    "title": "Article about this sentence",
    "link": "https://example.com/",
    "snippet": "Content related to the searched sentence..."
  }},
  {{
    "title": "Another source",
    "link": "https://example.com/",
    "snippet": "More details about the sentence..."
  }}
]
"""
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        json_response = json.loads(response_text)
        if isinstance(json_response, list):
            results = [r for r in json_response if r.get('link', '').startswith('http')][:2]
        return results, "Thành công" if results else "Lỗi: Không tìm thấy URL hợp lệ"
    except json.JSONDecodeError:
        print(f"Debug: Phản hồi thô từ Gemini: {response_text}")
        return results, f"Lỗi: Không thể parse JSON từ Gemini response"
    except Exception as e:
        return results, f"Lỗi: {str(e)}"
    finally:
        time.sleep(random.uniform(0.5, 1.5))


def analyze_serp_structure(text):
    all_results = []
    seen_links = set()
    sentences = split_sentences(text)

    if not sentences:
        print("Không có câu nào hợp lệ.")
        return []

    for i, sentence in enumerate(sentences, 1):
        print(f"\nCâu {i}: {sentence}")
        results, status = search_sentence(sentence)
        print(f"Trạng thái: {status}")
        urls = [result.get('link', 'N/A') for result in results]
        print(f"URL lấy được: {urls}")

        for result in results:
            link = result.get('link', 'N/A')
            if link not in seen_links and link.startswith('http'):
                seen_links.add(link)
                all_results.append({
                    "title": result.get('title', 'N/A'),
                    "link": link,
                    "snippet": result.get('snippet', 'N/A')
                })
                print(json.dumps({
                    "title": result.get('title', 'N/A'),
                    "link": link,
                    "snippet": result.get('snippet', 'N/A')
                }, ensure_ascii=False, indent=4))

    try:
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
        print("\nKết quả đã được lưu vào file result.json.")
    except Exception as e:
        print(f"Lỗi khi lưu file result.json: {e}")

    return all_results


if __name__ == "__main__":
    try:
        with open("outputtest.txt", "r", encoding="utf-8") as f:
            text = f.read().strip()
        results = analyze_serp_structure(text)
        if not results:
            print("Không tìm thấy kết quả nào!")
    except Exception as e:
        print(f"Lỗi khi chạy script: {e}")