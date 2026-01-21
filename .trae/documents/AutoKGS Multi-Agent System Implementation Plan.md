# AutoKGS Agent System Implementation Plan

## 1. Infrastructure & Configuration

* [ ] Update `agent_engine/config.py` to include `KIMI_API_KEY` and `KIMI_API_BASE`.

* [ ] Update `.env` template to include `KIMI_API_KEY`.

## 2. Tool Development

* [ ] **Kimi LLM Client**: Implement `agent_engine/tools/kimi_llm.py` to interact with Moonshot AI API.

* [ ] **Arxiv Search Tool**: Implement `agent_engine/tools/search_arxiv.py` using `arxiv` python package (need to add to requirements).

* [ ] **Wikipedia Search Tool**: Implement `agent_engine/tools/search_wikipedia.py` using `wikipedia` python package (need to add to requirements).

## 3. Agent Implementation

Create `agent_engine/agents/` directory and implement the following agents based on provided prompts:

* [ ] **Planner Agent**: `agents/planner.py` (Uses `ecnu-plus`).

* [ ] **Miner Agent**: `agents/miner.py` (Uses `ecnu-plus`, calls RAG tool).

* [ ] **Query Agent**: `agents/query.py` (Uses `ecnu-plus`).

* [ ] **Miner Online Agent**: `agents/miner_online.py` (Uses **Kimi**, calls Arxiv/Wiki tools).

* [ ] **Validator Agent**: `agents/validator.py` (Uses `ecnu-plus`).

* [ ] **Relation Agent**: `agents/relation.py` (Uses `ecnu-plus`).

## 4. Workflow Orchestration

* [ ] Implement `agent_engine/workflow.py` to chain the agents:

  1. **Planner**: User Input -> Keywords & Subjects.
  2. **RAG Search**: Keywords + Subjects -> Chunks.
  3. **Miner**: Chunks -> Initial Node List.
  4. **Query**: Check if results are sufficient.
  5. **Miner Online (Conditional)**: If Query=Yes, search Arxiv/Wiki -> Additional/Refined Nodes.
  6. **Validator**: Score all nodes -> Add `confidence` score.
  7. **ID Assignment**: Assign UUIDs to nodes.
  8. **Relation**: Analyze pairs of nodes -> Generate Links.
  9. **Link ID Assignment**: Map Links to Node IDs.
  10. **Final Output**: Graph JSON.

## 5. Main Integration

* [ ] Update `agent_engine/worker_main.py` to listen to Redis tasks and execute the workflow.

* [ ] Implement result writing to Neo4j.

