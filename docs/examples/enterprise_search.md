# Example: Enterprise Search Across Internal Systems

This guide builds a unified enterprise search agent that lets employees ask natural-language questions and get accurate answers pulled from across the company's scattered knowledge — Confluence, Google Drive, Slack, Notion, Zendesk, and internal databases — with full source attribution and permission-aware access control.

---

## What We're Building

```
Employee Query: "What's our current parental leave policy and who approved the last update?"
                              │
                              ▼
                  Enterprise Search Agent
        ┌─────────────┬──────────────┬─────────────┬─────────────┐
        ▼             ▼              ▼             ▼             ▼
   Confluence    Google Drive      Notion        Slack       SQL (HRIS)
   (HR space)    (policy docs)   (wiki)        (#hr channel) (approval log)
        │             │              │             │             │
        └─────────────┴──────────────┴─────────────┴─────────────┘
                              │
                    Permission-Filtered, Reranked Results
                              │
                              ▼
                  Synthesized Answer + Citations
```

**Capabilities:**
- Search across 5+ disconnected internal systems with one query
- Respect per-user access permissions (no data leakage across departments)
- Cite exact source documents with deep links back to the original system
- Distinguish between current and outdated/superseded documents
- Handle queries that span multiple systems (e.g., "policy" in Confluence + "approval" in HRIS database)

---

## Prerequisites

```bash
pip install neuralcore[all]
export NEURALCORE_API_KEY=nck_live_...
export OPENAI_API_KEY=sk-proj-...
export CONFLUENCE_API_TOKEN=...
export NOTION_TOKEN=...
export SLACK_BOT_TOKEN=xoxb-...
export ZENDESK_API_TOKEN=...
```

---

## Step 1 — Architecture Decision: One KB or Many?

For enterprise search, NeuralCore supports two patterns. We use **separate knowledge bases per source system**, unified at query time — this preserves per-system metadata richness and lets us apply different refresh schedules and permission models per source.

```python
from neuralcore import NeuralCoreClient

client = NeuralCoreClient()

project = client.projects.create(
    name="Enterprise Search",
    description="Unified search across all internal knowledge systems",
    settings={"default_model": "gpt-4o", "cost_budget_usd_monthly": 800.0},
)
PROJECT_ID = project.id

# One KB per source system
kb_confluence = client.knowledge_bases.create(
    name="Confluence — All Spaces",
    project_id=PROJECT_ID,
    embedding={"provider": "openai", "model": "text-embedding-3-large", "dimensions": 1536},
    chunking={"strategy": "markdown", "chunk_size": 512, "chunk_overlap": 64},
)

kb_drive = client.knowledge_bases.create(
    name="Google Drive — Policy Docs",
    project_id=PROJECT_ID,
    embedding={"provider": "openai", "model": "text-embedding-3-large", "dimensions": 1536},
    chunking={"strategy": "semantic", "chunk_size": 512, "chunk_overlap": 64},
)

kb_notion = client.knowledge_bases.create(
    name="Notion — Engineering Wiki",
    project_id=PROJECT_ID,
    embedding={"provider": "openai", "model": "text-embedding-3-large", "dimensions": 1536},
    chunking={"strategy": "markdown", "chunk_size": 512, "chunk_overlap": 64},
)

kb_slack = client.knowledge_bases.create(
    name="Slack — Key Channels",
    project_id=PROJECT_ID,
    embedding={"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
    chunking={"strategy": "fixed", "chunk_size": 256, "chunk_overlap": 32},
)

kb_zendesk = client.knowledge_bases.create(
    name="Zendesk — Internal Help Center",
    project_id=PROJECT_ID,
    embedding={"provider": "openai", "model": "text-embedding-3-large", "dimensions": 1536},
    chunking={"strategy": "semantic", "chunk_size": 512, "chunk_overlap": 64},
)

KB_IDS = {
    "confluence": kb_confluence.id,
    "drive": kb_drive.id,
    "notion": kb_notion.id,
    "slack": kb_slack.id,
    "zendesk": kb_zendesk.id,
}
print(KB_IDS)
```

---

## Step 2 — Connect & Ingest Each Source

### 2.1 Confluence

```python
job = client.knowledge_bases.documents.from_connector(
    kb_id=KB_IDS["confluence"],
    connector="confluence",
    config={
        "base_url": "https://yourorg.atlassian.net/wiki",
        "username": "search-bot@yourorg.com",
        "api_token": os.getenv("CONFLUENCE_API_TOKEN"),
        "spaces": ["HR", "ENG", "PRODUCT", "LEGAL", "FINANCE"],
        "include_page_types": ["page"],
        "exclude_labels": ["draft", "archived", "deprecated"],
        "metadata_extraction": {
            "include_space": True,
            "include_last_editor": True,
            "include_labels": True,
            "include_permissions": True,   # Critical for access control
        },
        "refresh_interval_hours": 6,
    },
)
print(f"Confluence ingestion: {job.ingestion_job_id}")
```

### 2.2 Google Drive

```python
job = client.knowledge_bases.documents.from_connector(
    kb_id=KB_IDS["drive"],
    connector="google_drive",
    config={
        "service_account_json": os.getenv("GOOGLE_SERVICE_ACCOUNT"),
        "folder_ids": [
            "1A2b3C4d5E6f_HRPolicies",
            "1X9y8Z7w6V5u_LegalDocs",
            "1M3n4O5p6Q7r_FinancePolicies",
        ],
        "file_types": [
            "application/vnd.google-apps.document",
            "application/pdf",
        ],
        "recursive": True,
        "metadata_extraction": {
            "include_owner": True,
            "include_shared_with": True,   # For permission filtering
            "include_modified_date": True,
        },
        "refresh_interval_hours": 12,
    },
)
```

### 2.3 Notion

```python
job = client.knowledge_bases.documents.from_connector(
    kb_id=KB_IDS["notion"],
    connector="notion",
    config={
        "integration_token": os.getenv("NOTION_TOKEN"),
        "database_ids": ["eng-wiki-db-id", "architecture-decisions-db-id"],
        "include_child_pages": True,
        "metadata_extraction": {
            "include_author": True,
            "include_tags": True,
        },
        "refresh_interval_hours": 12,
    },
)
```

### 2.4 Slack (Key Channels Only)

Slack is high-volume and low-signal — only ingest curated channels, and only pinned/high-reaction messages plus full threads in dedicated knowledge channels:

```python
job = client.knowledge_bases.documents.from_connector(
    kb_id=KB_IDS["slack"],
    connector="slack",
    config={
        "bot_token": os.getenv("SLACK_BOT_TOKEN"),
        "channels": ["hr-policies", "eng-architecture-decisions", "it-helpdesk"],
        "include_threads": True,
        "min_reactions": 3,           # Only index messages with 3+ reactions, OR
        "pinned_only_channels": ["general-announcements"],
        "exclude_bot_messages": True,
        "lookback_days": 365,
        "refresh_interval_hours": 6,
    },
)
```

### 2.5 Zendesk (Internal Help Center)

```python
job = client.knowledge_bases.documents.from_connector(
    kb_id=KB_IDS["zendesk"],
    connector="zendesk",
    config={
        "subdomain": "yourcompany-internal",
        "email": "search-bot@yourorg.com",
        "api_token": os.getenv("ZENDESK_API_TOKEN"),
        "sources": ["help_center_articles"],
        "help_center": {
            "locales": ["en-US"],
            "published_only": True,
        },
        "refresh_interval_hours": 24,
    },
)
```

### 2.6 Wait for All Ingestion Jobs

```python
from neuralcore.ingestion_jobs import wait_all

job_ids = [job.ingestion_job_id for job in [
    # collect all job objects from above
]]
results = wait_all(client, job_ids, timeout=1800)  # 30 minutes for full sync

for r in results:
    print(f"{r.source}: {r.status} — {r.result.chunks_created if r.result else 0} chunks")
```

---

## Step 3 — Permission-Aware Retrieval

This is the most critical design decision in enterprise search: **users must only see results they're authorized to see.** NeuralCore enforces this via metadata-based access control filters applied at query time, not after.

### 3.1 Permission Metadata Schema

Every ingested document carries a `acl` (access control list) field in its metadata:

```json
{
  "metadata": {
    "acl": {
      "visibility": "department",
      "allowed_groups": ["hr", "people-ops", "leadership"],
      "allowed_users": [],
      "denied_users": []
    },
    "source_system": "confluence",
    "space": "HR"
  }
}
```

### 3.2 Building the Permission Filter at Query Time

```python
def build_acl_filter(user_id: str, user_groups: list[str]) -> dict:
    """Construct a metadata filter that only matches documents this user can see."""
    return {
        "or": [
            {"metadata": {"acl.visibility": "public"}},
            {"metadata": {"acl.allowed_users": {"contains": user_id}}},
            {"metadata": {"acl.allowed_groups": {"intersects": user_groups}}},
        ],
        "not": {
            "metadata": {"acl.denied_users": {"contains": user_id}}
        }
    }

def get_user_groups(user_id: str) -> list[str]:
    """Fetch the user's group memberships from your identity provider."""
    # In production: query your IdP (Okta, Azure AD, etc.)
    # This example uses a mock lookup
    return identity_provider.get_groups(user_id)
```

### 3.3 Multi-KB Retrieval with Permissions

```python
def enterprise_search(query: str, user_id: str) -> dict:
    user_groups = get_user_groups(user_id)
    acl_filter = build_acl_filter(user_id, user_groups)

    results = client.retrieve_multi(
        query=query,
        knowledge_bases=[
            {"id": KB_IDS["confluence"], "weight": 1.0, "top_k": 6, "filters": acl_filter},
            {"id": KB_IDS["drive"], "weight": 1.0, "top_k": 6, "filters": acl_filter},
            {"id": KB_IDS["notion"], "weight": 0.9, "top_k": 5, "filters": acl_filter},
            {"id": KB_IDS["slack"], "weight": 0.6, "top_k": 4, "filters": acl_filter},
            {"id": KB_IDS["zendesk"], "weight": 0.8, "top_k": 5, "filters": acl_filter},
        ],
        merge_strategy="weighted_rrf",
        final_top_k=10,
        reranking={"enabled": True, "model": "BAAI/bge-reranker-large"},
    )
    return results
```

---

## Step 4 — Create the Search Agent

```python
SYSTEM_PROMPT = """
You are the Acme Corp Enterprise Search Assistant. You help employees find 
accurate information from across all internal knowledge systems: Confluence, 
Google Drive, Notion, Slack, and the internal help center.

Core principles:
1. ONLY answer based on retrieved documents — never use outside knowledge for 
   company-specific facts (policies, processes, org structure, etc.)
2. ALWAYS cite your sources with [Source: Document Title, System] format
3. If multiple sources conflict, point out the conflict and note which is 
   more recent or authoritative
4. If you cannot find relevant information, say so clearly — do not guess
5. Distinguish between current policy and historical/superseded versions when 
   the metadata indicates an update history
6. Respect that some answers may be incomplete because the user doesn't have 
   access to all relevant documents — don't claim something "doesn't exist" 
   when it might just be access-restricted

Source attribution format:
"According to [Document Title] (last updated: [date], via [Confluence/Drive/etc.]), ..."

When information might be sensitive (HR, legal, compensation):
- Be precise and avoid editorializing
- Recommend the user verify with the relevant department for final decisions
- Note if a document appears to be more than 6 months old, as policies may have changed
"""

agent = client.agents.create(
    name="Enterprise Search Assistant",
    project_id=PROJECT_ID,
    type="rag",
    model={
        "provider": "openai",
        "model_name": "gpt-4o",
        "temperature": 0.0,
        "max_tokens": 1500,
    },
    system_prompt=SYSTEM_PROMPT,
    tools=["kb_retrieval"],
    # Note: actual retrieval is done via enterprise_search() with ACL filtering,
    # then injected as context — see Step 5 for the full integration pattern
    memory={
        "enabled": True,
        "type": "episodic",
        "episodic": {"session_ttl_hours": 4, "inject_last_n_turns": 6},
    },
    guardrails={
        "max_iterations": 4,
        "max_tokens_per_run": 8000,
        "max_cost_per_run_usd": 0.08,
        "timeout_seconds": 45,
        "content_filters": {
            "output": ["pii_redaction"],
        },
    },
)

AGENT_ID = agent.id
```

---

## Step 5 — Full Integration: Permission-Filtered RAG

Since native agent retrieval doesn't know about per-request ACL filters, we manually retrieve with permissions applied, then inject the results as context for the agent run:

```python
def search_with_permissions(query: str, user_id: str, session_id: str) -> dict:
    # Step 1: Permission-filtered retrieval across all KBs
    retrieval_results = enterprise_search(query, user_id)

    if not retrieval_results.results:
        return {
            "output": "I couldn't find any relevant information you have access to. "
                      "You may want to check with the relevant department directly, "
                      "or this content may require additional permissions.",
            "sources": [],
        }

    # Step 2: Format retrieved context for the agent
    context_block = "\n\n".join([
        f"[Document {i+1}: {r.document_title} (System: {r.metadata.get('source_system')}, "
        f"Last updated: {r.metadata.get('modified_date', 'unknown')})]\n{r.text}"
        for i, r in enumerate(retrieval_results.results)
    ])

    # Step 3: Run the agent with the pre-retrieved, permission-safe context
    result = client.agents.run(
        agent_id=AGENT_ID,
        input=f"""
Retrieved context (already permission-filtered for this user):

{context_block}

User question: {query}
""",
        session_id=session_id,
        user_id=user_id,
        context={"retrieval_method": "manual_acl_filtered"},
    )

    return {
        "output": result.output,
        "sources": [
            {
                "title": r.document_title,
                "system": r.metadata.get("source_system"),
                "url": r.metadata.get("source_url"),
                "score": r.final_score,
            }
            for r in retrieval_results.results
        ],
        "cost_usd": result.cost_usd,
    }
```

---

## Step 6 — Example Queries

```python
# Cross-system query
result = search_with_permissions(
    query="What is our current parental leave policy?",
    user_id="emp_alice_123",
    session_id="session_alice_001",
)
print(result["output"])
for s in result["sources"]:
    print(f"  - {s['title']} ({s['system']}) — {s['url']}")
```

**Example response:**
```
According to "Parental Leave Policy 2026" (last updated: 2026-03-15, via Confluence), 
Acme Corp provides 16 weeks of fully paid parental leave for all employees, 
regardless of gender, for births, adoptions, or fostering [Source: Parental Leave 
Policy 2026, Confluence].

This was confirmed in a related discussion [Source: #hr-policies Slack thread, 
2026-03-16] where People Ops noted the policy update took effect for all leave 
requests starting April 1, 2026.

Sources:
  - Parental Leave Policy 2026 (confluence) — https://yourorg.atlassian.net/wiki/...
  - #hr-policies thread (slack) — https://yourorg.slack.com/archives/...
```

```python
# Query restricted by access control
result = search_with_permissions(
    query="What was discussed in the executive compensation committee meeting?",
    user_id="emp_bob_456",  # Bob is not in the "leadership" group
    session_id="session_bob_001",
)
# Returns: "I couldn't find any relevant information you have access to..."
# because the documents have acl.allowed_groups: ["leadership", "board"]
# and Bob's groups don't intersect
```

---

## Step 7 — Web Search Frontend

```python
from fastapi import FastAPI, Header
from pydantic import BaseModel

app = FastAPI(title="Enterprise Search API")

class SearchRequest(BaseModel):
    query: str
    session_id: str | None = None

@app.post("/search")
async def search(req: SearchRequest, x_user_id: str = Header(..., alias="X-User-ID")):
    session_id = req.session_id or f"session_{x_user_id}_{uuid.uuid4().hex[:8]}"
    result = search_with_permissions(req.query, x_user_id, session_id)
    return result
```

```jsx
// Minimal React search UI
function EnterpriseSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    setLoading(true);
    const res = await fetch("/search", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-ID": currentUser.id },
      body: JSON.stringify({ query }),
    });
    setResults(await res.json());
    setLoading(false);
  };

  return (
    <div className="search-container">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && search()}
        placeholder="Ask anything about company policies, processes, or docs..."
      />
      <button onClick={search} disabled={loading}>
        {loading ? "Searching..." : "Search"}
      </button>
      {results && (
        <div className="results">
          <p>{results.output}</p>
          <div className="sources">
            {results.sources.map((s, i) => (
              <a key={i} href={s.url} target="_blank" rel="noreferrer">
                {s.title} ({s.system})
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## Step 8 — Quality & Freshness Monitoring

### Staleness Detection

```python
import datetime

def flag_stale_results(results: list, max_age_days: int = 180) -> list:
    """Flag results that may be outdated."""
    now = datetime.datetime.utcnow()
    for r in results:
        modified = r.metadata.get("modified_date")
        if modified:
            age_days = (now - datetime.datetime.fromisoformat(modified)).days
            r.metadata["is_stale"] = age_days > max_age_days
            r.metadata["age_days"] = age_days
    return results
```

### Source Coverage Dashboard

Track which systems are contributing to answers — useful for identifying ingestion gaps:

```python
# Prometheus metrics to monitor
"""
enterprise_search_queries_total{source_system="confluence"}
enterprise_search_queries_total{source_system="drive"}
enterprise_search_zero_result_rate          # % of queries with no results (KB gap signal)
enterprise_search_acl_denied_rate           # % of results filtered out by ACL
enterprise_search_avg_sources_per_answer
enterprise_search_stale_result_rate         # % of citations older than 180 days
"""
```

### Continuous Quality Eval

```python
eval_queries = [
    {"query": "vacation policy", "expected_system": "confluence"},
    {"query": "how to expense a conference", "expected_system": "drive"},
    {"query": "engineering RFC process", "expected_system": "notion"},
]

for case in eval_queries:
    result = search_with_permissions(case["query"], "eval_user", "eval_session")
    systems_used = {s["system"] for s in result["sources"]}
    if case["expected_system"] not in systems_used:
        print(f"WARNING: '{case['query']}' didn't retrieve from {case['expected_system']}")
```

---

## Production Checklist

- [ ] ACL metadata correctly populated for every document at ingestion time
- [ ] Permission filter tested with users in different groups (no leakage)
- [ ] Refresh intervals tuned per source (Slack/Confluence change faster than legal docs)
- [ ] Staleness flagging enabled for policy-sensitive content
- [ ] Citation deep-links verified to resolve correctly for each source system
- [ ] Zero-result queries logged and reviewed weekly for KB gaps
- [ ] Cost monitoring per department (if charging back internally)
- [ ] Audit log enabled — who searched what, when (compliance requirement in regulated industries)

---

*Full source code: [github.com/neuralcore-ai/examples/tree/main/enterprise-search](https://github.com/neuralcore-ai/examples/tree/main/enterprise-search)*
