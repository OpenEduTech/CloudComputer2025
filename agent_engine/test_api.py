import requests
import time
import json
import os

BASE_URL = os.getenv("BASE_URL", "http://backend:8000/api")

def test_full_flow():
    print(f"=== Starting Integration Test (Target: {BASE_URL}) ===")
    
    # 1. Create Task
    keyword = "熵"
    print(f"Creating task for keyword: {keyword}...")
    try:
        resp = requests.post(f"{BASE_URL}/task", json={"keyword": keyword})
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id")
        print(f"Task created. ID: {task_id}")
    except Exception as e:
        print(f"Failed to create task: {e}")
        return

    # 2. Poll Status
    print("Polling task status...")
    max_retries = 120 # 120 * 2s = 240s timeout (Agent run takes time)
    for i in range(max_retries):
        try:
            resp = requests.get(f"{BASE_URL}/task/{task_id}/status")
            resp.raise_for_status()
            status_data = resp.json()
            
            status = status_data.get("status")
            progress = status_data.get("progress")
            message = status_data.get("message")
            
            print(f"[{i+1}/{max_retries}] Status: {status}, Progress: {progress}%, Message: {message}")
            
            if status == "SUCCESS":
                print("Task completed successfully!")
                result = status_data.get("result")
                print("Result Snippet:", json.dumps(result, ensure_ascii=False)[:200] + "...")
                break
            elif status == "FAILED":
                print(f"Task failed: {status_data.get('error')}")
                break
                
            time.sleep(2)
        except Exception as e:
            print(f"Error polling status: {e}")
            time.sleep(2)
    else:
        print("Timeout waiting for task completion.")

if __name__ == "__main__":
    test_full_flow()
