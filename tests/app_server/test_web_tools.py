from __future__ import annotations

import httpx
import respx

from vibe.app_server._web_tools import (
    WebfetchArgs,
    WebsearchArgs,
    run_webfetch,
    run_websearch,
)

LONG_PAGE = (
    "<html><head><style>p{color:red}</style></head><body>"
    '<nav><a href="/rubrique">Rubrique</a></nav>'
    "<main><h1>Titre de la page</h1>"
    + "".join(f"<p>ligne {index} du corps</p>" for index in range(40))
    + "</main><footer>Mentions legales</footer></body></html>"
)

CLIENT_SIDE_PAGE = (
    "<html><body><div id='app'></div><script>"
    + "var bundle = '" + "x" * 20_000 + "';"
    + "</script></body></html>"
)


def test_webfetch_drops_chrome_and_pages_through_content(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("https://example.com/long").mock(
        return_value=httpx.Response(200, text=LONG_PAGE)
    )

    first = run_webfetch(WebfetchArgs(url="https://example.com/long", max_chars=200))

    assert first.error is None
    assert "Rubrique" not in first.content
    assert "Mentions legales" not in first.content
    assert first.truncated is True
    assert first.next_offset is not None

    rest = run_webfetch(
        WebfetchArgs(url="https://example.com/long", offset=first.next_offset or 0)
    )

    assert rest.error is None
    assert rest.content
    assert set(first.content.split()) != set(rest.content.split())
    assert "ligne 39 du corps" in rest.content


def test_webfetch_pattern_keeps_matching_lines(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://example.com/long").mock(
        return_value=httpx.Response(200, text=LONG_PAGE)
    )

    result = run_webfetch(
        WebfetchArgs(url="https://example.com/long", pattern=r"^ligne 3 \D")
    )

    assert result.error is None
    assert result.content == "ligne 3 du corps"
    assert result.note is None


def test_webfetch_reports_a_pattern_that_matches_nothing(
    respx_mock: respx.MockRouter,
) -> None:
    respx_mock.get("https://example.com/long").mock(
        return_value=httpx.Response(200, text=LONG_PAGE)
    )

    result = run_webfetch(WebfetchArgs(url="https://example.com/long", pattern="absente"))

    assert result.content == ""
    assert result.note is not None
    assert "absente" in result.note


def test_webfetch_rejects_an_invalid_pattern(respx_mock: respx.MockRouter) -> None:
    result = run_webfetch(WebfetchArgs(url="https://example.com/long", pattern="["))

    assert result.error is not None
    assert result.error.startswith("invalid pattern")
    assert not respx_mock.calls


def test_webfetch_notes_a_client_side_page(respx_mock: respx.MockRouter) -> None:
    respx_mock.get("https://example.com/spa").mock(
        return_value=httpx.Response(200, text=CLIENT_SIDE_PAGE)
    )

    result = run_webfetch(WebfetchArgs(url="https://example.com/spa"))

    assert result.content.strip() == ""
    assert result.note is not None
    assert "client-side" in result.note


def _bing_page(title: str, url: str, snippet: str) -> str:
    return (
        "<html><body><ol>"
        f'<li class="b_algo"><h2><a href="{url}">{title}</a></h2>'
        f"<p>{snippet}</p></li>"
        "</ol></body></html>"
    )


def _duckduckgo_page(title: str, url: str, snippet: str) -> str:
    return (
        "<html><body>"
        f'<a class="result__a" rel="nofollow" href="{url}">{title}</a>'
        f'<a class="result__snippet" href="{url}">{snippet}</a>'
        "</body></html>"
    )


def test_websearch_skips_an_engine_that_answers_off_topic(
    respx_mock: respx.MockRouter, monkeypatch
) -> None:
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    respx_mock.get("https://www.bing.com/search").mock(
        return_value=httpx.Response(
            200,
            text=_bing_page(
                "Meilleur - Dictionnaire", "https://dico.example/meilleur", "definition"
            ),
        )
    )
    respx_mock.post("https://html.duckduckgo.com/html/").mock(
        return_value=httpx.Response(
            200,
            text=_duckduckgo_page(
                "Comparatif photophone 2026",
                "https://photo.example/guide",
                "tests camera comparatif photophone 2026",
            ),
        )
    )

    result = run_websearch(
        WebsearchArgs(query="meilleur photophone 2026 test comparatif camera")
    )

    assert result.error is None
    assert result.note is None
    assert [hit.url for hit in result.results] == ["https://photo.example/guide"]


def test_websearch_returns_best_effort_when_nothing_is_relevant(
    respx_mock: respx.MockRouter, monkeypatch
) -> None:
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    for route, page in (
        (
            respx_mock.get("https://www.bing.com/search"),
            _bing_page("Meilleur - Wikipedia", "https://dico.example/meilleur", "page"),
        ),
        (
            respx_mock.post("https://html.duckduckgo.com/html/"),
            _duckduckgo_page("Meilleur", "https://dico.example/autre", "page"),
        ),
    ):
        route.mock(return_value=httpx.Response(200, text=page))

    result = run_websearch(
        WebsearchArgs(query="meilleur photophone 2026 test comparatif camera")
    )

    assert result.error is None
    assert result.note is not None
    assert len(result.results) == 1


def test_websearch_drops_engine_pages_from_results(
    respx_mock: respx.MockRouter, monkeypatch
) -> None:
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    respx_mock.get("https://www.bing.com/search").mock(
        return_value=httpx.Response(
            200,
            text=_bing_page("photophone comparatif test", "https://www.bing.com/x", "spam"),
        )
    )
    respx_mock.post("https://html.duckduckgo.com/html/").mock(
        return_value=httpx.Response(
            200,
            text=_duckduckgo_page(
                "photophone comparatif test",
                "https://photo.example/guide",
                "tests camera comparatif photophone 2026",
            ),
        )
    )

    result = run_websearch(
        WebsearchArgs(query="meilleur photophone 2026 test comparatif camera")
    )

    assert [hit.url for hit in result.results] == ["https://photo.example/guide"]
