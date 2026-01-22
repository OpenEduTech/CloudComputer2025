import time
import redis
import json
import traceback
from config import settings
from workflow import KnowledgeGraphWorkflow
from neo4j import GraphDatabase

class Neo4jWriter:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI, 
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def write_graph(self, data, task_id):
        with self.driver.session() as session:
            # Write Nodes
            for node in data.get("nodes", []):
                node["task_id"] = task_id
                session.execute_write(self._create_node, node)
            
            # Write Links
            for link in data.get("links", []):
                link["task_id"] = task_id
                session.execute_write(self._create_link, link)

    @staticmethod
    def _create_node(tx, node):
        # 使用 task_ids 列表来记录该节点被哪些任务引用过
        query = (
            "MERGE (n:Entity {id: $id}) "
            "SET n.label = $label, n.group = $group, n.info = $info, "
            "n.source = $source, n.confidence = $confidence, n.url = $url "
            "SET n.task_ids = CASE WHEN n.task_ids IS NULL THEN [$task_id] "
            "ELSE n.task_ids + [x IN [$task_id] WHERE NOT x IN n.task_ids] END"
        )
        tx.run(query, **node)

    @staticmethod
    def _create_link(tx, link):
        query = (
            "MATCH (a:Entity {id: $source_id}), (b:Entity {id: $target_id}) "
            "MERGE (a)-[r:RELATED {relation: $relation}]->(b) "
            "SET r.desc = $desc, r.citation = $citation "
            "SET r.task_ids = CASE WHEN r.task_ids IS NULL THEN [$task_id] "
            "ELSE r.task_ids + [x IN [$task_id] WHERE NOT x IN r.task_ids] END"
        )
        tx.run(query, **link)

def main():
    print("AutoKGS Worker starting...")
    
    # Connect to Redis
    r = None
    retry_count = 0
    while retry_count < 5:
        try:
            r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
            r.ping()
            print("Successfully connected to Redis.")
            break
        except Exception as e:
            print(f"Failed to connect to Redis (Attempt {retry_count+1}/5): {e}")
            retry_count += 1
            time.sleep(2)
            
    if not r:
        print("Could not connect to Redis. Exiting.")
        return

    # Initialize Workflow & Neo4j
    workflow = KnowledgeGraphWorkflow()
    neo4j_writer = None
    try:
        neo4j_writer = Neo4jWriter()
        print("Connected to Neo4j.")
    except Exception as e:
        print(f"Warning: Could not connect to Neo4j: {e}")

    print("Worker is ready and waiting for tasks...")
    
    while True:
        try:
            # Blocking pop from task_queue
            # Expecting format: {"task_id": "...", "keyword": "..."}
            item = r.blpop("task_queue", timeout=5)
            
            if item:
                queue_name, task_json = item
                print(f"Received task: {task_json}")
                
                try:
                    task = json.loads(task_json)
                    user_input = task.get("keyword")
                    task_id = task.get("task_id")
                    
                    # Update status
                    r.set(f"task:{task_id}", json.dumps({
                        "status": "PROCESSING", 
                        "progress": 5, 
                        "step_index": 1,
                        "message": "Planning..."
                    }))
                    
                    # Define Callback
                    def status_callback(step_index, progress, message):
                        try:
                            r.set(f"task:{task_id}", json.dumps({
                                "status": "PROCESSING",
                                "progress": progress,
                                "step_index": step_index,
                                "message": message
                            }))
                            print(f"Status Updated: Step={step_index}, Progress={progress}%, Msg={message}")
                        except Exception as e:
                            print(f"Failed to update status: {e}")

                    # Run Workflow
                    # Pass depth parameter if available
                    params = task.get("params", {})
                    depth = params.get("depth", 2) # Default depth 2
                    
                    result = workflow.run(user_input, depth=depth, status_callback=status_callback)
                    
                    if result:
                        # Write to Neo4j
                        if neo4j_writer:
                            neo4j_writer.write_graph(result, task_id)
                            
                        # Update status
                        r.set(f"task:{task_id}", json.dumps({
                            "status": "SUCCESS", 
                            "step_index": 5,
                            "progress": 100, 
                            "message": "Completed",
                            "result_node_id": result.get("main_node_id"),
                            "result": result
                        }))
                        print(f"Task {task_id} completed successfully.")
                    else:
                        r.set(f"task:{task_id}", json.dumps({"status": "FAILED", "error": "Workflow returned no result"}))
                
                except Exception as e:
                    print(f"Error processing task: {e}")
                    traceback.print_exc()
                    if task_id:
                         r.set(f"task:{task_id}", json.dumps({"status": "FAILED", "error": str(e)}))
            
            else:
                # Heartbeat
                print(".", end="", flush=True)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in worker loop: {e}")
            time.sleep(5)
            
    if neo4j_writer:
        neo4j_writer.close()

if __name__ == "__main__":
    main()
