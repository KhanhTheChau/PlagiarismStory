from googleapiclient.discovery import build

# Nhập key & cx
API_KEY = "xxxxxxxxxxxxxxxxxxxxxxx"
CX = "xxxxxxxxxxxxxxxxxxxxxxx"

def google_search(query, num=5):
    service = build("customsearch", "v1", developerKey=API_KEY)
    res = service.cse().list(q=query, cx=CX, num=num).execute()
    results = []
    for item in res.get("items", []):
        results.append({
            "title": item["title"],
            "link": item["link"],
            "snippet": item.get("snippet", "")
        })
    return results

# Ví dụ: tìm bài liên quan
query = "Đại học Cần Thơ có vai trò quan trọng trong đào tạo đa ngành, đa lĩnh vực, cung cấp nguồn nhân lực cho Thành phố Cần Thơ cũng như vùng Đồng bằng sông Cửu Long"
results = google_search(query)

for r in results:
    print(r["title"])
    print(r["link"])
    print(r["snippet"])
    print("─" * 50)
