export type Evidence = {
  title: string;
  snippet: string;
  url?: string | null;
  domain?: string | null;
};

export type Node = {
  id: string;
  name: string;
  domain: string;
  definition?: string | null;
  confidence: number;
};

export type Edge = {
  id?: string | null;
  source: string;
  target: string;
  relation: "related_to" | "used_in" | "is_a" | "explains" | "bridges";
  explanation: string;
  evidence: Evidence;
  confidence: number;
  checked: boolean;
  check_reason?: string | null;
  flags?: string[];
};

export type GraphResult = {
  concept: string;
  nodes: Node[];
  edges: Edge[];
  meta: {
    generated_at: string;
    version: string;
    checker_summary: { passed: number; failed: number };
    agent_trace?: {
      domains?: Record<string, string[]>;
      passages_by_domain?: Record<
        string,
        { source?: string; domain?: string; title: string; snippet: string; url?: string | null }[]
      >;
    } | null;
  };
};

export type JobStatus = {
  job_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  concept: string;
  message?: string | null;
  logs: string[];
  result?: GraphResult | null;
  created_at: string;
  updated_at: string;
};

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers || {})
    }
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function generateGraph(params: {
  concept: string;
  domains?: string[];
  depth?: number;
  strict_check?: boolean;
}): Promise<{ job_id: string }> {
  return await jsonFetch("/api/graph/generate", {
    method: "POST",
    body: JSON.stringify({
      concept: params.concept,
      domains: params.domains,
      depth: params.depth ?? 2,
      strict_check: params.strict_check ?? true
    })
  });
}

export async function getJob(jobId: string): Promise<JobStatus> {
  return await jsonFetch(`/api/job/${encodeURIComponent(jobId)}`);
}

export async function getGraph(concept: string, depth = 2): Promise<GraphResult> {
  return await jsonFetch(`/api/graph/${encodeURIComponent(concept)}?depth=${depth}&version=v1`);
}

export async function expandNode(nodeId: string, depthIncrement = 1): Promise<GraphResult> {
  return await jsonFetch("/api/graph/expand", {
    method: "POST",
    body: JSON.stringify({ node_id: nodeId, depth_increment: depthIncrement })
  });
}

