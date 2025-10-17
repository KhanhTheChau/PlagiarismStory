from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from bs4 import BeautifulSoup
import time
import re
import json
import random
from pdftotext import PDFTextExtractor
import os
import tempfile
import requests
import docx
import unicodedata

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
    url_list = []
    with open("result.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        for entry in data:
            if entry["sentence"] == sentence:
                for result in entry["results"]:
                    url_list.append(result)
    return url_list

def fetch_other_type_file(url: str, type_file: str):
    try:
        if not url.lower().startswith(("http://", "https://")):
            return "", [], f"Lỗi: URL không hợp lệ ({url})"
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        suffix = f".{type_file.lower()}"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(tmp_fd, "wb") as tmp_file:
            tmp_file.write(resp.content)
        if type_file.lower() == "pdf":
            extractor = PDFTextExtractor(tmp_path)
            text = extractor.extract_text()
            sentences = extractor.get_sentences()
            status = "Thành công"
        elif type_file.lower() == "docx":
            doc = docx.Document(tmp_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            text = " ".join(paragraphs)
            sentences = re.split(r'(?<=[.!?])\s+', text)
            status = "Thành công"
        elif type_file.lower() == "txt":
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            text = re.sub(r'\s+', ' ', text).strip()
            sentences = re.split(r'(?<=[.!?])\s+', text)
            status = "Thành công"
        elif type_file.lower() == "doc":
            text = ""
            sentences = []
            status = "Lỗi: Chưa hỗ trợ định dạng DOC."
        else:
            text = ""
            sentences = []
            status = f"Lỗi: Không nhận dạng được định dạng '{type_file}'."
        return text, sentences, status
    except requests.exceptions.RequestException as e:
        return "", [], f"Lỗi khi tải file: {e}"
    except Exception as e:
        return "", [], f"Lỗi khi đọc file {type_file}: {e}"
    finally:
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

def convert_google_docs_url(url: str):
    match = re.search(r'document/d/([a-zA-Z0-9_-]+)', url)
    if match:
        doc_id = match.group(1)
        return f"https://docs.google.com/document/d/{doc_id}/export?format=docx"
    return url

def fetch_and_extract_text(sentence_url):
    sentence_url = convert_google_docs_url(sentence_url)
    filename = os.path.basename(sentence_url).split("?")[0].split("#")[0].lower()
    file_types = [".pdf", ".doc", ".docx", ".txt"]
    for ext in file_types:
        if filename.endswith(ext) or "export?format=" in sentence_url:
            type_file = ext.replace('.', '') if ext in filename else "docx"
            text, sentences, status = fetch_other_type_file(sentence_url, type_file)
            if status == "Thành công":
                return text, "Thành công"
            else:
                return "", status
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

def normalize_text(text):
    text = text.lower()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def check_plagiarism(sentence, extracted_text):
    sentence_clean = normalize_text(sentence)
    extracted_text_clean = normalize_text(extracted_text)
    return sentence_clean in extracted_text_clean

if __name__ == "__main__":
    with open("result.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    updated_data = []
    processed_sentences = set()
    for entry in data:
        sentence = entry["sentence"]
        if sentence not in processed_sentences:
            processed_sentences.add(sentence)
            url_list = get_url_list(sentence)
            updated_results = []
            for result in url_list:
                text, status = fetch_and_extract_text(result["link"])
                print(f"Processing URL: {result['link']}")
                print(f"Status: {status}")
                has_plagiarism = check_plagiarism(sentence, text) if status == "Thành công" else False
                result["has_plagiarism"] = has_plagiarism
                if has_plagiarism:
                    print(f"⚠️ Câu: \"{sentence}\" xuất hiện trong URL: {result['link']}")
                updated_results.append(result)
            updated_data.append({
                "sentence": sentence,
                "results": updated_results
            })
    with open("result.json", "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)
    print("Đã cập nhật result.json với trạng thái đạo văn")


#-------------------TEST PDF-------------------
# if __name__ == "__main__":
#     sentence = "Ngay từ nhỏ, chúng ta đã có khái niệm về tiền bạc."
#     url = "https://bugs.python.org/file47781/Tutorial_EDIT.pdf"

#     text, status = fetch_and_extract_text(url)
#     print("== KẾT QUẢ KIỂM TRA PDF ==")
#     print("Trạng thái tải:", status)

#     if status == "Thành công":
#         has_plagiarism = check_plagiarism(sentence, text)
#         result_entry = {
#             "sentence": sentence,
#             "results": [
#                 {
#                     "title": "PDF Document",
#                     "link": url,
#                     "snippet": text[:150] + "...",
#                     "has_plagiarism": has_plagiarism
#                 }
#             ]
#         }
#         print(json.dumps(result_entry, ensure_ascii=False, indent=4))
#     else:
#         print("Không thể tải hoặc đọc file PDF. Lỗi:", status)


#-------------------TEST DOC-------------------
# if __name__ == "__main__":
#     sentence = "haha"
#     url = "https://docs.google.com/document/d/1v38d9dJpucOsGYBJ8_IlKcX-5SMWoW7dv6aVO4T3sGo/preview?hgd=1&tab=t.0"

#     text, status = fetch_and_extract_text(url)
#     print("== KẾT QUẢ KIỂM TRA DOCX ==")
#     print("Trạng thái tải:", status)

#     if status == "Thành công":
#         has_plagiarism = check_plagiarism(sentence, text)
#         result_entry = {
#             "sentence": sentence,
#             "results": [
#                 {
#                     "title": "Google Docs Document",
#                     "link": url,
#                     "snippet": text[:150] + "...",
#                     "has_plagiarism": has_plagiarism
#                 }
#             ]
#         }
#         print(json.dumps(result_entry, ensure_ascii=False, indent=4))
#     else:
#         print("Không thể tải hoặc đọc file DOCX. Lỗi:", status)
