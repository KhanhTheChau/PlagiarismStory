import requests
import html
import itertools
from typing import List, Tuple, Dict

class PlagiarismChecker:
    """
    Kiểm tra đạo văn theo từng dòng, giữ format gốc.
    Nếu API_KEYS hoặc CX_IDS không được cung cấp thì chuyển sang chế độ mock (không gọi API).
    """
    def __init__(self, api_keys: List[str], cx_ids: List[str]):
        self.api_keys = api_keys or []
        self.cx_ids = cx_ids or []
        self.has_api = bool(self.api_keys and self.cx_ids)
        if self.has_api:
            self._key_iter = itertools.cycle(self.api_keys)
            self._cx_iter = itertools.cycle(self.cx_ids)
            self.api_url = "https://www.googleapis.com/customsearch/v1"
        else:
            self._key_iter = None
            self._cx_iter = None

    def _get_next_keypair(self) -> Tuple[str, str]:
        if not self.has_api:
            return None, None
        return next(self._key_iter), next(self._cx_iter)

    def check_line(self, line: str) -> Tuple[bool, List[str]]:
        """Kiểm tra 1 dòng; trả về (is_plagiarized, [sources])."""
        stripped = line.strip()
        # Bỏ qua tiêu đề quá ngắn
        if len(stripped) < 20:
            return False, []

        # Nếu không có API thì trả False (hoặc bạn có thể mock bằng cách random)
        if not self.has_api:
            return False, []

        key, cx = self._get_next_keypair()
        params = {"key": key, "cx": cx, "q": f'"{stripped}"'}
        try:
            resp = requests.get(self.api_url, params=params, timeout=10)
            data = resp.json()
            items = data.get("items", [])
            if items:
                sources = [it.get("link") for it in items[:3] if it.get("link")]
                return True, sources
            return False, []
        except Exception as e:
            # Khi lỗi gọi API, tránh crash — coi là không tìm thấy
            print(f"[PlagiarismChecker] Lỗi khi gọi API: {e}")
            return False, []

    def check_text(self, full_text: str, lines: List[str], limit: int = 30) -> Tuple[float, List[Dict]]:
        """
        Kiểm tra danh sách lines. Trả về (percent_plagiarized, details)
        details: [{"line": line_text, "plagiarized": bool, "sources": [...]}...]
        """
        total = min(len(lines), limit)
        details = []
        plag_count = 0
        for i, line in enumerate(lines[:limit], 1):
            is_plag, sources = self.check_line(line)
            details.append({"line": line.strip(), "plagiarized": is_plag, "sources": sources})
            if is_plag:
                plag_count += 1
        percent = (plag_count / total * 100) if total else 0.0
        return round(percent, 2), details

    def highlight_text(self, original_text: str, details: List[Dict]) -> str:
        """
        Tô những dòng bị nghi đạo văn nhưng vẫn giữ nguyên format.
        Trả về HTML-safe string; giữ nguyên xuống dòng bằng <br>.
        Logic: so khớp dòng chi tiết với dòng đã extract (so sánh .strip()).
        """
        # build map: stripped line -> list of details (in order)
        mapping = {}
        for d in details:
            key = d["line"].strip()
            mapping.setdefault(key, []).append(d)

        html_lines = []
        for ln in original_text.splitlines():
            stripped = ln.strip()
            if stripped == "":
                html_lines.append("")  # giữ dòng trống
                continue

            entry_list = mapping.get(stripped)
            if entry_list:
                # lấy entry chưa dùng (pop 0)
                entry = entry_list.pop(0)
                if entry["plagiarized"]:
                    escaped = html.escape(ln)
                    sources = " | ".join(html.escape(s) for s in entry.get("sources", []))
                    # lưu sources trong data-sources (escape)
                    html_lines.append(f'<mark class="plag" data-sources="{sources}">{escaped}</mark>')
                    continue

            # nếu không bị đánh dấu plagiarized: escape bình thường
            html_lines.append(html.escape(ln))

        # nối lại với <br> để preserve newlines
        return "<br>".join(html_lines)
