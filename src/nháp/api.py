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


# =============================
# Cấu hình trình duyệt Edge
# =============================
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


# =============================
# Tách câu văn tiếng Việt
# =============================
def split_sentences(text, output_file="sentences_list.json", max_len=400):
    text = re.sub(r'\s+', ' ', text.strip())

    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÀ-Ỹ“(])', text)

    result = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        while len(sentence) > max_len or len(urllib.parse.quote(sentence)) > 1800:
            mid = len(sentence) // 2

            # Tìm điểm tách gần giữa — ưu tiên dấu câu
            split_point = max(
                sentence.rfind('.', 0, mid),
                sentence.rfind(',', 0, mid),
                sentence.rfind(' ', 0, mid)
            )

            # Nếu không tìm thấy vị trí phù hợp, chia đôi thẳng
            if split_point == -1 or split_point < 50:
                split_point = mid

            part1 = sentence[:split_point + 1].strip()
            part2 = sentence[split_point + 1:].strip()

            print(f"⚠️ Câu dài, tách làm 2 phần:\n  1️⃣ {part1[:100]}...\n  2️⃣ {part2[:100]}...")

            if part1:
                result.append(part1)

            # Tiếp tục xử lý phần còn lại (có thể vẫn dài)
            sentence = part2

        if sentence:
            result.append(sentence)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Đã tách được {len(result)} câu hợp lệ và lưu vào '{output_file}'.")
    return result


# =============================
# Tìm kiếm từng câu trên Bing
# =============================
def search_sentence(sentence, num_results=5, proxy=None):
    driver = setup_driver(proxy)
    if not driver:
        return [{"sentence": sentence, "results": [], "error": "Không thể khởi tạo WebDriver"}]

    data = [{"sentence": sentence, "results": []}]
    try:
        query = f'"{sentence}"'
        url = f"https://www.bing.com/search?q={query}&count={num_results}&setLang=vi&mkt=vi-VN&cc=VN"

        # Kiểm tra URL dài
        if len(url) > 2048:
            # Câu quá dài => chia đôi
            parts = [sentence[:len(sentence)//2], sentence[len(sentence)//2:]]
            print(f"Câu quá dài, chia thành 2 phần:\n{parts[0]}\n{parts[1]}")
            all_data = []
            for part in parts:
                all_data.extend(search_sentence(part, num_results, proxy))
            return all_data

        # --- Lần tìm kiếm đầu tiên (có ngoặc kép) ---
        driver.get(url)
        time.sleep(random.uniform(3, 6))

        if "captcha" in driver.current_url.lower() or "sorry" in driver.page_source.lower():
            data[0]["error"] = "Bị chặn CAPTCHA – thử lại với proxy khác"
            return data

        soup = BeautifulSoup(driver.page_source, "lxml")
        blocks = soup.select("li.b_algo, div.b_algo, div.b_card")[:num_results]

        for block in blocks:
            a = block.find("a", href=True)
            title_tag = block.find("h2")
            snippet_tag = block.find("p")

            link = a["href"] if a else ""
            title = title_tag.get_text(strip=True) if title_tag else ""
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            if not link or not title:
                continue
            if "sex" in link.lower() or "porn" in link.lower():
                continue

            data[0]["results"].append({
                "title": title,
                "link": link,
                "snippet": snippet,
                "has_plagiarism": False
            })

        # Nếu không tìm thấy kết quả, thử lại không có ngoặc kép
        if not data[0]["results"]:
            print(f"Không tìm thấy kết quả cho câu (có ngoặc kép), thử lại không ngoặc kép:\n→ {sentence[:100]}...")
            driver.quit()  # Đóng driver cũ
            time.sleep(random.uniform(2, 4))

            driver_retry = setup_driver(proxy)
            if not driver_retry:
                data[0]["error"] = "Không thể khởi tạo WebDriver khi tìm lại"
                return data

            query2 = urllib.parse.quote(sentence)
            url2 = f"https://www.bing.com/search?q={query2}&count={num_results}&setLang=vi&mkt=vi-VN&cc=VN"
            driver_retry.get(url2)
            time.sleep(random.uniform(3, 6))

            if "captcha" in driver_retry.current_url.lower() or "sorry" in driver_retry.page_source.lower():
                data[0]["error"] = "Bị chặn CAPTCHA khi thử lại – thử proxy khác"
                driver_retry.quit()
                return data

            soup2 = BeautifulSoup(driver_retry.page_source, "lxml")
            blocks2 = soup2.select("li.b_algo, div.b_algo, div.b_card")[:num_results]

            for block in blocks2:
                a = block.find("a", href=True)
                title_tag = block.find("h2")
                snippet_tag = block.find("p")

                link = a["href"] if a else ""
                title = title_tag.get_text(strip=True) if title_tag else ""
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if not link or not title:
                    continue
                if "sex" in link.lower() or "porn" in link.lower():
                    continue

                data[0]["results"].append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "has_plagiarism": False,
                    "retry_without_quotes": True
                })

            driver_retry.quit()

        # Nếu sau cả hai lần vẫn rỗng
        if not data[0]["results"]:
            data[0]["error"] = "Không tìm thấy kết quả dù đã thử lại không ngoặc kép"

        return data

    except Exception as e:
        data[0]["error"] = f"Lỗi xử lý: {e}"
        return data
    finally:
        try:
            driver.quit()
        except:
            pass


# =============================
# Chạy toàn bộ pipeline
# =============================
def analyze_serp_structure(query, proxy=None):
    num_results = 5
    all_results = []
    sentences = split_sentences(query)
    if not sentences:
        print("Không có câu hợp lệ.")
        return [], ""

    for i, sentence in enumerate(sentences, 1):
        print(f"\n🔹 Câu {i}/{len(sentences)}: {sentence}")
        results = search_sentence(sentence, num_results=num_results, proxy=proxy)
        for res in results:
            all_results.append(res)
            print(json.dumps(res, ensure_ascii=False, indent=4))
        time.sleep(random.uniform(3, 7))

    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)

    print("\nĐã lưu kết quả vào result.json")
    return all_results, ""


# =============================
# Chạy chính
# =============================
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
