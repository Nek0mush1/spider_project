import re


def parse_price(text):
    if not text:
        return None
    nums = re.findall(r"\d+\.?\d*", str(text))
    return float(nums[0]) if nums else None


def parse_rating_from_style(style):
    if not style:
        return None
    m = re.search(r"width\s*:\s*([\d.]+)%", str(style), re.IGNORECASE)
    return float(m.group(1)) if m else None


def parse_review_count(text):
    if not text:
        return None
    m = re.search(r"(\d+)", str(text))
    return int(m.group(1)) if m else None


def parse_detail_rating(html):
    m = re.search(r'<span class="star"[^>]*style="[^"]*width:\s*([\d.]+)%', html)
    rating = float(m.group(1)) if m else None
    m = re.search(r'id="comm_num_down"[^>]*>(\d+)', html)
    people = int(m.group(1)) if m else None
    return rating, people
