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

def get_url_list(sentence):
    sentences_url_list = []
    
    with open('result.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
        for entry in data:
            if entry['sentence'] == sentence:
                sentences_url_list.extend(entry['results'])
    return sentences_url_list

def fetch_and_extract_text(sentence_url):
    driver = setup_driver()
    if not driver:
        return "", "Lỗi: Không thể khởi tạo WebDriver"

    try:
        if len(sentence_url) > 2048:
            return "", f"Lỗi: URL quá dài ({len(sentence_url)} ký tự)"

        driver.get(sentence_url)
        time.sleep(random.uniform(2, 4))

        if "captcha" in driver.current_url.lower() or "sorry" in driver.current_url.lower():
            return "", "Lỗi: Bị chặn bởi CAPTCHA hoặc trang lỗi"

        soup = BeautifulSoup(driver.page_source, "lxml")

        for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            element.decompose()

        text = soup.get_text(separator=" ", strip=True)

        cleaned_text = re.sub(r'\s+', ' ', text).strip()

        return cleaned_text, "Thành công"

    except Exception as e:
        return "", f"Lỗi: Không thể tải trang hoặc xử lý kết quả ({str(e)})"
    
    finally:
        if driver:
            driver.quit()

def check_plagiarism(sentence, extracted_text):
    sentence_clean = re.sub(r'\s+', ' ', sentence).strip()
    extracted_text_clean = re.sub(r'\s+', ' ', extracted_text).strip()
    
    if sentence_clean in extracted_text_clean:
        return True
    return False

if __name__ == "__main__":
    with open('result.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    updated_data = []
    processed_sentences = set()

    for entry in data:
        sentence = entry['sentence']
        if sentence not in processed_sentences:
            processed_sentences.add(sentence)
            url_list = get_url_list(sentence)
            updated_results = []
            
            for result in url_list:
                text, status = fetch_and_extract_text(result['link'])
                print(f"Processing URL: {result['link']}")
                print(f"Status: {status}")
                
                has_plagiarism = check_plagiarism(sentence, text) if status == "Thành công" else False
                result['has_plagiarism'] = has_plagiarism
                updated_results.append(result)
            
            updated_data.append({
                'sentence': sentence,
                'results': updated_results
            })
    
    with open('result.json', 'w', encoding='utf-8') as file:
        json.dump(updated_data, file, ensure_ascii=False, indent=4)
    
    print("Đã cập nhật result.json với trạng thái đạo văn")