import uuid
from agents.planner import PlannerAgent
from agents.miner import MinerAgent
from agents.query import QueryAgent
from agents.miner_online import MinerOnlineAgent
from agents.validator import ValidatorAgent
from agents.relation import RelationAgent

class KnowledgeGraphWorkflow:
    def __init__(self):
        self.planner = PlannerAgent()
        self.miner = MinerAgent()
        self.query = QueryAgent()
        self.miner_online = MinerOnlineAgent()
        self.validator = ValidatorAgent()
        self.relation = RelationAgent()

    def run(self, user_input, depth=2, status_callback=None):
        print(f"\n=== Starting Workflow for: {user_input} (Depth: {depth}) ===")
        
        if status_callback:
            status_callback(step_index=1, progress=10, message="Agent 正在规划任务...")

        # 1. Planner
        plan = self.planner.run(user_input)
        if not plan:
            print("Planner failed.")
            return None
            
        keywords = plan.get("keywords", [])
        subjects = plan.get("subjects", [])
        print(f"Plan: Keywords={keywords}, Subjects={subjects}")
        
        if status_callback:
            status_callback(step_index=2, progress=20, message=f"规划完成，发现 {len(keywords)} 个关键词...")

        nodes = []
        
        # 2. Miner Loop
        # 使用 ThreadPoolExecutor 实现并发 (Max 3 workers)
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        miner_tasks = []
        for keyword in keywords:
            for subject in subjects:
                miner_tasks.append((keyword, subject))
        
        total_mining_steps = len(miner_tasks)
        completed_mining_steps = 0
        
        # 线程安全锁
        import threading
        node_lock = threading.Lock()
        
        def process_miner_task(task_args):
            keyword, subject = task_args
            print(f"\n--- Processing {keyword} in {subject} ---")
            
            # Miner (RAG)
            miner_results = self.miner.run(keyword, subject, depth=depth)
            
            # Fallback to Online
            if not miner_results:
                online_node = self.miner_online.run(keyword, subject, depth=depth)
                if online_node:
                    miner_results = [online_node]
            
            local_nodes = []
            for node_data in miner_results:
                # Query Check
                need_online = self.query.run(node_data)
                
                if need_online == "yes" and not node_data.get("is_online", False):
                    print(f"Node {node_data['label']} flagged as poor quality.")
                
                if node_data:
                    # Validator
                    score = self.validator.run(node_data, subject)
                    node_data["confidence"] = score
                    node_data["id"] = str(uuid.uuid4())
                    
                    if score > 0.5:
                        local_nodes.append(node_data)
                        print(f"Node created: {node_data['label']} (Score: {score})")
            
            return local_nodes

        print(f"Starting parallel mining with {len(miner_tasks)} tasks...")
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_task = {executor.submit(process_miner_task, t): t for t in miner_tasks}
            
            for future in as_completed(future_to_task):
                completed_mining_steps += 1
                if status_callback:
                    p = 20 + int((completed_mining_steps / max(1, total_mining_steps)) * 50)
                    status_callback(step_index=2, progress=p, message=f"正在并行检索 ({completed_mining_steps}/{total_mining_steps})...")
                
                try:
                    new_nodes = future.result()
                    with node_lock:
                        nodes.extend(new_nodes)
                except Exception as e:
                    print(f"Mining task failed: {e}")

        if status_callback:
            status_callback(step_index=3, progress=70, message="正在分析实体间关系...")

        # 3. Relation Loop
        # Prepare relation pairs
        relation_pairs = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1 = nodes[i]
                n2 = nodes[j]
                if n1['label'] == n2['label'] and n1['group'] != n2['group']:
                    relation_pairs.append((n1, n2))
        
        links = []
        total_rel_steps = len(relation_pairs)
        completed_rel_steps = 0
        
        def process_relation_task(pair):
            n1, n2 = pair
            print(f"\n--- Analyzing Relation: {n1['group']} <-> {n2['group']} ---")
            link = self.relation.run(n1, n2)
            if link:
                link["source_id"] = n1["id"]
                link["target_id"] = n2["id"]
                s1 = n1.get("source", "Unknown")
                if isinstance(s1, list): s1 = "; ".join(s1)
                s2 = n2.get("source", "Unknown")
                if isinstance(s2, list): s2 = "; ".join(s2)
                link["citation"] = f"{s1}; {s2}"
                link["source"] = n1["label"]
                link["target"] = n2["label"]
                return link
            return None

        print(f"Starting parallel relation analysis with {len(relation_pairs)} pairs...")
        # Reduce concurrency to 2 to prevent OOM
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_pair = {executor.submit(process_relation_task, p): p for p in relation_pairs}
            
            for future in as_completed(future_to_pair):
                completed_rel_steps += 1
                # Optional: update progress for relation phase if needed
                
                try:
                    new_link = future.result()
                    if new_link:
                        with node_lock: # Reuse lock for links list safety
                            links.append(new_link)
                            print(f"Link created: {new_link['relation']}")
                except Exception as e:
                    print(f"Relation task failed: {e}")

        if status_callback:
            status_callback(step_index=4, progress=90, message="图谱构建完成，准备写入数据库...")

        result = {
            "nodes": nodes,
            "links": links,
            "main_node_id": nodes[0]["id"] if nodes else None
        }
        return result

if __name__ == "__main__":
    workflow = KnowledgeGraphWorkflow()
    # Test run
    res = workflow.run("熵在信息论和热力学中的定义")
    import json
    print(json.dumps(res, ensure_ascii=False, indent=2))
