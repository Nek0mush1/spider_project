"""Douban book page parsers using lxml.html and Scrapy selectors."""

import re
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
