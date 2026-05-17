"""Douban book page parsers using lxml.html and Scrapy selectors."""

import re
from collections import Counter
from lxml import html as lxml_html


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _strip(v):
    """Strip whitespace; return None if empty after stripping."""
    if v is None:
        return None
    s = v.strip()
    return s if s else None


def _css_one(tree, selector, default=None):
    sel = tree.cssselect(selector)
    return sel[0] if sel else default


def _css_text(tree, selector, default=None):
    sel = tree.cssselect(selector)
    if not sel:
        return default
    return _strip(sel[0].text_content())


def _extract_digits(value, default=0):
    if not value:
        return default
    digits = re.sub(r"\D", "", value)
    return int(digits) if digits else default


def _extract_star_from_class(value):
    if not value:
        return None
    match = re.search(r"allstar(\d{2})", value)
    if not match:
        return None
    return int(match.group(1)) // 10


def _clean_author_prefix(value):
    """Remove leading colon-space prefix from parsed info-table values.

    Some Douban info-table entries have a trailing separator (": " / "：")
    in the label's tail text that ends up prepended to the value.
    """
    if value is None:
        return None
    cleaned = re.sub(r'^[：:]\s*', '', value.strip())
    return cleaned.strip() or None


# ---------------------------------------------------------------------------
# 1. extract_subject_id
# ---------------------------------------------------------------------------

def extract_subject_id(url):
    """Extract numeric subject ID from a Douban URL.

    >>> extract_subject_id('https://book.douban.com/subject/1000005/')
    '1000005'
    >>> extract_subject_id('/subject/1234567/')
    '1234567'
    >>> extract_subject_id('')
    """
    if not url:
        return None
    m = re.search(r'/subject/(\d+)', url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# 2. parse_title
# ---------------------------------------------------------------------------

def parse_title(tree):
    """Return the book title from a detail-page lxml tree."""
    # Primary selector
    el = _css_one(tree, '#wrapper h1 span[property="v:itemreviewed"]')
    if el is not None:
        return _strip(el.text_content())
    # Fallback: any h1 span
    el = _css_one(tree, '#wrapper h1 span')
    if el is not None:
        return _strip(el.text_content())
    return None


# ---------------------------------------------------------------------------
# 3. parse_rating_score
# ---------------------------------------------------------------------------

def parse_rating_score(tree):
    """Return the average rating (float) or None when missing / 0."""
    text = _css_text(tree, 'strong.ll.rating_num[property="v:average"]')
    if not text:
        return None
    try:
        val = float(text)
    except (ValueError, TypeError):
        return None
    return val if val > 0 else None


# ---------------------------------------------------------------------------
# 4. parse_votes
# ---------------------------------------------------------------------------

def parse_votes(tree):
    """Return the number of rating votes (int) or 0."""
    el = _css_one(tree, 'span[property="v:votes"]')
    if el is not None:
        text = _strip(el.text_content())
        if text:
            digits = re.sub(r'\D', '', text)
            if digits:
                n = int(digits)
                return n if n > 0 else 0
    # Fallback
    el = _css_one(tree, 'a.rating_people span')
    if el is not None:
        text = _strip(el.text_content())
        if text:
            digits = re.sub(r'\D', '', text)
            if digits:
                n = int(digits)
                return n if n > 0 else 0
    return 0


# ---------------------------------------------------------------------------
# 5. parse_info_table  (reduced to 4 fields)
# ---------------------------------------------------------------------------

_INFO_LABEL_MAP = {
    '作者': 'authors',
    '出版社': 'publisher',
    '出版年': 'pubdate',
    '定价': 'price',
}


def _walk_info_siblings(span):
    """Collect text from siblings after *span* until next span.pl or br."""
    parts = []
    elem = span.getnext()
    while elem is not None:
        tag = getattr(elem, 'tag', None)
        if tag == 'span' and 'pl' in (elem.get('class') or ''):
            break
        if tag == 'br':
            break
        if tag == 'a':
            parts.append((elem.text_content() or '').strip())
        else:
            t = (elem.text or '') if hasattr(elem, 'text') else ''
            s = (elem.tail or '') if hasattr(elem, 'tail') else ''
            if hasattr(elem, 'text_content'):
                t = elem.text_content() or ''
            parts.append(t)
            if s.strip():
                parts.append(s.strip())
        elem = elem.getnext()
    return ' '.join(p for p in parts if p)


def parse_info_table(tree):
    """Return a dict with reduced info fields: authors, publisher, pubdate, price.

    Also cleans the leading ': ' prefix that sometimes appears in author values.
    """
    result: dict = {
        'authors': None, 'publisher': None,
        'pubdate': None, 'price': None,
    }

    info = _css_one(tree, '#info')
    if info is None:
        return result

    sps = info.cssselect('span.pl')
    for sp in sps:
        label_raw = _strip(sp.text_content())
        if not label_raw:
            continue
        label = label_raw.rstrip(':').strip()
        key = _INFO_LABEL_MAP.get(label)
        if key is None:
            continue

        # Text immediately after the span (tail)
        tail = (sp.tail or '').strip()
        # Text from following siblings
        sibling_text = _walk_info_siblings(sp)

        value = _strip((tail + ' ' + sibling_text)) if tail or sibling_text else None
        if not value:
            continue

        # Clean leading colon-space prefix from author names
        if key == 'authors':
            value = _clean_author_prefix(value)

        result[key] = value

    return result


# ---------------------------------------------------------------------------
# 6. parse_list_items
# ---------------------------------------------------------------------------

def parse_list_items(response):
    """Parse a list page; return list of {subject_id, title, detail_url, rating_avg}.

    Supports current live Douban layout (``tr.item`` / ``div.pl2 a[title]``)
    and falls back to the older ``li.subject-item`` structure used in fixtures.
    """
    items = []
    tree = lxml_html.fromstring(response.text)

    # -- Row detection: live (tr.item) first, then legacy (li.subject-item) --
    rows = tree.cssselect('tr.item')
    if not rows:
        rows = tree.cssselect('li.subject-item')

    for row in rows:
        # -- Title / detail_url -------------------------------------------------
        # Try selectors from newest DOM to oldest
        a_el = (
            row.cssselect('div.pl2 a[title]')
            or row.cssselect('td.pl2 a[title]')
            or row.cssselect('.info h2 a')
            or row.cssselect('.info a[title]')
        )
        if not a_el:
            continue

        a = a_el[0]
        detail_url = _strip(a.get('href'))
        title = _strip(a.get('title')) or _strip(a.text_content())

        if not detail_url:
            continue

        subject_id = extract_subject_id(detail_url)

        # -- Rating -------------------------------------------------------------
        rating_el = row.cssselect('span.rating_nums')
        rating_avg = None
        if rating_el:
            try:
                r = float(rating_el[0].text_content().strip())
                if r > 0:
                    rating_avg = r
            except (ValueError, TypeError):
                pass

        items.append({
            'subject_id': subject_id,
            'title': title or None,
            'detail_url': detail_url,
            'rating_avg': rating_avg,
        })

    return items


# ---------------------------------------------------------------------------
# 7. parse_detail  (reduced to 8 fields)
# ---------------------------------------------------------------------------

def parse_detail(response):
    """Parse a book detail page into an 8-field dict.

    Parameters
    ----------
    response : scrapy.http.Response
        The HTTP response from the detail page.

    Returns
    -------
    dict with keys:
        url, title, authors, publisher, pubdate, price, rating, votes
    """
    tree = lxml_html.fromstring(response.text)
    url = response.url

    # Title
    title = parse_title(tree)

    # Info table (authors, publisher, pubdate, price)
    info = parse_info_table(tree)
    authors = info.get('authors')
    publisher = info.get('publisher')
    pubdate = info.get('pubdate')
    price = info.get('price')

    # Rating
    rating = parse_rating_score(tree)
    votes = parse_votes(tree)  # int, 0 if missing

    # 0 ratings → rating None, votes 0
    if rating is None:
        votes = 0
    if votes == 0 and rating:
        rating = None

    return {
        'url': url,
        'title': title,
        'authors': authors,
        'publisher': publisher,
        'pubdate': pubdate,
        'price': price,
        'rating': rating,
        'votes': votes,
    }


def parse_review_entries(response, book_url, limit=20):
    tree = lxml_html.fromstring(response.text)
    entries = []
    rows = tree.cssselect(".review-list .review-item")
    for row in rows[:limit]:
        review_url = _css_one(row, "h2 a").get("href") if _css_one(row, "h2 a") is not None else None
        rating_el = _css_one(row, ".main-hd .main-title-rating")
        useful_text = _css_text(row, ".action .action-btn.up", default="0")
        useless_text = _css_text(row, ".action .action-btn.down", default="0")
        useful_count = _extract_digits(useful_text)
        useless_count = _extract_digits(useless_text)
        total_votes = useful_count + useless_count
        entries.append({
            "book_url": book_url,
            "review_url": _strip(review_url),
            "title": _css_text(row, "h2 a"),
            "content": _css_text(row, ".short-content"),
            "rating": _extract_star_from_class(rating_el.get("class", "") if rating_el is not None else None),
            "useful_count": useful_count,
            "useless_count": useless_count,
            "useful_ratio": round(useful_count / total_votes, 4) if total_votes else None,
            "replies_count": _extract_digits(_css_text(row, ".reply-btn", default="0")),
            "reviewer_name": _css_text(row, ".main-hd .name"),
            "reviewer_url": _strip(_css_one(row, ".main-hd .name").get("href")) if _css_one(row, ".main-hd .name") is not None else None,
            "published_at": _css_text(row, ".main-hd .main-meta"),
        })

    next_href = _css_one(tree, ".paginator .next a")
    next_url = None
    if next_href is not None:
        next_url = response.urljoin(next_href.get("href"))
    return entries, next_url


def parse_official_rating_distribution(response):
    tree = lxml_html.fromstring(response.text)
    values = [_strip(node.text_content()) for node in tree.cssselect("#interest_sectl .rating_per")]
    cleaned = []
    for value in values[:5]:
        if value is None:
            cleaned.append(0.0)
            continue
        try:
            cleaned.append(float(value.replace("%", "")))
        except ValueError:
            cleaned.append(0.0)
    while len(cleaned) < 5:
        cleaned.append(0.0)
    return {
        "star_5_pct": cleaned[0],
        "star_4_pct": cleaned[1],
        "star_3_pct": cleaned[2],
        "star_2_pct": cleaned[3],
        "star_1_pct": cleaned[4],
    }


def parse_reading_state(response):
    tree = lxml_html.fromstring(response.text)
    collector = _css_one(tree, "#collector")
    texts = collector.text_content().splitlines() if collector is not None else []
    payload = {"want_to_read": 0, "reading": 0, "read": 0}
    for text in texts:
        stripped = _strip(text)
        if not stripped:
            continue
        if "想读" in stripped:
            payload["want_to_read"] = _extract_digits(stripped)
        elif "在读" in stripped:
            payload["reading"] = _extract_digits(stripped)
        elif "读过" in stripped:
            payload["read"] = _extract_digits(stripped)
    return payload


def build_derived_rating_distribution(reviews):
    counter = Counter()
    for review in reviews:
        rating = review.get("rating")
        if rating in (1, 2, 3, 4, 5):
            counter[rating] += 1
    sample_size = sum(counter.values())

    def pct(star):
        if sample_size == 0:
            return 0.0
        return round(counter[star] * 100.0 / sample_size, 4)

    return {
        "sample_size": sample_size,
        "star_5_count": counter[5],
        "star_4_count": counter[4],
        "star_3_count": counter[3],
        "star_2_count": counter[2],
        "star_1_count": counter[1],
        "star_5_pct": pct(5),
        "star_4_pct": pct(4),
        "star_3_pct": pct(3),
        "star_2_pct": pct(2),
        "star_1_pct": pct(1),
    }


def parse_user_profile(response):
    tree = lxml_html.fromstring(response.text)
    links = tree.cssselect(".rev-link a")
    following = 0
    followers = 0
    for link in links:
        text = _strip(link.text_content()) or ""
        if "关注" in text and "被关注" not in text:
            following = _extract_digits(text)
        elif "被关注" in text:
            followers = _extract_digits(text)
    return {
        "reviewer_url": response.url,
        "display_name": _css_text(tree, ".user-info h1"),
        "following_count": following,
        "followers_count": followers,
    }
