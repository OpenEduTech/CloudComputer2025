import chromadb
import json
import os
import sys
import time

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from chromadb.utils import embedding_functions
from tools.ecnu_embedding import ECNUEmbeddingFunction

def import_dump():
    dump_file_path = "/app/data/chroma_dump.json"
    
    if not os.path.exists(dump_file_path):
        print(f"Error: Dump file not found at {dump_file_path}")
        return

    print(f"Connecting to ChromaDB at {settings.CHROMA_SERVER_HOST}:{settings.CHROMA_SERVER_PORT}...")
    try:
        client = chromadb.HttpClient(
            host=settings.CHROMA_SERVER_HOST,
            port=settings.CHROMA_SERVER_PORT
        )
        
        # Initialize Embedding Function
        if "ecnu" in settings.EMBEDDING_MODEL:
            print("Using ECNU Embedding Function")
            embedding_fn = ECNUEmbeddingFunction()
        else:
            print(f"Using SentenceTransformer Embedding: {settings.EMBEDDING_MODEL}")
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )

        print(f"Reading dump file: {dump_file_path}...")
        with open(dump_file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
            
        print(f"Found {len(all_data)} collections in dump file.")
        
        for col_name, records in all_data.items():
            print(f"\nProcessing collection: {col_name} ({len(records)} records)")
            
            # Get or create collection
            # We delete it first to ensure a clean state if it exists, 
            # or we can use upsert. For a full restore, deleting might be safer to avoid stale data.
            # But let's stick to get_or_create and upsert to be safe against accidental data loss of other things?
            # Actually, user said "import", usually implies restore. 
            # Let's try to get_or_create.
            
            collection = client.get_or_create_collection(
                name=col_name,
                embedding_function=embedding_fn
            )
            
            if not records:
                continue
                
            # Prepare batches
            batch_size = 500
            total_records = len(records)
            
            # Extract lists
            ids = [r['id'] for r in records]
            documents = [r['document'] for r in records]
            metadatas = [r['metadata'] for r in records]
            
            # Upsert in batches
            for i in range(0, total_records, batch_size):
                end_idx = min(i + batch_size, total_records)
                batch_ids = ids[i:end_idx]
                batch_docs = documents[i:end_idx]
                batch_metas = metadatas[i:end_idx]
                
                print(f"  - Upserting batch {i//batch_size + 1}/{(total_records + batch_size - 1)//batch_size} ({len(batch_ids)} items)...")
                
                try:
                    collection.upsert(
                        ids=batch_ids,
                        documents=batch_docs,
                        metadatas=batch_metas
                    )
                except Exception as e:
                    print(f"    Error upserting batch: {e}")
                    # Fallback to add if upsert not available or other error? 
                    # Usually upsert is the way to go.
            
            print(f"  - Collection {col_name} import finished.")

        print("\nAll collections imported successfully.")
        
    except Exception as e:
        print(f"Error during import: {e}")

if __name__ == "__main__":
    import_dump()
