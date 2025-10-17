from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
import time
import re
import urllib.parse
import json
import random
import os



def setup_driver(proxy=None):
    s = Service('./msedgedriver.exe')
    options = Options()
    options.use_chromium = True
    options.add_argument("--headless=new")  
    options.add_argument("--window-size=1000,800")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=vi-VN")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")


    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/141.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    options.add_argument(f"--user-agent={random.choice(ua_list)}")

    if proxy:
        options.add_argument(f"--proxy-server={proxy}")

    try:
        driver = webdriver.Edge(service=s, options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver
    except Exception as e:
        print(f"Lỗi khởi tạo WebDriver: {e}")
        return None


def split_sentences(text, output_file="sentences_list.json"):
    # 1️⃣ Chuẩn hóa văn bản
    text = re.sub(r'\s+', ' ', text.strip())

    # 2️⃣ Regex tách câu theo . ? ! (kể cả khi không có khoảng trắng sau dấu)
    sentences = re.split(r'(?<=[.!?])(?=\s+|[A-ZÀ-Ỹ(“"])', text)

    result = []

    # 3️⃣ Duyệt từng câu
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # 4️⃣ Cắt câu quá dài nếu cần
        while len(urllib.parse.quote(sentence)) > 1800:
            mid = len(sentence) // 2
            split_point = max(
                sentence.rfind('.', 0, mid),
                sentence.rfind(',', 0, mid),
                sentence.rfind(' ', 0, mid)
            )
            if split_point == -1:
                split_point = mid
            part = sentence[:split_point+1].strip()
            result.append(part)
            sentence = sentence[split_point+1:].strip()

        if sentence:
            result.append(sentence)

    # 5️⃣ Ghi file JSON (UTF-8, dạng danh sách câu)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Tách được {len(result)} câu hợp lệ. Đã ghi vào '{output_file}'.")
    return result




def search_sentence(sentence, num_results=5, proxy=None):
    driver = setup_driver(proxy)
    if not driver:
        return [], "Không thể khởi tạo WebDriver"

    data = [{"sentence": sentence, "results": []}]
    try:
        encoded_sentence = urllib.parse.quote(sentence)

        url = f"https://www.bing.com/search?q=\"{encoded_sentence}\"&count={num_results}&setLang=vi&mkt=vi-VN&cc=VN"
        if len(url) > 2048:
            return data, f"URL quá dài ({len(url)} ký tự)"

        driver.get(url)
        time.sleep(random.uniform(3, 6)) 

  
        if "captcha" in driver.current_url.lower() or "sorry" in driver.page_source.lower():
            return data, "Bị chặn CAPTCHA – thử lại với proxy khác"

        soup = BeautifulSoup(driver.page_source, "lxml")

  
        blocks = soup.select("li.b_algo, div.b_algo, div.b_card")[:num_results]
        for block in blocks:
            a = block.find("a", href=True)
            h2 = block.find("h2")
            snippet = block.find("p")

            link = a['href'] if a else "N/A"
            title = h2.get_text(strip=True) if h2 else "N/A"
            desc = snippet.get_text(strip=True) if snippet else "N/A"


            if not re.search(r'\.vn|bing\.com', link):
                continue

            data[0]["results"].append({
                "title": title,
                "link": link,
                "snippet": desc,
                "has_plagiarism": False
            })

        return data, "Thành công"
    except Exception as e:
        return data, f"Lỗi xử lý: {e}"
    finally:
        try:
            driver.quit()
        except:
            pass


def analyze_serp_structure(query, proxy=None):
    num_results = 5
    all_results = []
    seen_links = set()
    sentences = split_sentences(query)
    if not sentences:
        print("Không có câu hợp lệ.")
        return [], ""

    for i, sentence in enumerate(sentences, 1):
        print(f"\nCâu {i}: {sentence}")
        results, status = search_sentence(sentence, num_results=num_results, proxy=proxy)
        print(f"Trạng thái: {status}")

        if results and len(results) > 0:
            result_group = results[0]
            for result in result_group["results"]:
                if result["link"] not in seen_links:
                    seen_links.add(result["link"])
                    all_results.append({
                        "sentence": sentence,
                        "results": [result]
                    })
                    print(json.dumps({"sentence": sentence, "results": [result]}, ensure_ascii=False, indent=4))


        time.sleep(random.uniform(3, 7))

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)
    print("\nĐã lưu kết quả vào result.json")

    return all_results, ""


if __name__ == "__main__":
    try:
        if not os.path.exists("outputtest.txt"):
            print("Không tìm thấy file outputtest.txt")
        else:
            with open("outputtest.txt", "r", encoding="utf-8") as f:
                query = f.read().strip()
            analyze_serp_structure(query)
    except Exception as e:
        print(f"Lỗi khi chạy script: {e}")
