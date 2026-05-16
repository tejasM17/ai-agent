from ddgs import DDGS

def medical_web_search(query: str) -> str:
    """
    Searches DuckDuckGo for medical guidance related to symptoms.
    """

    results_text = []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query=query,
                max_results=5
            ))

            for result in results:
                title = result.get("title", "")
                body = result.get("body", "")
                results_text.append(f"{title}: {body}")

        if not results_text:
            return "No relevant medical guidelines found."

    except Exception as e:
        print(f"Web Search Tool Error: {e}")
        return f"Error during search: {str(e)}"

    return "\n".join(results_text)