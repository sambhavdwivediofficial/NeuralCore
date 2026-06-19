# Agents

NeuralCore's agent system provides a production-grade framework for building, deploying, and orchestrating autonomous AI agents that can reason, plan, use tools, maintain memory, and collaborate in multi-agent pipelines. This document covers every layer of the agent system — from the conceptual model to runtime internals, configuration, deployment, and operational best practices.

---

## 1. Conceptual Overview

An **agent** in NeuralCore is a stateful, goal-directed computational entity that wraps a Large Language Model (LLM) with:

- A **system prompt** defining its persona, constraints, and capabilities
- A set of **tools** it can invoke (APIs, code interpreters, databases, retrieval systems)
- A **memory system** that persists context across runs and sessions
- A **knowledge base** it can query for domain-specific grounding
- An **execution runtime** that handles the LLM ↔ tool ↔ memory loop

Unlike simple LLM wrappers, NeuralCore agents are **production entities** — they have persistent identity, version-controlled configurations, audit trails, rate limits, cost budgets, and lifecycle management.

### The ReAct Loop

All NeuralCore agents execute using a variant of the **ReAct** (Reason + Act) paradigm:

```
┌─────────────────────────────────────────────────────┐
│                     Agent Run                       │
│                                                     │
│  Input → [Think] → [Act / Tool Call] → [Observe]   │
│               ↑                              │      │
│               └──────────────────────────────┘      │
│                    (loop until done)                │
│                         ↓                           │
│                    Final Response                   │
└─────────────────────────────────────────────────────┘
```

Each iteration:
1. **Think** — The LLM receives the conversation history, tool results, and memory context, then reasons about what to do next
2. **Act** — The LLM either calls a tool, queries the knowledge base, or produces a final answer
3. **Observe** — Tool results are appended to the context and the loop continues

The loop terminates when the LLM produces a `FINAL_ANSWER` or the maximum iteration limit is reached.

---

## 2. Agent Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         NeuralCore Agent                             │
│                                                                      │
│  ┌──────────────────┐    ┌───────────────────┐   ┌────────────────┐ │
│  │   Agent Config   │    │  Execution Engine  │   │  Agent State   │ │
│  │  - ID / version  │    │  - ReAct loop      │   │  - run_id      │ │
│  │  - system prompt │    │  - tool dispatch   │   │  - step_count  │ │
│  │  - model config  │───▶│  - memory inject   │──▶│  - tool_calls  │ │
│  │  - tool list     │    │  - streaming       │   │  - token_usage │ │
│  │  - memory config │    │  - error handling  │   │  - cost        │ │
│  │  - guardrails    │    └────────┬──────────┘   └────────────────┘ │
│  └──────────────────┘             │                                  │
│                                   │                                  │
│         ┌─────────────────────────┼──────────────────────────┐      │
│         ▼                         ▼                          ▼       │
│  ┌─────────────┐        ┌──────────────────┐      ┌──────────────┐  │
│  │  LLM Router │        │   Tool Registry   │      │ Memory Store │  │
│  │  (OpenAI /  │        │  - web_search     │      │  - episodic  │  │
│  │  Anthropic/ │        │  - code_executor  │      │  - semantic  │  │
│  │  Cohere/    │        │  - kb_retrieval   │      │  - working   │  │
│  │  local)     │        │  - http_request   │      │  - long-term │  │
│  └─────────────┘        │  - sql_query      │      └──────────────┘  │
│                         │  - custom tools   │                        │
│                         └──────────────────┘                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility |
|-----------|---------------|
| **Agent Config** | Immutable definition — system prompt, model, tools, limits |
| **Execution Engine** | Stateful runtime that drives the ReAct loop per run |
| **LLM Router** | Selects and invokes the appropriate model provider |
| **Tool Registry** | Manages available tools, their schemas, and dispatch |
| **Memory Store** | Persists and retrieves agent memory across sessions |
| **Agent State** | Ephemeral per-run state (steps, costs, outputs) |

---

## 3. Agent Types

NeuralCore ships with four built-in agent architectures, each optimized for different use cases:

### 3.1 ReAct Agent (Default)

The standard single-agent executor. Uses the ReAct loop with tool calling and optional memory injection. Best for most general-purpose tasks.

```json
{
  "type": "react",
  "max_iterations": 10,
  "early_stopping": true
}
```

**Use when:** You need a capable, general-purpose assistant with tool access.

### 3.2 RAG Agent

A ReAct agent with a tightly integrated knowledge base. Before every LLM call, relevant documents are retrieved and injected into the context window. Designed for document-heavy tasks.

```json
{
  "type": "rag",
  "knowledge_base_id": "kb_abc123",
  "retrieval_strategy": "hybrid",
  "top_k": 8,
  "reranking": true
}
```

**Use when:** The agent needs to answer questions from a large document corpus.

### 3.3 Plan-and-Execute Agent

A two-phase agent: first it generates a complete multi-step plan, then executes each step sequentially. More reliable for complex multi-step tasks but less adaptive than pure ReAct.

```json
{
  "type": "plan_and_execute",
  "planner_model": "gpt-4o",
  "executor_model": "gpt-4o-mini",
  "max_plan_steps": 20
}
```

**Use when:** Tasks are complex, predictable, and benefit from upfront planning (data pipelines, report generation).

### 3.4 Multi-Agent (Supervisor)

An orchestrator agent that delegates subtasks to specialized sub-agents. Each sub-agent is itself a full NeuralCore agent with its own tools and memory. The supervisor synthesizes sub-agent outputs into a final response.

```json
{
  "type": "supervisor",
  "sub_agents": ["agent_id_researcher", "agent_id_writer", "agent_id_critic"],
  "routing_strategy": "llm",
  "aggregation": "synthesize"
}
```

**Use when:** Tasks require parallel specialization — e.g., research + writing + code review running concurrently.

---

## 4. Creating an Agent

### 4.1 Via the API

```bash
POST /api/v1/agents
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Customer Support Agent",
  "description": "Handles Tier-1 customer inquiries using internal KB and CRM",
  "project_id": "proj_abc123",
  "type": "rag",
  "model": {
    "provider": "openai",
    "model_name": "gpt-4o",
    "temperature": 0.1,
    "max_tokens": 2048,
    "top_p": 1.0
  },
  "system_prompt": "You are a helpful customer support agent for Acme Corp...",
  "tools": ["kb_retrieval", "http_request", "sql_query"],
  "knowledge_base_id": "kb_xyz789",
  "memory": {
    "enabled": true,
    "type": "hybrid",
    "max_tokens": 4000,
    "summarize_after": 20
  },
  "guardrails": {
    "max_iterations": 8,
    "max_tokens_per_run": 16000,
    "max_cost_per_run_usd": 0.10,
    "timeout_seconds": 120,
    "content_filters": ["pii", "profanity"]
  },
  "metadata": {
    "team": "support",
    "tier": "production"
  }
}
```

**Response:**

```json
{
  "id": "agent_9f3kd82",
  "name": "Customer Support Agent",
  "status": "active",
  "version": 1,
  "created_at": "2026-06-18T10:00:00Z",
  "project_id": "proj_abc123",
  "type": "rag",
  "model": { ... },
  "tools": ["kb_retrieval", "http_request", "sql_query"],
  "knowledge_base_id": "kb_xyz789"
}
```

### 4.2 Via Python SDK

```python
from neuralcore import NeuralCoreClient
from neuralcore.agents import AgentConfig, ModelConfig, MemoryConfig, GuardrailsConfig

client = NeuralCoreClient(api_key="nck_...")

agent = client.agents.create(
    name="Customer Support Agent",
    project_id="proj_abc123",
    type="rag",
    model=ModelConfig(
        provider="openai",
        model_name="gpt-4o",
        temperature=0.1,
        max_tokens=2048,
    ),
    system_prompt="""
        You are a helpful customer support agent for Acme Corp.
        Always be polite, concise, and accurate.
        If you cannot find the answer in the knowledge base, say so clearly.
        Never fabricate information or make up policies.
    """,
    tools=["kb_retrieval", "http_request"],
    knowledge_base_id="kb_xyz789",
    memory=MemoryConfig(enabled=True, type="hybrid", max_tokens=4000),
    guardrails=GuardrailsConfig(
        max_iterations=8,
        max_cost_per_run_usd=0.10,
        content_filters=["pii"],
    ),
)

print(f"Created agent: {agent.id}")
```

### 4.3 Running an Agent

```python
# Synchronous run
result = client.agents.run(
    agent_id="agent_9f3kd82",
    input="What is your return policy for electronics?",
    session_id="session_user123",     # for memory continuity
    user_id="user_456",
    metadata={"channel": "web_chat"},
)

print(result.output)
print(f"Steps: {result.steps_taken}")
print(f"Tokens used: {result.token_usage.total}")
print(f"Cost: ${result.cost_usd:.4f}")
```

```python
# Streaming run
for chunk in client.agents.stream(
    agent_id="agent_9f3kd82",
    input="Summarize our refund policy and compare it to industry standards",
    session_id="session_user123",
):
    if chunk.type == "token":
        print(chunk.content, end="", flush=True)
    elif chunk.type == "tool_call":
        print(f"\n[Tool: {chunk.tool_name}({chunk.tool_input})]")
    elif chunk.type == "tool_result":
        print(f"[Result: {chunk.result[:100]}...]")
    elif chunk.type == "done":
        print(f"\n\nCompleted in {chunk.steps_taken} steps.")
```

---

## 5. Tools & Tool Calling

Tools are functions that the agent LLM can invoke. NeuralCore uses OpenAI-compatible function calling format under the hood.

### 5.1 Built-in Tools

| Tool Name | Description | Key Parameters |
|-----------|-------------|----------------|
| `kb_retrieval` | Query a knowledge base using semantic/hybrid search | `knowledge_base_id`, `query`, `top_k`, `strategy` |
| `web_search` | Search the web using Bing/Google/Brave APIs | `query`, `num_results`, `safe_search` |
| `code_executor` | Execute Python/JavaScript code in a sandboxed environment | `code`, `language`, `timeout` |
| `http_request` | Make arbitrary HTTP requests to external APIs | `url`, `method`, `headers`, `body` |
| `sql_query` | Execute read-only SQL against a connected database | `connection_id`, `query`, `max_rows` |
| `file_reader` | Read files from connected storage (S3, GCS, local) | `path`, `encoding` |
| `calculator` | Perform precise mathematical computations | `expression` |
| `datetime` | Get current time, compute date deltas | `operation`, `timezone` |

### 5.2 Custom Tools

Register custom tools that the agent can call as if they were built-in:

```python
from neuralcore.tools import tool, ToolSchema

@tool(
    name="crm_lookup",
    description="Look up a customer record in Salesforce CRM by email or customer ID",
    schema=ToolSchema(
        properties={
            "identifier": {
                "type": "string",
                "description": "Customer email address or Salesforce Account ID"
            },
            "fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields to return (e.g. ['name', 'mrr', 'plan'])"
            }
        },
        required=["identifier"]
    )
)
async def crm_lookup(identifier: str, fields: list[str] | None = None) -> dict:
    """Fetch customer data from Salesforce."""
    async with SalesforceClient() as sf:
        record = await sf.query_by_identifier(identifier, fields=fields)
    return {
        "found": record is not None,
        "data": record.to_dict() if record else None
    }

# Register with agent
client.agents.register_tool("agent_9f3kd82", crm_lookup)
```

### 5.3 Tool Schemas via API

```bash
POST /api/v1/agents/{agent_id}/tools
{
  "name": "crm_lookup",
  "description": "Look up a customer in CRM by email or ID",
  "type": "http_webhook",
  "webhook_url": "https://your-service.com/tools/crm_lookup",
  "auth": {
    "type": "bearer",
    "token": "{{env.CRM_WEBHOOK_TOKEN}}"
  },
  "schema": {
    "type": "object",
    "properties": {
      "identifier": {"type": "string"},
      "fields": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["identifier"]
  },
  "timeout_seconds": 10,
  "retry_on_failure": true,
  "max_retries": 2
}
```

### 5.4 Tool Execution Flow

```
LLM Output (JSON function call)
         │
         ▼
  Tool Dispatcher
    ├── Validate schema against tool definition
    ├── Check tool permissions for agent
    ├── Apply rate limits (per tool, per run)
    ├── Execute tool (built-in or webhook)
    ├── Capture result + latency + errors
    └── Append result to conversation context
         │
         ▼
  Next LLM Iteration
```

---

## 6. Memory & Context Management

NeuralCore implements a four-layer memory architecture:

### 6.1 Memory Types

| Type | Scope | Storage | Description |
|------|-------|---------|-------------|
| **Working Memory** | Current run | RAM | Active conversation messages for this run |
| **Episodic Memory** | Session | Redis + PostgreSQL | Recent interactions within a user session |
| **Semantic Memory** | Persistent | Qdrant | Long-term facts and summaries stored as embeddings |
| **Long-term Memory** | Persistent | PostgreSQL | Structured facts, preferences, extracted entities |

### 6.2 Memory Configuration

```json
{
  "memory": {
    "enabled": true,
    "type": "hybrid",
    "working_memory": {
      "max_messages": 50,
      "max_tokens": 8000
    },
    "episodic_memory": {
      "enabled": true,
      "session_ttl_hours": 24,
      "max_episodes": 100
    },
    "semantic_memory": {
      "enabled": true,
      "embedding_model": "text-embedding-3-large",
      "top_k": 5,
      "similarity_threshold": 0.75,
      "max_tokens_injected": 2000
    },
    "long_term_memory": {
      "enabled": true,
      "auto_extract": true,
      "extract_entities": ["person", "organization", "product", "preference"]
    },
    "summarize_after": 30,
    "summarization_model": "gpt-4o-mini"
  }
}
```

### 6.3 Memory Injection

Before each LLM call, memory is injected into the system prompt in this order:

```
[SYSTEM PROMPT]

--- RELEVANT MEMORY ---
[Semantic search results: top-K similar past interactions]
[Long-term facts about this user/entity]

--- RECENT CONTEXT ---
[Last N messages from episodic memory]
--- END MEMORY ---

[CURRENT CONVERSATION]
```

### 6.4 Memory Management API

```python
# Read agent memory for a user
memories = client.agents.memory.list(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    memory_type="semantic",
    limit=20
)

# Inject a fact into long-term memory
client.agents.memory.store(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    fact="User prefers email communication over phone. Primary use case: e-commerce returns.",
    memory_type="long_term"
)

# Clear session memory
client.agents.memory.clear(
    agent_id="agent_9f3kd82",
    user_id="user_456",
    memory_type="episodic"
)
```

---

## 7. Retrieval-Augmented Generation (RAG) in Agents

When an agent is configured with a knowledge base, it can retrieve and cite relevant documents during execution.

### 7.1 RAG Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `semantic` | Pure vector similarity search | General Q&A |
| `keyword` | BM25 full-text search | Exact terminology matching |
| `hybrid` | Weighted combination of semantic + keyword | Production default |
| `reranking` | Hybrid + cross-encoder reranking | High-precision tasks |

### 7.2 Configuring RAG

```json
{
  "retrieval": {
    "knowledge_base_id": "kb_xyz789",
    "strategy": "hybrid",
    "top_k": 8,
    "reranking": {
      "enabled": true,
      "model": "cross-encoder/ms-marco-MiniLM-L-12-v2",
      "top_k_after_rerank": 4
    },
    "filters": {
      "metadata": {
        "document_type": ["policy", "faq"],
        "language": "en"
      }
    },
    "citation_mode": "inline",
    "min_similarity_score": 0.70
  }
}
```

### 7.3 Citations

When `citation_mode` is set, the agent automatically cites source documents:

```json
{
  "output": "Our return policy allows returns within 30 days [1]. Electronics are subject to a 15-day return window [2].",
  "citations": [
    {
      "ref": 1,
      "document_id": "doc_abc",
      "document_title": "General Return Policy",
      "chunk_id": "chunk_001",
      "similarity_score": 0.91,
      "text_excerpt": "Items may be returned within 30 days of purchase..."
    },
    {
      "ref": 2,
      "document_id": "doc_xyz",
      "document_title": "Electronics Return Policy",
      "chunk_id": "chunk_048",
      "similarity_score": 0.88,
      "text_excerpt": "Electronic devices must be returned within 15 days..."
    }
  ]
}
```

---

## 8. Multi-Agent Orchestration

### 8.1 Supervisor Pattern

```python
# Create specialized sub-agents
researcher = client.agents.create(
    name="Research Specialist",
    type="rag",
    tools=["web_search", "kb_retrieval"],
    system_prompt="You are a research specialist. Find comprehensive, accurate information...",
    knowledge_base_id="kb_research",
)

writer = client.agents.create(
    name="Content Writer",
    type="react",
    tools=["code_executor"],
    system_prompt="You are an expert technical writer. Transform research into clear documentation...",
)

critic = client.agents.create(
    name="Quality Critic",
    type="react",
    system_prompt="You are a quality assurance expert. Review content for accuracy, clarity, completeness...",
)

# Create supervisor
supervisor = client.agents.create(
    name="Documentation Orchestrator",
    type="supervisor",
    sub_agents=[researcher.id, writer.id, critic.id],
    routing_strategy="llm",
    system_prompt="""
        You are an orchestrator managing a team of specialist agents.
        For each documentation request:
        1. Send research tasks to the Research Specialist
        2. Send writing tasks to the Content Writer
        3. Send the draft to the Quality Critic for review
        4. Synthesize the final output
    """,
)
```

### 8.2 Parallel Execution

Sub-agents can be executed in parallel for independent tasks:

```json
{
  "type": "supervisor",
  "execution_mode": "parallel",
  "sub_agents": ["agent_id_1", "agent_id_2", "agent_id_3"],
  "max_parallel": 3,
  "aggregation": "synthesize"
}
```

### 8.3 Agent-to-Agent Communication

```
Supervisor
    │
    ├──▶ Researcher Agent  ──[results]──▶  Supervisor
    │                                          │
    ├──▶ Writer Agent  ◀──[research]───────────┤
    │         │                                │
    │         └──[draft]──▶ Critic Agent       │
    │                           │              │
    │                           └──[review]──▶ Supervisor
    │                                          │
    └──────────────────────────────────────────┘
                                │
                           Final Response
```

---

## 9. Agent Lifecycle & State Machine

```
         create()
             │
             ▼
         [draft]
             │
          activate()
             │
             ▼
         [active] ◀────────────────────────────┐
             │                                  │
          run()                              re-activate()
             │                                  │
             ▼                                  │
         [running]                         [paused]
             │                                  │
             ├── success ──▶ [idle] ────────────┘
             │
             ├── error ──▶ [failed]
             │                │
             │           retry() or debug
             │
             └── timeout ──▶ [timed_out]
             │
          deactivate()
             │
             ▼
         [inactive]
             │
          delete()
             │
             ▼
         [deleted]
```

### State Transitions

| From | Event | To | Side Effects |
|------|-------|-----|-------------|
| `draft` | `activate()` | `active` | Validates config, allocates resources |
| `active` | `run()` | `running` | Creates run record, starts execution |
| `running` | success | `idle` | Stores run result, updates metrics |
| `running` | error | `failed` | Logs error, triggers alerts if configured |
| `running` | timeout | `timed_out` | Releases resources, partial result saved |
| `active` | `deactivate()` | `inactive` | Flushes pending runs, releases memory |
| `inactive` | `delete()` | `deleted` | Soft-deletes, retains audit logs |

---

## 10. Streaming & Real-Time Execution

All agent runs support Server-Sent Events (SSE) streaming:

### 10.1 Stream Event Types

| Event Type | Payload | Description |
|------------|---------|-------------|
| `run.started` | `{run_id, agent_id, timestamp}` | Run has begun |
| `step.started` | `{step_number, type}` | New ReAct iteration started |
| `llm.token` | `{content}` | Streamed token from LLM |
| `tool.called` | `{tool_name, tool_input}` | LLM invoked a tool |
| `tool.result` | `{tool_name, result, latency_ms}` | Tool execution complete |
| `memory.retrieved` | `{count, tokens}` | Memory injection event |
| `retrieval.done` | `{doc_count, strategy}` | KB retrieval complete |
| `run.done` | `{output, steps, tokens, cost_usd}` | Final answer ready |
| `run.error` | `{error_code, message}` | Run failed |

### 10.2 Consuming the Stream (JavaScript)

```javascript
const eventSource = new EventSource(
  `https://api.neuralcore.ai/api/v1/agents/${agentId}/stream`,
  {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  }
);

eventSource.addEventListener('llm.token', (e) => {
  const { content } = JSON.parse(e.data);
  process.stdout.write(content);
});

eventSource.addEventListener('tool.called', (e) => {
  const { tool_name, tool_input } = JSON.parse(e.data);
  console.log(`\n[Calling tool: ${tool_name}]`, tool_input);
});

eventSource.addEventListener('run.done', (e) => {
  const { output, steps, cost_usd } = JSON.parse(e.data);
  console.log(`\nCompleted in ${steps} steps. Cost: $${cost_usd.toFixed(4)}`);
  eventSource.close();
});

eventSource.addEventListener('run.error', (e) => {
  console.error('Run failed:', JSON.parse(e.data));
  eventSource.close();
});
```

---

## 11. Guardrails & Safety

### 11.1 Built-in Guardrails

```json
{
  "guardrails": {
    "max_iterations": 10,
    "max_tokens_per_run": 32000,
    "max_cost_per_run_usd": 0.50,
    "timeout_seconds": 180,
    "max_tool_calls": 20,
    "content_filters": {
      "input": ["pii_detection", "prompt_injection", "jailbreak"],
      "output": ["pii_redaction", "profanity", "harmful_content"]
    },
    "topic_restrictions": {
      "deny": ["competitor_mentions", "legal_advice", "medical_diagnosis"],
      "allow_only": ["customer_support", "product_information"]
    },
    "tool_restrictions": {
      "deny_tools": ["code_executor"],
      "require_confirmation": ["http_request", "sql_query"]
    },
    "output_validation": {
      "schema": {
        "type": "object",
        "properties": {
          "answer": {"type": "string"},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    }
  }
}
```

### 11.2 PII Detection & Redaction

NeuralCore uses a Presidio-based PII detection pipeline. Detected entities are automatically redacted or flagged before being sent to the LLM or stored:

| Entity Type | Detection Method | Default Action |
|-------------|-----------------|---------------|
| Email | Regex + NER | Redact |
| Phone number | Regex | Redact |
| Credit card | Luhn + Regex | Block run |
| SSN / ID | Regex | Block run |
| Name | NER | Flag |
| Address | NER | Redact |

### 11.3 Prompt Injection Defense

Input sanitization pipeline:

1. **Structural analysis** — Detects injected instructions (`Ignore previous instructions...`)
2. **Role confusion detection** — Flags attempts to override system prompt
3. **Encoding attack detection** — Detects base64/unicode obfuscation
4. **Similarity scoring** — Flags inputs that closely match known attack patterns

---

## 12. Evaluation & Observability

### 12.1 Run Metrics

Every run produces a rich telemetry payload:

```json
{
  "run_id": "run_abc123",
  "agent_id": "agent_9f3kd82",
  "status": "success",
  "started_at": "2026-06-18T10:00:00Z",
  "ended_at": "2026-06-18T10:00:12.340Z",
  "latency_ms": 12340,
  "steps_taken": 4,
  "token_usage": {
    "prompt_tokens": 3412,
    "completion_tokens": 287,
    "total_tokens": 3699
  },
  "cost_usd": 0.0523,
  "tool_calls": [
    {"tool": "kb_retrieval", "latency_ms": 89, "success": true},
    {"tool": "http_request", "latency_ms": 234, "success": true}
  ],
  "memory_tokens_injected": 1024,
  "retrieval_docs_used": 6,
  "guardrails_triggered": []
}
```

### 12.2 Prometheus Metrics

NeuralCore exports the following agent metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `agent_runs_total` | Counter | Total runs by agent_id, status |
| `agent_run_duration_seconds` | Histogram | Run latency distribution |
| `agent_tokens_used_total` | Counter | Tokens by provider, model |
| `agent_cost_usd_total` | Counter | Cumulative cost by agent |
| `agent_tool_calls_total` | Counter | Tool invocations by tool name, status |
| `agent_guardrails_triggered_total` | Counter | Safety triggers by type |
| `agent_steps_per_run` | Histogram | ReAct iterations per run |

### 12.3 Tracing

Every run is fully traced using OpenTelemetry. Traces include:
- Full ReAct loop spans
- LLM call spans (with model, tokens, latency)
- Tool call spans (input, output, latency)
- Memory retrieval spans
- KB retrieval spans

Traces are exported to your configured OTLP endpoint (Jaeger, Tempo, Datadog, etc.).

---

## 13. API Reference

### Agents CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/agents` | Create agent |
| `GET` | `/api/v1/agents` | List agents (paginated, filterable) |
| `GET` | `/api/v1/agents/{id}` | Get agent details |
| `PATCH` | `/api/v1/agents/{id}` | Update agent config |
| `DELETE` | `/api/v1/agents/{id}` | Soft-delete agent |
| `POST` | `/api/v1/agents/{id}/activate` | Activate agent |
| `POST` | `/api/v1/agents/{id}/deactivate` | Deactivate agent |
| `POST` | `/api/v1/agents/{id}/clone` | Clone agent with new name |

### Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/agents/{id}/run` | Synchronous run |
| `GET` | `/api/v1/agents/{id}/stream` | SSE streaming run |
| `GET` | `/api/v1/agents/{id}/runs` | List past runs |
| `GET` | `/api/v1/agents/{id}/runs/{run_id}` | Get run details + steps |
| `POST` | `/api/v1/agents/{id}/runs/{run_id}/cancel` | Cancel active run |

### Memory

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents/{id}/memory` | List memory entries |
| `POST` | `/api/v1/agents/{id}/memory` | Inject memory |
| `DELETE` | `/api/v1/agents/{id}/memory` | Clear memory (by type/user) |

### Tools

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents/{id}/tools` | List agent tools |
| `POST` | `/api/v1/agents/{id}/tools` | Register custom tool |
| `DELETE` | `/api/v1/agents/{id}/tools/{tool_name}` | Remove tool |

---

## 14. Configuration Reference

### Agent Object Schema

```typescript
interface AgentConfig {
  // Identity
  name: string;                        // Display name (max 100 chars)
  description?: string;                // Optional description
  project_id: string;                  // Parent project
  tags?: string[];                     // Searchable tags

  // Execution
  type: "react" | "rag" | "plan_and_execute" | "supervisor";

  // Model
  model: {
    provider: "openai" | "anthropic" | "cohere" | "mistral" | "custom";
    model_name: string;                // e.g. "gpt-4o", "claude-3-5-sonnet-20241022"
    temperature: number;               // 0.0–2.0, default 0.1 for production
    max_tokens: number;                // Max completion tokens
    top_p?: number;                    // Nucleus sampling
    frequency_penalty?: number;
    presence_penalty?: number;
    seed?: number;                     // For deterministic outputs
  };

  // Prompt
  system_prompt: string;               // Main system prompt (max 32,000 chars)
  system_prompt_template?: string;     // Jinja2 template with variables

  // Tools
  tools: string[];                     // Built-in tool names
  custom_tools?: CustomToolDefinition[];

  // Knowledge
  knowledge_base_id?: string;          // Attached KB (for RAG agents)
  retrieval?: RetrievalConfig;

  // Memory
  memory?: MemoryConfig;

  // Safety
  guardrails: GuardrailsConfig;

  // Metadata
  metadata?: Record<string, string>;
}
```

---

## 15. Error Handling

### Error Codes

| Code | HTTP Status | Description | Resolution |
|------|-------------|-------------|-----------|
| `AGENT_NOT_FOUND` | 404 | Agent ID does not exist | Check agent ID |
| `AGENT_INACTIVE` | 409 | Agent is not in active state | Call `/activate` first |
| `RUN_TIMEOUT` | 408 | Run exceeded timeout limit | Increase timeout or reduce task complexity |
| `MAX_ITERATIONS_EXCEEDED` | 422 | ReAct loop hit max iterations | Increase `max_iterations` or simplify task |
| `COST_LIMIT_EXCEEDED` | 402 | Run exceeded cost budget | Increase `max_cost_per_run_usd` |
| `TOOL_EXECUTION_FAILED` | 502 | A tool call returned an error | Check tool configuration and target service |
| `GUARDRAIL_TRIGGERED` | 451 | Content filter blocked the run | Review input/output for policy violations |
| `LLM_PROVIDER_ERROR` | 503 | Upstream model API error | Check provider status; NeuralCore retries 3x |
| `CONTEXT_LENGTH_EXCEEDED` | 422 | Token limit for model exceeded | Reduce memory injection or shorten prompt |
| `INVALID_TOOL_SCHEMA` | 400 | Custom tool schema is malformed | Validate against JSON Schema draft-07 |

### Error Response Format

```json
{
  "error": {
    "code": "GUARDRAIL_TRIGGERED",
    "message": "Run blocked by PII detection filter. Email address detected in input.",
    "details": {
      "guardrail": "pii_detection",
      "trigger": "email",
      "position": "input",
      "run_id": "run_abc123"
    },
    "request_id": "req_xyz789"
  }
}
```

---

## 16. Performance Tuning

### Latency Optimization

| Technique | Impact | Trade-off |
|-----------|--------|-----------|
| Use `gpt-4o-mini` for planning steps | -40% latency | Slight quality reduction |
| Reduce `top_k` retrieval from 10 to 5 | -20% latency | Fewer retrieved docs |
| Disable reranking for simple queries | -30% retrieval latency | Lower precision |
| Enable response caching (identical inputs) | -90% latency on cache hits | Stale data risk |
| Reduce `max_tokens` | -15% latency | Shorter outputs |
| Use `temperature: 0` | -5% latency | Deterministic outputs only |

### Throughput Optimization

```yaml
# config/agents.yaml
execution:
  max_concurrent_runs: 50          # Per agent, across all users
  queue_strategy: "priority"       # FIFO or priority-based
  priority_by: "user_tier"         # Route premium users first
  run_pool_size: 20                # Coroutine pool
  tool_timeout_ms: 5000            # Per-tool timeout
  llm_retry_attempts: 3
  llm_retry_backoff_ms: 500
```

### Cost Optimization

- Use **`gpt-4o-mini`** for tool-calling iterations; **`gpt-4o`** only for final synthesis
- Enable **semantic caching** to avoid repeat LLM calls for similar queries
- Set aggressive **`max_tokens`** limits — agents rarely need full context windows
- Use **`summarize_after: 20`** to prevent episodic memory from growing unbounded
- Set **per-project cost budgets** via the billing API to prevent runaway costs

---

## 17. Security Considerations

### Authentication & Authorization

- All agent API calls require a valid JWT Bearer token
- Agents are scoped to **projects** — users can only access agents in projects they belong to
- Role-based access: `viewer` (list/get runs), `developer` (create/update agents), `admin` (delete/deactivate)
- Agent API keys can be issued per-agent for webhook-based integrations

### Data Isolation

- Agent memory is **per-user and per-project** — cross-user memory leakage is architecturally impossible
- Multi-tenant isolation is enforced at the database level via `tenant_id` row-level security in PostgreSQL
- Knowledge base access is permission-controlled: an agent can only query KBs in its own project

### Audit Logging

Every agent action is recorded in the immutable audit log:

```json
{
  "event": "agent.run.completed",
  "actor": "user_456",
  "agent_id": "agent_9f3kd82",
  "run_id": "run_abc123",
  "tenant_id": "tenant_xyz",
  "timestamp": "2026-06-18T10:00:12Z",
  "ip_address": "1.2.3.4",
  "user_agent": "NeuralCore-Python-SDK/1.0.0",
  "token_usage": 3699,
  "cost_usd": 0.0523
}
```

Audit logs are append-only, stored in PostgreSQL with a separate write-only service account, and exported to your SIEM of choice.

### Network Security

- All agent-to-external-tool communication goes through the **NeuralCore Egress Proxy**, which enforces allowlists for HTTP tool calls
- Tool call payloads are signed with HMAC-SHA256; webhook endpoints must verify the signature
- Sensitive values in tool configs (API keys, tokens) are stored in **Vault** and never exposed in API responses

---

*For questions, bug reports, or feature requests related to the agent system, see [CONTRIBUTING.md](CONTRIBUTING.md) or open a GitHub issue tagged `area:agents`.*
