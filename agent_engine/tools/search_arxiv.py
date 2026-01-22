import arxiv

def search_arxiv(query: str, max_results: int = 3):
    """
    搜索 Arxiv 论文
    """
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for result in search.results():
            results.append({
                "title": result.title,
                "summary": result.summary,
                "url": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d")
            })
        return results
    except Exception as e:
        print(f"Error searching Arxiv: {e}")
        return []

if __name__ == "__main__":
    print(search_arxiv("Knowledge Graph"))
