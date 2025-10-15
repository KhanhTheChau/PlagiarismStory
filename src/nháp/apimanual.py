from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import time
import re
import urllib.parse
import json
import random

def setup_driver():
    s = Service('./chromedriver.exe')
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")  # Bật chế độ headless
    options.add_argument("--window-size=1000,800")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    try:
        driver = webdriver.Chrome(service=s, options=options)
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

def search_sentence(sentence):
    driver = setup_driver()
    if not driver:
        return [], "Lỗi: Không thể khởi tạo WebDriver"

    results = []
    try:
        encoded_sentence = urllib.parse.quote(sentence)
        url = f"https://www.google.com/search?q={encoded_sentence}&num=5&hl=vi"
        if len(url) > 2048:
            return results, f"Lỗi: URL quá dài ({len(url)} ký tự)"
        
        driver.get(url)
        time.sleep(random.uniform(3, 5)) 

        if "captcha" in driver.current_url.lower() or "sorry" in driver.current_url.lower():
            return results, "Lỗi: Bị chặn bởi CAPTCHA"

        soup = BeautifulSoup(driver.page_source, "lxml")
        blocks = soup.find_all("div", class_="tF2Cxc")[:2]  # Lấy tối đa 2 kết quả

        for block in blocks:
            a = block.find("a", href=True)
            h3 = block.find("h3")
            snippet = block.find("div", class_="VwiC3b") or block.find("span", class_="aCOpRe")
            
            item = {
                "title": h3.get_text(strip=True) if h3 else "N/A",
                "link": a['href'] if a else "N/A",
                "snippet": snippet.get_text(strip=True) if snippet else "N/A"
            }
            results.append(item)

        return results, "Thành công"
    except Exception:
        return results, "Lỗi: Không thể tải trang hoặc xử lý kết quả"
    finally:
        if driver:
            driver.quit()

def analyze_serp_structure(query="python"):
    """Phân tích SERP, tìm kiếm từng câu từ query, giữ 2 URL mỗi câu, và loại bỏ trùng lặp."""
    all_results = []
    seen_links = set()


    query_sentences = split_sentences(query)
    if not query_sentences:
        print("Query không chứa câu nào hợp lệ (ít nhất 5 từ và chứa từ khóa liên quan).")
        return [], ""


    for i, sentence in enumerate(query_sentences, 1):
        print(f"\nCâu {i}: {sentence}")
        results, status = search_sentence(sentence)
        print(f"Trạng thái: {status}")
        print(f"URL lấy được: {[result['link'] for result in results]}")
        
        for result in results:
            if result["link"] not in seen_links:
                seen_links.add(result["link"])
                all_results.append({
                    "title": result["title"],
                    "link": result["link"],
                    "snippet": result["snippet"]
                })
                print(json.dumps({
                    "title": result["title"],
                    "link": result["link"],
                    "snippet": result["snippet"]
                }, ensure_ascii=False, indent=4))


    try:
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)
        print("\nKết quả đã được lưu vào file result.json dưới dạng JSON.")
    except Exception as e:
        print(f"Lỗi khi lưu file result.json: {e}")

    return all_results, ""

if __name__ == "__main__":
    try:
        query = ""
        with open("output.txt", "r", encoding="utf-8") as f:
            query = f.read().strip()
        results, html_content = analyze_serp_structure(query)
        if not results:
            print("Không tìm thấy kết quả nào!")
    except Exception as e:
        print(f"Lỗi khi chạy script: {e}")