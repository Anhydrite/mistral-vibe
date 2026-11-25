"""Web tools for the Vibe agent: fetch a page, search the web.

The slim agent ships both, and they are what makes research possible without a plugin or
an MCP server. They run in the app server as provided tools, so the harness
needs no change. `websearch` asks DuckDuckGo's HTML endpoint, which needs no
key; an Exa key, when set, gives better ranking and is used first.
"""

from __future__ import annotations

import html
import os
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field

WEBFETCH_TOOL_NAME = "webfetch"
WEBSEARCH_TOOL_NAME = "websearch"

MAX_BYTES = 5_000_000
MAX_CONTENT_CHARS = 200_000
USER_AGENT = "vibe/1.0 (+https://github.com/Anhydrite/mistral-vibe)"

WEBFETCH_DESCRIPTION = """\
Fetch a URL and return its contents. markdown (the default) strips the page to
readable text, text keeps the raw body, html keeps the markup. Caps the body at
5 MB. Use it to read a documentation page or a raw file; prefer `bash`+`curl`
only when you need headers or a non-text body."""

WEBSEARCH_DESCRIPTION = """\
Search the web and return result titles, URLs and snippets. Use it for current
events, documentation, APIs or anything not in local files, then `webfetch` the
promise that looks relevant. Prefer several specific queries to one broad one."""


class WebfetchArgs(BaseModel):
    url: str = Field(description="Absolute http(s) URL")
    format: Literal["markdown", "text", "html"] = "markdown"
    timeout: int = Field(default=30, ge=1, le=120, description="Seconds")


class WebfetchResult(BaseModel):
    url: str
    status: int | None = None
    content: str = ""
    truncated: bool = False
    error: str | None = None


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str = ""


class WebsearchArgs(BaseModel):
    query: str
    num_results: int = Field(default=8, ge=1, le=20)


class WebsearchResult(BaseModel):
    query: str
    results: list[SearchHit] = Field(default_factory=list)
    error: str | None = None


_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_SPACE = re.compile(r"[ \t\r\f\v]+")
_LINES = re.compile(r"\n{3,}")
_DDG_LINK = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL
)
_DDG_SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
_ENCODED_URL = re.compile(r"uddg=([^&\"]+)")


def _strip(page: str) -> str:
    page = _SCRIPT.sub(" ", page)
    page = _TAG.sub(" ", page)
    page = html.unescape(page)
    page = _SPACE.sub(" ", page)
    page = "\n".join(line.strip() for line in page.splitlines())
    return _LINES.sub("\n\n", page).strip()


def _html_to_markdown(page: str) -> str:
    """Keep headings, links and list items, drop the rest of the markup."""
    page = _SCRIPT.sub(" ", page)
    page = re.sub(
        r"<h([1-6])[^>]*>(.*?)</h\1>",
        lambda m: "\n\n" + "#" * int(m.group(1)) + " " + _strip(m.group(2)) + "\n",
        page,
        flags=re.IGNORECASE | re.DOTALL,
    )
    page = re.sub(
        r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: f"[{_strip(m.group(2))}]({html.unescape(m.group(1))})",
        page,
        flags=re.IGNORECASE | re.DOTALL,
    )
    page = re.sub(r"<li[^>]*>", "\n- ", page, flags=re.IGNORECASE)
    page = re.sub(r"</p>|<br\s*/?>", "\n", page, flags=re.IGNORECASE)
    page = _TAG.sub(" ", page)
    page = html.unescape(page)
    page = _SPACE.sub(" ", page)
    page = "\n".join(line.strip() for line in page.splitlines())
    return _LINES.sub("\n\n", page).strip()


def run_webfetch(args: WebfetchArgs) -> WebfetchResult:
    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        return WebfetchResult(url=url, error="url must start with http:// or https://")
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=args.timeout,
            headers={"user-agent": USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            raw = response.content[:MAX_BYTES]
            text = raw.decode(response.encoding or "utf-8", "replace")
    except Exception as error:  # the model needs the reason, not a traceback
        return WebfetchResult(url=url, error=f"{type(error).__name__}: {error}")
    if args.format == "html":
        content = text
    elif args.format == "text":
        content = _strip(text) if "<" in text[:2000] else text
    else:
        content = _html_to_markdown(text) if "<" in text[:2000] else text
    truncated = len(content) > MAX_CONTENT_CHARS
    return WebfetchResult(
        url=url,
        status=response.status_code,
        content=content[:MAX_CONTENT_CHARS],
        truncated=truncated,
    )


def _exa_search(query: str, count: int, key: str) -> list[SearchHit]:
    with httpx.Client(timeout=20, headers={"x-api-key": key}) as client:
        response = client.post(
            "https://api.exa.ai/search",
            json={"query": query, "numResults": count, "contents": {"text": {"maxCharacters": 400}}},
        )
        response.raise_for_status()
        payload = response.json()
    return [
        SearchHit(
            title=hit.get("title") or hit.get("url", ""),
            url=hit.get("url", ""),
            snippet=(hit.get("text") or "")[:400],
        )
        for hit in payload.get("results", [])[:count]
    ]


def _duckduckgo_search(query: str, count: int) -> list[SearchHit]:
    with httpx.Client(
        follow_redirects=True,
        timeout=20,
        headers={"user-agent": USER_AGENT},
    ) as client:
        response = client.post("https://html.duckduckgo.com/html/", data={"q": query})
        response.raise_for_status()
        page = response.text
    links = _DDG_LINK.findall(page)
    snippets = [_strip(fragment) for fragment in _DDG_SNIPPET.findall(page)]
    hits: list[SearchHit] = []
    for index, (href, title_html) in enumerate(links):
        encoded = _ENCODED_URL.search(href)
        url = html.unescape(encoded.group(1)) if encoded else html.unescape(href)
        if not url.startswith("http"):
            continue
        hits.append(
            SearchHit(
                title=_strip(title_html),
                url=url,
                snippet=snippets[index] if index < len(snippets) else "",
            )
        )
        if len(hits) >= count:
            break
    return hits


def run_websearch(args: WebsearchArgs) -> WebsearchResult:
    query = args.query.strip()
    if not query:
        return WebsearchResult(query=query, error="query must not be empty")
    key = os.environ.get("EXA_API_KEY", "").strip()
    try:
        hits = _exa_search(query, args.num_results, key) if key else _duckduckgo_search(
            query, args.num_results
        )
    except Exception as error:
        return WebsearchResult(query=query, error=f"{type(error).__name__}: {error}")
    if not hits:
        return WebsearchResult(query=query, error="no results")
    return WebsearchResult(query=query, results=hits)
