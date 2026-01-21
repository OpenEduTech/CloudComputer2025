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

    def write_graph(self, data):
        with self.driver.session() as session:
            # Write Nodes
            for node in data.get("nodes", []):
                session.execute_write(self._create_node, node)
            
            # Write Links
            for link in data.get("links", []):
                session.execute_write(self._create_link, link)

    @staticmethod
    def _create_node(tx, node):
        query = (
            "MERGE (n:Entity {id: $id}) "
            "SET n.label = $label, n.group = $group, n.info = $info, "
            "n.source = $source, n.confidence = $confidence, n.url = $url"
        )
        tx.run(query, **node)

    @staticmethod
    def _create_link(tx, link):
        query = (
            "MATCH (a:Entity {id: $source_id}), (b:Entity {id: $target_id}) "
            "MERGE (a)-[r:RELATED {relation: $relation}]->(b) "
            "SET r.desc = $desc, r.citation = $citation"
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
                    r.set(f"task:{task_id}", json.dumps({"status": "PROCESSING", "progress": 10, "message": "Planning..."}))
                    
                    # Run Workflow
                    result = workflow.run(user_input)
                    
                    if result:
                        # Write to Neo4j
                        if neo4j_writer:
                            neo4j_writer.write_graph(result)
                            
                        # Update status
                        r.set(f"task:{task_id}", json.dumps({
                            "status": "SUCCESS", 
                            "progress": 100, 
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
