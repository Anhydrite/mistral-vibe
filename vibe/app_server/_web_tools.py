"""Web tools for the Vibe agent: fetch a page, search the web.

The PicoVibe agent ships both, and they are what makes research possible without a plugin or
an MCP server. They run in the app server as provided tools, so the harness
needs no change. `websearch` needs no key: it asks Exa first when a key is set,
then Bing, then DuckDuckGo's HTML endpoint, and stops at the first engine that
returns parseable and *relevant* results. Falling through matters, because
either scraper answers an empty page under rate limiting instead of failing
loudly, and because a generic query makes them return dictionary pages.

`webfetch` returns a bounded window rather than the whole page: `pattern` keeps
only the matching lines, `offset`/`max_chars` page through the rest with
`next_offset`, so a long guide costs one tool result instead of spilling into a
side file the model has to grep with `bash`. Boilerplate (nav, footer, aside,
forms) is dropped, and a page that renders client-side says so in `note`
instead of returning an empty body.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
import html
import os
import re
from typing import Literal
import unicodedata

import httpx2
from pydantic import BaseModel, Field

from vibe.utils.http import build_ssl_context, with_user_agent

WEBFETCH_TOOL_NAME = "webfetch"
WEBSEARCH_TOOL_NAME = "websearch"

MAX_BYTES = 5_000_000
MAX_CONTENT_CHARS = 200_000
# Below the harness' tool-result cap on purpose: one page view should not spill
# into a side file, and `next_offset` lets the model ask for the rest.
DEFAULT_CONTENT_CHARS = 12_000
# A page this small after extraction while the markup is large means the text is
# built by scripts, so say it instead of returning nothing.
MIN_TEXT_CHARS = 200
MIN_RENDERED_HTML_CHARS = 20_000
HEADERS = with_user_agent({"accept-language": "fr-FR,fr;q=0.9,en;q=0.8"}, backend=None)
SNIPPET_CHARS = 400

WEBFETCH_DESCRIPTION = """\
Fetch a URL and return its contents. markdown (the default) strips the page to
readable text, text keeps the raw body, html keeps the markup. Caps the body at
5 MB. Use it to read a documentation page or a raw file; prefer `bash`+`curl`
only when you need headers or a non-text body.

Long pages come back in a window of `max_chars` starting at `offset`; when
`truncated` is true, call again with `offset=next_offset` for the rest. Pass
`pattern` (a regular expression) to keep only the lines that match, which is
the cheapest way to read one section of a long page. A `note` explains an empty
or short result, for example a page that renders client-side."""

WEBSEARCH_DESCRIPTION = """\
Search the web and return result titles, URLs and snippets. Use it for current
events, documentation, APIs or anything not in local files, then `webfetch` the
promise that looks relevant. Prefer several specific queries to one broad one."""


class WebfetchArgs(BaseModel):
    url: str = Field(description="Absolute http(s) URL")
    format: Literal["markdown", "text", "html"] = "markdown"
    pattern: str | None = Field(
        default=None,
        description="Keep only the lines matching this regular expression (case-insensitive)",
    )
    offset: int = Field(
        default=0, ge=0, description="Character offset into the extracted content"
    )
    max_chars: int = Field(
        default=DEFAULT_CONTENT_CHARS,
        ge=200,
        le=MAX_CONTENT_CHARS,
        description="Characters to return from `offset`",
    )
    timeout: int = Field(default=30, ge=1, le=120, description="Seconds")


class WebfetchResult(BaseModel):
    url: str
    status: int | None = None
    content: str = ""
    truncated: bool = False
    next_offset: int | None = None
    note: str | None = None
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
    note: str | None = None
    error: str | None = None


_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
# Chrome that repeats on every page of a site and carries no answer.
_CHROME = re.compile(
    r"<(script|style|noscript|template|svg|nav|footer|aside|form)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_MAIN = re.compile(r"<main[^>]*>.*?</main>", re.DOTALL | re.IGNORECASE)
_ARTICLE = re.compile(r"<article[^>]*>.*?</article>", re.DOTALL | re.IGNORECASE)
_SPACE = re.compile(r"[ \t\r\f\v]+")
_LINES = re.compile(r"\n{3,}")
# DuckDuckGo: split the page on `result__a` so a result's link and its snippet
# stay in the same block. Two independent matches drift out of sync as soon as
# a result has no snippet.
_DDG_RESULT_MARKER = 'class="result__a"'
_DDG_LINK_SLICE = re.compile(r'href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
_DDG_SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
_ENCODED_URL = re.compile(r"uddg=([^&\"]+)")
# Bing wraps organic links in ck/a redirects carrying the target as base64 in `u=a1…`.
_BING_REDIRECT = re.compile(r"[?&]u=a1([A-Za-z0-9_\-=]+)")
# Bing: one <li class="b_algo"> per organic result.
_BING_BLOCK = re.compile(r'<li class="b_algo".*?</li>', re.DOTALL)
_BING_LINK = re.compile(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
_BING_SNIPPET = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL)


def _strip(page: str) -> str:
    page = _SCRIPT.sub(" ", page)
    page = _TAG.sub(" ", page)
    page = html.unescape(page)
    page = _SPACE.sub(" ", page)
    page = "\n".join(line.strip() for line in page.splitlines())
    return _LINES.sub("\n\n", page).strip()


def _content_region(page: str) -> str:
    """Narrow the page to its main text when that keeps most of the words.

    Index pages carry several articles and doc sites put navigation outside
    `<main>`, so this only wins when the narrowed region is still the bulk of it.
    """
    candidates = [page]
    main = _MAIN.search(page)
    if main is not None:
        candidates.append(main.group(0))
    else:
        articles = _ARTICLE.findall(page)
        if len(articles) == 1:
            candidates.append(articles[0])
    if len(candidates) == 1:
        return page
    region = candidates[-1]
    region_chars = len(_strip(region))
    return region if region_chars * 2 >= len(_strip(page)) else page


def _html_to_readable(page: str) -> str:
    return _html_to_markdown(_CHROME.sub(" ", _content_region(page)))


def _text_to_readable(page: str) -> str:
    return _strip(_CHROME.sub(" ", _content_region(page)))


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


def _looks_like_html(body: str) -> bool:
    return "<" in body[:2000]


def _matching_lines(content: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    return "\n".join(line for line in content.splitlines() if regex.search(line))


def run_webfetch(args: WebfetchArgs) -> WebfetchResult:
    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        return WebfetchResult(url=url, error="url must start with http:// or https://")
    if args.pattern is not None:
        try:
            re.compile(args.pattern, re.IGNORECASE)
        except re.error as error:
            return WebfetchResult(url=url, error=f"invalid pattern: {error}")
    try:
        with httpx2.Client(
            follow_redirects=True,
            timeout=args.timeout,
            headers=with_user_agent({}, backend=None),
            verify=build_ssl_context(),
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            raw = response.content[:MAX_BYTES]
            text = raw.decode(response.encoding or "utf-8", "replace")
    except Exception as error:  # the model needs the reason, not a traceback
        return WebfetchResult(url=url, error=f"{type(error).__name__}: {error}")
    if args.format == "html":
        extracted = text
    elif args.format == "text":
        extracted = _text_to_readable(text) if _looks_like_html(text) else text
    else:
        extracted = _html_to_readable(text) if _looks_like_html(text) else text
    note = _empty_content_note(extracted, text, args.format)
    if args.pattern is not None:
        extracted = _matching_lines(extracted, args.pattern)
        if not extracted and note is None:
            note = f"no line matched pattern {args.pattern!r}"
    window = extracted[args.offset : args.offset + args.max_chars]
    truncated = args.offset + args.max_chars < len(extracted)
    return WebfetchResult(
        url=url,
        status=response.status_code,
        content=window,
        truncated=truncated,
        next_offset=args.offset + len(window) if truncated else None,
        note=note,
    )


def _empty_content_note(extracted: str, text: str, fmt: str) -> str | None:
    if fmt == "html" or len(text) < MIN_RENDERED_HTML_CHARS:
        return None
    # Either nothing survived extraction, or what did is a sliver of the markup:
    # both mean the words are built by scripts, as for a JS-rendered ranking.
    if len(extracted.strip()) >= MIN_TEXT_CHARS and len(extracted) * 50 >= len(text):
        return None
    return (
        "the page carries little text after extraction although its markup is large:"
        " it is probably rendered client-side. Try format=html, a cached or AMP copy,"
        " or the JSON endpoint the page itself calls."
    )


def _exa_search(query: str, count: int, key: str) -> list[SearchHit]:
    with httpx2.Client(
        timeout=20, headers={"x-api-key": key}, verify=build_ssl_context()
    ) as client:
        response = client.post(
            "https://api.exa.ai/search",
            json={
                "query": query,
                "numResults": count,
                "contents": {"text": {"maxCharacters": 400}},
            },
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


def _unwrap_url(href: str) -> str:
    href = html.unescape(href)
    encoded = _ENCODED_URL.search(href)
    if encoded is not None:
        return html.unescape(encoded.group(1))
    redirect = _BING_REDIRECT.search(href)
    if redirect is not None:
        token = redirect.group(1)
        padded = token + "=" * (-len(token) % 4)
        try:
            return base64.urlsafe_b64decode(padded).decode("utf-8", "replace")
        except ValueError:
            return href
    return href


def _bing_search(query: str, count: int) -> list[SearchHit]:
    with httpx2.Client(
        follow_redirects=True, timeout=20, headers=HEADERS, verify=build_ssl_context()
    ) as client:
        response = client.get("https://www.bing.com/search", params={"q": query})
        response.raise_for_status()
        page = response.text
    hits: list[SearchHit] = []
    for block in _BING_BLOCK.findall(page):
        link = _BING_LINK.search(block)
        if link is None:
            continue
        url = _unwrap_url(link.group(1))
        if not url.startswith("http"):
            continue
        snippet = _BING_SNIPPET.search(block)
        hits.append(
            SearchHit(
                title=_strip(link.group(2)),
                url=url,
                snippet=_strip(snippet.group(1))[:SNIPPET_CHARS] if snippet else "",
            )
        )
        if len(hits) >= count:
            break
    return hits


def _duckduckgo_search(query: str, count: int) -> list[SearchHit]:
    with httpx2.Client(
        follow_redirects=True, timeout=20, headers=HEADERS, verify=build_ssl_context()
    ) as client:
        response = client.post("https://html.duckduckgo.com/html/", data={"q": query})
        response.raise_for_status()
        page = response.text
    hits: list[SearchHit] = []
    for block in page.split(_DDG_RESULT_MARKER)[1:]:
        link = _DDG_LINK_SLICE.search(block)
        if link is None:
            continue
        url = _unwrap_url(link.group(1))
        if not url.startswith("http"):
            continue
        snippet = _DDG_SNIPPET.search(block)
        hits.append(
            SearchHit(
                title=_strip(link.group(2)),
                url=url,
                snippet=_strip(snippet.group(1))[:SNIPPET_CHARS] if snippet else "",
            )
        )
        if len(hits) >= count:
            break
    return hits


def _normalize(href: str) -> str:
    return href.split("#", 1)[0].rstrip("/")


def _dedupe(hits: list[SearchHit]) -> list[SearchHit]:
    seen: set[str] = set()
    unique: list[SearchHit] = []
    for hit in hits:
        key = _normalize(hit.url)
        if key in seen or _host(hit.url) in _ENGINE_HOSTS:
            continue
        seen.add(key)
        unique.append(hit)
    return unique


def _host(href: str) -> str:
    without_scheme = href.split("://", 1)[-1]
    return without_scheme.split("/", 1)[0].lower()


# A scraper's own pages answer a query without being an answer to it.
_ENGINE_HOSTS = frozenset({
    "bing.com",
    "www.bing.com",
    "duckduckgo.com",
    "html.duckduckgo.com",
    "exa.ai",
})

# Long queries are the ones a generic scraper answers with a definition page; a
# short one (a product name) must not be filtered out for missing a word. Half
# the distinct words is enough to tell a real result from a dictionary entry.
_CANDIDATE_WORDS = 2
# Shorter words are articles, years or noise in both languages.
MIN_WORD_CHARS = 3


def _words(text: str) -> set[str]:
    folded = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char))
    words = re.findall(r"[a-z0-9]+", ascii_text.lower())
    return {
        word for word in words if len(word) >= MIN_WORD_CHARS and word not in _STOPWORDS
    }


_STOPWORDS = frozenset({
    "the",
    "and",
    "for",
    "with",
    "best",
    "que",
    "qui",
    "les",
    "des",
    "une",
    "dans",
    "pour",
    "sur",
    "avec",
    "meilleur",
    "meilleurs",
})


def _relevant(hits: list[SearchHit], query: str) -> list[SearchHit]:
    wanted = _words(query)
    if not wanted:
        return hits
    needed = max(1, len(wanted) // _CANDIDATE_WORDS)
    kept = [
        hit
        for hit in hits
        if len(wanted & _words(f"{hit.title} {hit.url} {hit.snippet}")) >= needed
    ]
    return kept


def _engines(
    query: str, count: int, key: str
) -> list[tuple[str, Callable[[], list[SearchHit]]]]:
    engines: list[tuple[str, Callable[[], list[SearchHit]]]] = []
    if key:
        engines.append(("exa", lambda: _exa_search(query, count, key)))
    engines.append(("bing", lambda: _bing_search(query, count)))
    engines.append(("duckduckgo", lambda: _duckduckgo_search(query, count)))
    return engines


def run_websearch(args: WebsearchArgs) -> WebsearchResult:
    query = args.query.strip()
    if not query:
        return WebsearchResult(query=query, error="query must not be empty")
    key = os.environ.get("EXA_API_KEY", "").strip()
    failures: list[str] = []
    # The first engine that answers anything, kept in case no engine answers
    # with something relevant: a poor list still beats no list.
    fallback: list[SearchHit] | None = None
    for name, engine in _engines(query, args.num_results, key):
        try:
            hits = _dedupe(engine())
        except Exception as error:  # the model needs the reason, not a traceback
            failures.append(f"{name}: {type(error).__name__}: {error}")
            continue
        if not hits:
            failures.append(f"{name}: no results")
            continue
        relevant = _relevant(hits, query)
        if relevant:
            return WebsearchResult(query=query, results=relevant[: args.num_results])
        failures.append(f"{name}: no relevant results")
        if fallback is None:
            fallback = hits
    if fallback is not None:
        return WebsearchResult(
            query=query,
            results=fallback[: args.num_results],
            note="no engine returned a result sharing this query's words;"
            " these are the closest, narrow the query or add a site name.",
        )
    return WebsearchResult(query=query, error="; ".join(failures))
