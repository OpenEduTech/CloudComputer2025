import requests
import time
import sys
import json

# Inside docker, backend is at localhost:8000 because we run this script inside backend container
# OR if we run from host, it's localhost:8000. 
# Let's assume we run this script INSIDE the backend container for network reliability.
BASE_URL = "http://localhost:8000/api"
KEYWORD = "熵在物理学和化学领域的定义"

def test():
    print(f"=== 1. 发起任务: {KEYWORD} ===")
    try:
        # Create task
        res = requests.post(f"{BASE_URL}/task", json={"keyword": KEYWORD, "params": {"depth": 2}})
        res.raise_for_status()
        task_id = res.json()["task_id"]
        print(f"Task ID: {task_id}")
    except Exception as e:
        print(f"Error starting task: {e}")
        sys.exit(1)

    print("\n=== 2. 等待任务完成 ===")
    result_node_id = None
    start_time = time.time()
    while True:
        try:
            status_res = requests.get(f"{BASE_URL}/task/{task_id}/status")
            status_data = status_res.json()
            status = status_data["status"]
            progress = status_data.get("progress", 0)
            msg = status_data.get("message", "")
            
            # Print status update
            print(f"\rStatus: {status} [{progress}%] - {msg}", end="", flush=True)
            
            if status == "SUCCESS":
                print("\n\nTask Completed Successfully!")
                result_node_id = status_data.get("result_node_id")
                # Fallback if result_node_id is null (older logic might use keyword)
                if not result_node_id: 
                    result_node_id = KEYWORD
                break
            elif status == "FAILED":
                print(f"\n\nTask Failed: {status_data.get('error')}")
                sys.exit(1)
            
            if time.time() - start_time > 300: # 5 minutes timeout
                print("\n\nTimeout waiting for task completion")
                sys.exit(1)
                
            time.sleep(1)
        except Exception as e:
            print(f"\nPolling error: {e}")
            time.sleep(1)

    print(f"\n=== 3. 获取图谱数据 (Node ID: {result_node_id}) ===")
    try:
        # Fetch graph
        # Note: result_node_id might be a keyword string or a UUID depending on backend implementation
        # But for 'search', it usually returns the graph for the keyword or the center node.
        # Let's try fetching by the keyword first if UUID fails or is ambiguous.
        # Actually, the API expects the center node ID or keyword.
        
        graph_res = requests.get(f"{BASE_URL}/graph/{result_node_id}", params={"depth": 2})
        graph_data = graph_res.json()
        
        nodes = graph_data.get("nodes", [])
        links = graph_data.get("links", [])
        
        print(f"\n[检测结果]")
        print(f"节点数量: {len(nodes)}")
        print(f"连线数量: {len(links)}")
        
        if len(nodes) > 0:
            print("\n发现以下节点:")
            for n in nodes:
                # Check confidence to see if it would be highlighted
                conf = n.get('confidence', 0.6)
                is_low = conf < 0.66
                marker = "[低置信度-红框]" if is_low else "[正常]"
                print(f"- {marker} {n.get('label')} | 领域: {n.get('group')} | 置信度: {conf}")
            
            print("\n结论: 后端已成功生成图谱数据。")
            if len(nodes) > 0:
                print("前端状态: 由于已移除过滤阈值(设为0)，前端 <main> 区域应当显示上述节点。")
            else:
                print("前端状态: 数据为空，前端无内容显示。")
        else:
            print("\n结论: 后端返回了空数据，未生成图谱。")

    except Exception as e:
        print(f"Error fetching graph: {e}")

if __name__ == "__main__":
    test()
