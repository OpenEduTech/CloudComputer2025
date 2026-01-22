import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent import get_agent
from neo4j_client import LocalNeo4jClient

app = FastAPI(title="Cross-Discipline Knowledge Graph Agent (Enhanced)")

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")

@app.get("/")
def index():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "web/index.html not found"}

@app.get("/api/graph")
def api_graph(concept: str, write_neo4j: bool = True):
    concept = (concept or "").strip()
    if not concept:
        raise HTTPException(status_code=400, detail="concept is required")

    agent = get_agent()
    graph = agent.generate_graph(concept)

    if write_neo4j:
        neo = LocalNeo4jClient()
        try:
            neo.clear_local_data()
            neo.import_to_local_neo4j(graph)
        finally:
            neo.close()

    return graph
