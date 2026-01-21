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

    def run(self, user_input):
        print(f"\n=== Starting Workflow for: {user_input} ===")
        
        # 1. Planner
        plan = self.planner.run(user_input)
        if not plan:
            print("Planner failed.")
            return None
            
        keywords = plan.get("keywords", [])
        subjects = plan.get("subjects", [])
        print(f"Plan: Keywords={keywords}, Subjects={subjects}")
        
        nodes = []
        
        # 2. Miner Loop
        for keyword in keywords:
            for subject in subjects:
                print(f"\n--- Processing {keyword} in {subject} ---")
                
                # Miner (RAG)
                node_data = self.miner.run(keyword, subject)
                
                # Query (Check Quality)
                need_online = self.query.run(node_data)
                
                if need_online == "yes":
                    print("RAG result insufficient, trying online search...")
                    online_node = self.miner_online.run(keyword, subject)
                    if online_node:
                        node_data = online_node
                
                if node_data:
                    # Validator
                    score = self.validator.run(node_data, subject)
                    node_data["confidence"] = score
                    node_data["id"] = str(uuid.uuid4()) # Assign ID
                    nodes.append(node_data)
                    print(f"Node created: {node_data['label']} (Score: {score})")
                else:
                    print(f"Failed to create node for {keyword} in {subject}")

        # 3. Relation Loop
        links = []
        # Find relations between nodes (Cross-domain analysis)
        # Simple logic: compare same keyword across different subjects
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1 = nodes[i]
                n2 = nodes[j]
                
                # Check if they are the same keyword but different subjects
                if n1['label'] == n2['label'] and n1['group'] != n2['group']:
                    print(f"\n--- Analyzing Relation between {n1['group']} and {n2['group']} for {n1['label']} ---")
                    link = self.relation.run(n1, n2)
                    if link:
                        link["source_id"] = n1["id"]
                        link["target_id"] = n2["id"]
                        # 手动添加 citation
                        s1 = n1.get("source", "Unknown")
                        s2 = n2.get("source", "Unknown")
                        # 如果 source 是列表，先转字符串
                        if isinstance(s1, list): s1 = "; ".join(s1)
                        if isinstance(s2, list): s2 = "; ".join(s2)
                        link["citation"] = f"{s1}; {s2}"
                        
                        links.append(link)
                        print(f"Link created: {link['relation']}")

        result = {
            "nodes": nodes,
            "links": links
        }
        return result

if __name__ == "__main__":
    workflow = KnowledgeGraphWorkflow()
    # Test run
    res = workflow.run("熵在信息论和热力学中的定义")
    import json
    print(json.dumps(res, ensure_ascii=False, indent=2))
