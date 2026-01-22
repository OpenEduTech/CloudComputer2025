import os
from pathlib import Path
from fastapi import FastAPI,Form
from fastapi.middleware.cors import CORSMiddleware
from model import graph,chain_difinition,chain_qa
from api_model import ConceptModel,DifinitionModel,QaModel
from typing import Annotated
from dotenv import load_dotenv
import pymongo
import json

load_dotenv()
dburl = os.getenv("mongoDB_url")
dbname = os.getenv("dbname")
#连接数据库
myclient = pymongo.MongoClient(dburl)
mydb = myclient[dbname]
#两个数据集和，一个存概念对应的结点和边，另一个存定义
collist = mydb.list_collection_names()
if "relations" not in collist:
    mydb.create_collection("relations")
    mydb['relations'].create_index('concept')
if "definition" not in collist:
    mydb.create_collection("definition")
    mydb["definition"].create_index(['concept','domain'])


app = FastAPI()

origins = ['*'] # 允许跨域请求的源列表

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def helloworld():
    return {"Hello":"world"}

#概念-关系api接口
@app.post("/api/v1/concept/relations")
def get_concept_relations(data:Annotated[ConceptModel,Form()]):
    hasdata = mydb['relations'].find_one({'concept':data.concept})
    if hasdata != None:
        return {
            "code": 200,
            "msg": "success",
            "data": hasdata['data']
        }
    try:
        res = graph.invoke({"concept":data.concept,"times":0})
    except BaseException:
        return {
            "code": 511,
            "msg": "error",
            "data": None
        }
    #将结果插入数据库，下次询问时可以不再依赖智能体
    mydata = {
        "concept":data.concept,
        "data":res['content']
    }
    mydb['relations'].insert_one(mydata)
    return {
        "code": 200,
        "msg": "success",
        "data": res['content']
    }

#获取具体概念的接口
@app.post("/api/v1/concept/definition")
def get_concept_definition(data:Annotated[DifinitionModel,Form()]):
    hasdata = mydb["definition"].find_one({"concept":data.concept,"domain":data.domain})
    if hasdata != None:
        return{
            "code": 200,
            "msg": "success",
            "data": hasdata['data']
        }
    try:
        res = chain_difinition.invoke({"concept":data.concept,"domain":data.domain})
    except BaseException as e:
        return {
            "code": 511,
            "msg": "error",
            "data": str(e)
        }
    #插入数据
    mydata = {
        "concept":data.concept,
        "domain":data.domain,
        "data":res
    }
    mydb['definition'].insert_one(mydata)
    return {
        "code": 200,
        "msg": "success",
        "data": res
    }

#提问api
@app.post("/api/v1/concept/qa")
def get_concept_qa(data:Annotated[QaModel,Form()]):
    concept = data.concept
    qa = data.question
    #从数据库获取图谱
    graphdata = mydb["relations"].find_one({"concept":concept})
    if graphdata == None:
        return {
            "code": 512,
            "msg": "图谱数据不存在",
            "data": None
        }
    #res = chain_qa.invoke({"concept":concept,"question":qa,"concept_relations":json.dumps(graphdata,ensure_ascii=False)})
    try:
        res = chain_qa.invoke({"concept":concept,"question":qa,"concept_relations":json.dumps(graphdata['data'],ensure_ascii=False)})
    except BaseException:
        return {
            "code": 511,
            "msg": "error",
            "data": None
        }
    return {
        "code": 200,
        "msg": "success",
        "data": res
    }