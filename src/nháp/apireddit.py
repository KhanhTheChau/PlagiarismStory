import requests
import time
from urllib.parse import quote

# Cấu hình thông tin ứng dụng
CLIENT_ID = "F0Ksw7l3IJJXcFDbQBwRjA"
SECRET_KEY = "FMP1lsC_yJYRfVr3FmV_BuyBpzzzWA"
USERNAME = "Federal_Piano942"
PASSWORD = "Nltt@0966771422"
USER_AGENT = f"python:myredditapp:0.0.1 (by /u/{USERNAME})"

# Lấy access token
auth = requests.auth.HTTPBasicAuth(CLIENT_ID, SECRET_KEY)
data = {
    'grant_type': 'password',
    'username': USERNAME,
    'password': PASSWORD
}
headers = {'User-Agent': USER_AGENT}

try:
    # print("Đang gửi yêu cầu lấy access token...")
    res = requests.post(
        'https://www.reddit.com/api/v1/access_token',
        auth=auth,
        data=data,
        headers=headers
    )
    # print("Mã trạng thái:", res.status_code)
    # print("Nội dung phản hồi:", res.text)
    
    if res.status_code == 200:
        token_data = res.json()
        access_token = token_data.get('access_token')
        if not access_token:
            print("Lỗi: Không tìm thấy access_token trong phản hồi.")
            exit(1)
        # print("Access Token:", access_token)
    else:
        print(f"Lỗi {res.status_code}: Không thể lấy token. Chi tiết:", res.text)
        exit(1)
except requests.exceptions.JSONDecodeError:
    print("Lỗi: Phản hồi không phải JSON hợp lệ. Nội dung:", res.text)
    exit(1)
except Exception as e:
    print("Lỗi khác:", str(e))
    exit(1)

# Đọc query từ file output.txt
try:
    with open("output.txt", "r", encoding="utf-8") as f:
        QUERY = f.read().strip()
    # print(f"\nQuery từ file output.txt ({len(QUERY)} ký tự): {QUERY}")
except FileNotFoundError:
    print("Lỗi: Không tìm thấy file output.txt")
    exit(1)
except Exception as e:
    print(f"Lỗi khi đọc file: {str(e)}")
    exit(1)

# Chia nhỏ query thành các đoạn 512 ký tự
MAX_QUERY_LENGTH = 512
queries = []
if len(QUERY) > MAX_QUERY_LENGTH:
    # print(f"Query vượt {MAX_QUERY_LENGTH} ký tự, chia nhỏ thành các đoạn...")
    start = 0
    while start < len(QUERY):
        end = min(start + MAX_QUERY_LENGTH, len(QUERY))
        while end > start and QUERY[end-1] not in (' ', '\n', '\t') and end < len(QUERY):
            end -= 1
        if end == start:  
            end = start + MAX_QUERY_LENGTH
        queries.append(QUERY[start:end].strip())
        start = end
else:
    queries = [QUERY]
# print("Các query sẽ tìm kiếm:", [q[:50] + "..." if len(q) > 50 else q for q in queries])


headers = {**headers, **{'Authorization': f"bearer {access_token}"}}

results = []
seen_links = set()  # Loại bỏ trùng lặp

for q in queries:
    encoded_query = quote(q)
    search_url = f"https://oauth.reddit.com/search?q={encoded_query}&limit=5&sort=relevance&type=link"
    
    try:
        response = requests.get(search_url, headers=headers)
        # print(f"\nMã trạng thái (tìm kiếm với query '{q[:50]}...'):", response.status_code)
        
        if response.status_code == 200:
            posts = response.json().get('data', {}).get('children', [])
            for item in posts:
                post_data = item.get('data', {})
                link = post_data.get("url", "")
                if link not in seen_links:
                    seen_links.add(link)
                    results.append({
                        "title": post_data.get("title", ""),
                        "link": link,
                        "snippet": post_data.get("selftext", "")[:200]
                    })
        else:
            print(f"Lỗi {response.status_code}: Không thể tìm kiếm. Chi tiết:", response.text)
    except requests.exceptions.JSONDecodeError:
        print("Lỗi: Phản hồi không phải JSON hợp lệ. Nội dung:", response.text)
    except Exception as e:
        print("Lỗi khác:", str(e))
    
    time.sleep(1)

# In kết quả
print("\nKết quả tìm kiếm bài viết:")
if results:
    for result in results:
        print(f"- Title: {result['title']}")
        print(f"  Link: {result['link']}")
        print(f"  Snippet: {result['snippet']}")
        print()
else:
    print("Không tìm thấy bài viết nào.")
print("\nDanh sách results:", results)