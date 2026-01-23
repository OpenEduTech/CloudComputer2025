import wikipedia

def search_wikipedia(query: str, lang: str = "zh"):
    """
    搜索 Wikipedia
    """
    try:
        wikipedia.set_lang(lang)
        # 先搜索获取建议标题
        search_res = wikipedia.search(query, results=1)
        if not search_res:
            return None
            
        title = search_res[0]
        page = wikipedia.page(title, auto_suggest=False)
        
        return {
            "title": page.title,
            "summary": page.summary[:500] + "...", # 截取摘要
            "url": page.url,
            "content": page.content[:2000] # 截取部分正文
        }
    except Exception as e:
        print(f"Error searching Wikipedia: {e}")
        return None

if __name__ == "__main__":
    print(search_wikipedia("知识图谱"))
