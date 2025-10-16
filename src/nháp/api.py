from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
import time
import re
import urllib.parse
import json
import random

def setup_driver():
    s = Service('./msedgedriver.exe')
    options = Options()
    options.use_chromium = True
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1000,800")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/141.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")

    try:
        driver = webdriver.Edge(service=s, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver
    except Exception:
        return None

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

def search_sentence(sentence, num_results):
    driver = setup_driver()
    if not driver:
        return [], "Lỗi: Không thể khởi tạo WebDriver"

    data = [{"sentence": sentence, "results": []}]
    try:
        encoded_sentence = urllib.parse.quote(sentence)
        url = f"https://www.bing.com/search?q={encoded_sentence}&count={num_results}"
        if len(url) > 2048:
            return data, f"Lỗi: URL quá dài ({len(url)} ký tự)"
        
        driver.get(url)
        time.sleep(random.uniform(2, 4))  # Đợi ngẫu nhiên để tránh bị chặn

        if "captcha" in driver.current_url.lower() or "sorry" in driver.current_url.lower():
            return data, "Lỗi: Bị chặn bởi CAPTCHA"

        soup = BeautifulSoup(driver.page_source, "lxml")
        blocks = soup.find_all("li", class_="b_algo")[:num_results]

        for block in blocks:
            a = block.find("a", href=True)
            h2 = block.find("h2")
            snippet = block.find("p")
            data[0]["results"].append({
                "title": h2.get_text(strip=True) if h2 else "N/A",
                "link": a['href'] if a else "N/A",
                "snippet": snippet.get_text(strip=True) if snippet else "N/A",
                "has_plagiarism": False
            })

        return data, "Thành công"
    except Exception as e:
        return data, f"Lỗi: Không thể tải trang hoặc xử lý kết quả ({str(e)})"
    finally:
        if driver:
            driver.quit()

def analyze_serp_structure(query):
    num_results = 5  # Số url cần lấy cho mỗi câu
    all_results = []
    seen_links = set()
    query_sentences = split_sentences(query)
    if not query_sentences:
        print("Query không chứa câu nào hợp lệ.")
        return [], ""
    for i, sentence in enumerate(query_sentences, 1):
        print(f"\nCâu {i}: {sentence}")
        results, status = search_sentence(sentence, num_results)
        print(f"Trạng thái: {status}")
        if results and len(results) > 0:  
            result_group = results[0] 
            if result_group["sentence"] == sentence:  
                for result in result_group["results"]:  
                    if result["link"] not in seen_links:
                        seen_links.add(result["link"])
                        all_results.append({
                            "sentence": sentence,
                            "results": [result]
                        })
                        print(json.dumps({"sentence": sentence, "results": [result]}, ensure_ascii=False, indent=4))
    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)
    print("\nĐã lưu kết quả vào result.json")
    return all_results, ""

if __name__ == "__main__":
    try:
        query = ""
        with open("outputtest.txt", "r", encoding="utf-8") as f:
            query = f.read().strip()
        analyze_serp_structure(query)
    except Exception as e:
        print(f"Lỗi khi chạy script: {e}")
