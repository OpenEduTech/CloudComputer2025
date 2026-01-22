from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse
from backend.models.llm_graph_builder import build_knowledge_graph
from backend.models.chat import llm_chat
from backend.models.bloom_filter import BloomFilter
from pymongo import MongoClient   
from tinydb import TinyDB, Query 
import asyncio
import os
import time
import shutil
from starlette.background import BackgroundTask

app = FastAPI()
users_col = None
templates = Jinja2Templates(directory="frontend/templates")
app.mount("/frontend/static", StaticFiles(directory="frontend/static"), name="frontend/static")
bf = BloomFilter(expected_elements=100, false_positive_rate=0.001)

# 开关服务器
@app.on_event("startup")
async def startup_event():
    global users_col
    while True:
        try:
            db = TinyDB("db.json")
            users_col = db.table("cloud_final")
            users_col.truncate()
            users_col.insert({
                "total_tokens": 50,
                "total_counts": 250
            })
             
            print(f"进程 {os.getpid()} 的 MongoDB 初始化成功")
            break
        except Exception as e:
            print(f"进程 {os.getpid()} 的 MongoDB 初始化失败：{str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    pass

# 功能路由
@app.post("/api/graph")
async def build_graph(request: Request):
    try:
        data = await request.json()
        concept = (data.get("concept") or "").strip()
        if not concept:
            return {"error": "empty concept", "nodes": [], "links": []}
        
        original_data = None

        global bf

        print("start")
        start = time.time()
        if bf.contains(concept):
            User = Query()
            doc = users_col.get(User.concept == concept)
            original_data = doc["graph"]
            # print(original_data)
            print("Bloom Filter 热查询命中")
            if original_data==None:
                original_data = await asyncio.to_thread(build_knowledge_graph, concept)
                users_col.insert({"concept": concept, "graph": original_data})
                bf.add(concept)
        else: 
            original_data = await asyncio.to_thread(build_knowledge_graph, concept)
            users_col.insert({"concept": concept, "graph": original_data})
            bf.add(concept)
        end = time.time()
        print("end")
        print(f"{end-start}")
        
        add_tokens = int(original_data.get("tokens", 0)/1000)
        add_counts = 1
        doc = next((d for d in users_col.all() if "total_tokens" in d and "total_counts" in d), None)
        if doc:
            doc["total_tokens"] += add_tokens
            doc["total_counts"] += add_counts
            users_col.update(doc, doc_ids=[doc.doc_id])
        
        nodes=[]
        links=[]
        for node in original_data["nodes"]:
            nodes.append({"id":node["id"],"name":node["name"],"discipline":node["discipline"],"value":node["value"],"description":node["description"]})
        for link in original_data["links"]:
            sourseName = [node["name"] for node in original_data["nodes"] if node["id"] == link["source"]]
            targetName = [node["name"] for node in original_data["nodes"] if node["id"] == link["target"]]
            links.append({"source":link["source"],"target":link["target"],"sourseName":sourseName,"targetName":targetName,"relation":link["relation"],"description":link["description"]})
        graph={"nodes":nodes, "links":links}
        return graph

    except Exception as e:
        return {"error": str(e), "nodes": [], "links": []}

@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = (data.get("message") or "").strip()
        history = data.get("history") or []
        
        reply_text, usage = await asyncio.to_thread(llm_chat, message, history)

        add_tokens = int(usage.get("total_tokens", 0)/1000)
        add_counts = 1
        doc = next((d for d in users_col.all() if "total_tokens" in d and "total_counts" in d), None)
        if doc:
            doc["total_tokens"] += add_tokens
            doc["total_counts"] += add_counts
            users_col.update(doc, doc_ids=[doc.doc_id])
        
        return {"reply": reply_text, "usage": usage}

    except Exception as e:
        return {"error": str(e), "reply": ""}

@app.post("/api/counts_and_tokens")
async def counts_and_tokens(request: Request):
    try:
        doc = next((d for d in users_col.all() if "total_tokens" in d and "total_counts" in d), None)
        docs = dict(doc) if doc else {}
        
        return {
            "total_counts": docs.get("total_counts",0),
            "total_tokens": docs.get("total_tokens",0)
        }

    except Exception as e:
        return {"error": str(e)}


# 下载路由：打包并下载 frontend/static/downloads 文件夹
@app.get("/download/source")
async def download_source():
    folder_path = os.path.join("frontend", "static", "downloads")
    if not os.path.isdir(folder_path):
        return Response(status_code=404, content="downloads 文件夹不存在")

    zip_base = os.path.join("frontend", "static", f"downloads_{int(time.time())}")
    zip_path = shutil.make_archive(zip_base, 'zip', folder_path)

    def _cleanup():
        try:
            os.remove(zip_path)
        except Exception:
            pass

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="downloads.zip",
        background=BackgroundTask(_cleanup)
    )


# 页面路由
@app.get("/index.html", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=200)

@app.get("/graph.html", response_class=HTMLResponse)
async def calculator2(request: Request):
    return templates.TemplateResponse("graph.html", {"request": request})

@app.get("/technologies.html", response_class=HTMLResponse)
async def calculator2(request: Request):
    return templates.TemplateResponse("technologies.html", {"request": request})

@app.get("/find.html", response_class=HTMLResponse)
async def find_page(request: Request):
    return templates.TemplateResponse("find.html", {"request": request})