"""
Web crawler: fetches publicly available content from configured sources.
Paywall-gated articles are skipped; only free text is extracted.
"""

import time
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AI-Articulation-Bot/1.0; "
        "+https://github.com/sharmilnk/ai-articulation)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

REQUEST_TIMEOUT = 15
CRAWL_DELAY = 1.5  # seconds between requests to avoid rate limiting
MAX_CONTENT_CHARS = 8000  # per page to keep API costs reasonable


@dataclass
class ScrapedPage:
    url: str
    source_name: str
    category: str
    title: str = ""
    content: str = ""
    links: list = field(default_factory=list)
    error: Optional[str] = None


def _get(url: str) -> Optional[requests.Response]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _clean_text(soup: BeautifulSoup, remove_tags: list = None) -> str:
    remove_tags = remove_tags or ["script", "style", "nav", "footer", "header",
                                  "aside", "form", "noscript", "svg", "img"]
    for tag in soup(remove_tags):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # collapse whitespace
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _is_paywalled(soup: BeautifulSoup) -> bool:
    indicators = [
        "subscribe to read", "subscribe to continue", "members only",
        "unlock this post", "this post is for paid subscribers",
        "become a member to read", "paywall",
    ]
    page_text = soup.get_text().lower()
    return any(ind in page_text for ind in indicators)


def _extract_substack(soup: BeautifulSoup) -> tuple[str, str, list]:
    """Extract content from Substack pages."""
    title = ""
    if h := soup.find("h1"):
        title = h.get_text(strip=True)

    # Free post body
    body = soup.find("div", class_=re.compile(r"body|post-content|available-content", re.I))
    content = _clean_text(body) if body else _clean_text(soup)

    # Collect article links from archive/home
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/p/" in href and href not in links:
            links.append(href if href.startswith("http") else "https://spillthegptea.substack.com" + href)

    return title, content[:MAX_CONTENT_CHARS], links[:10]


def _extract_lenny(soup: BeautifulSoup) -> tuple[str, str, list]:
    """Extract free preview content from Lenny's Newsletter."""
    title = ""
    if h := soup.find("h1"):
        title = h.get_text(strip=True)

    # Grab post preview / free portion only
    content_div = soup.find("div", class_=re.compile(r"post-content|body|free", re.I))
    raw = _clean_text(content_div) if content_div else _clean_text(soup)

    # Collect article titles from archive listing
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/p/" in href and href not in links:
            links.append(href if href.startswith("http") else "https://www.lennysnewsletter.com" + href)

    return title, raw[:MAX_CONTENT_CHARS], links[:10]


def _extract_generic(soup: BeautifulSoup, base_url: str = "") -> tuple[str, str, list]:
    """Generic extractor for standard web pages."""
    title = ""
    for tag in ["h1", "title"]:
        if elem := soup.find(tag):
            title = elem.get_text(strip=True)
            break

    # Prefer main/article content blocks
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"content|main|post|article|body", re.I))
        or soup.find("body")
    )
    content = _clean_text(main) if main else _clean_text(soup)

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and base_url and base_url.split("//")[1].split("/")[0] in href:
            links.append(href)
        elif href.startswith("/") and base_url:
            links.append(base_url.rstrip("/") + href)

    return title, content[:MAX_CONTENT_CHARS], list(set(links))[:5]


def scrape_source(source: dict) -> ScrapedPage:
    url = source["url"]
    name = source["name"]
    category = source["category"]

    logger.info("Crawling: %s", url)
    resp = _get(url)

    if resp is None:
        return ScrapedPage(url=url, source_name=name, category=category,
                           error="Request failed")

    soup = BeautifulSoup(resp.text, "html.parser")

    if _is_paywalled(soup):
        logger.info("Paywalled content detected at %s — extracting preview only", url)

    # Route to appropriate extractor
    if "substack.com" in url:
        title, content, links = _extract_substack(soup)
    elif "lennysnewsletter.com" in url:
        title, content, links = _extract_lenny(soup)
    else:
        domain = url.split("//")[1].split("/")[0]
        base = f"{url.split('//')[0]}//{domain}"
        title, content, links = _extract_generic(soup, base)

    return ScrapedPage(
        url=url,
        source_name=name,
        category=category,
        title=title,
        content=content,
        links=links,
    )


def crawl_all(sources: list) -> list[ScrapedPage]:
    """Crawl all sources with rate limiting. Returns list of ScrapedPage."""
    pages = []
    for i, source in enumerate(sources):
        page = scrape_source(source)
        pages.append(page)
        if page.error:
            logger.warning("Skipping %s — %s", source["name"], page.error)
        else:
            logger.info(
                "  ✓ %s — %d chars extracted",
                source["name"],
                len(page.content),
            )
        if i < len(sources) - 1:
            time.sleep(CRAWL_DELAY)
    return pages
