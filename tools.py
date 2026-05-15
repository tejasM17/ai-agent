from duckduckgo_search import DDGS

def medical_web_search(query: str) -> str:
    """
    Searches DuckDuckGo for medical guidance related to symptoms.
    """

    results_text = []

    with DDGS() as ddgs:
        results = ddgs.text(
            keywords=query,
            max_results=5
        )

        for result in results:
            title = result.get("title", "")
            body = result.get("body", "")
            results_text.append(f"{title}: {body}")

    return "\n".join(results_text)