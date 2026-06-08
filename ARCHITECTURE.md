<div align="center">
  
# NeuralCore Architecture
> A comprehensive technical reference for the NeuralCore AI infrastructure platform. This document describes the system design, subsystem boundaries, data flows, and engineering decisions that define the platform at its architectural level.
</div>

## Table of Contents

- [System Overview](#system-overview)
- [Architectural Principles](#architectural-principles)
- [High-Level Architecture](#high-level-architecture)
- [Subsystem Architecture](#subsystem-architecture)
  - [API Gateway Layer](#api-gateway-layer)
  - [Model Gateway](#model-gateway)
  - [Ingestion Pipeline](#ingestion-pipeline)
  - [Preprocessing Layer](#preprocessing-layer)
  - [Chunking System](#chunking-system)
  - [Embedding Layer](#embedding-layer)
  - [Vector Store Abstraction](#vector-store-abstraction)
  - [Retrieval Engine](#retrieval-engine)
  - [Reranking Layer](#reranking-layer)
  - [Prompt Engine](#prompt-engine)
  - [Memory Architecture](#memory-architecture)
  - [Knowledge Graph and GraphRAG](#knowledge-graph-and-graphrag)
  - [Agent System](#agent-system)
  - [Agent Runtime](#agent-runtime)
  - [Agent Communication Layer](#agent-communication-layer)
  - [Agent-to-Agent Protocol (A2A)](#agent-to-agent-protocol-a2a)
  - [Workflow Orchestration](#workflow-orchestration)
  - [Tool Framework](#tool-framework)
  - [Model Context Protocol (MCP)](#model-context-protocol-mcp)
  - [Fine-Tuning Pipeline](#fine-tuning-pipeline)
  - [Distributed Training Infrastructure](#distributed-training-infrastructure)
  - [Multi-Tenancy System](#multi-tenancy-system)
  - [Billing and Monetization](#billing-and-monetization)
  - [Evaluation Framework](#evaluation-framework)
  - [Background Processing](#background-processing)
  - [Plugin Ecosystem](#plugin-ecosystem)
  - [Rust Performance Engine](#rust-performance-engine)
  - [Monitoring and Observability](#monitoring-and-observability)
  - [Authentication and Authorization](#authentication-and-authorization)
  - [Database Layer](#database-layer)
  - [Frontend Application](#frontend-application)
  - [SDK Layer](#sdk-layer)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Deployment Architecture](#deployment-architecture)
- [Security Architecture](#security-architecture)
- [Scalability Model](#scalability-model)
- [Extension Points](#extension-points)
- [Technology Stack Reference](#technology-stack-reference)

---

## System Overview

NeuralCore is a modular, provider-agnostic AI infrastructure platform. Its architecture is organized around independently deployable subsystems that communicate through well-defined interfaces. No subsystem has hard dependencies on the internal implementation of another subsystem. Every major capability — retrieval, agents, memory, billing, multi-tenancy, evaluation — is an isolated module with its own domain boundary.

The platform is designed to serve multi-tenant enterprise workloads. It handles data ingestion from over twenty-five source types, manages knowledge across multiple vector store backends, orchestrates multi-agent workflows, and exposes all capabilities through a uniform REST API and six native SDKs.

Performance-critical operations are offloaded to a Rust engine compiled as a native library and loaded via FFI. The Python application layer handles orchestration, business logic, and API serving. The frontend application provides a complete management interface built with Next.js 14.

---

## Architectural Principles

**Strict Modularity**
Every subsystem is an independent module. Domain boundaries are enforced at the code level. Subsystems communicate through defined interfaces, not internal references. This makes every module independently testable, replaceable, and deployable.

**Provider Agnosticism**
No part of the core platform is tied to a specific model provider, vector store, embedding model, or payment processor. All external integrations are accessed through abstraction layers with a common interface. Switching providers is a configuration operation, not a code change.

**Async-First Design**
The entire backend is built on asynchronous Python with FastAPI and async SQLAlchemy. Every I/O-bound operation — database access, vector store queries, model API calls, background task execution — is non-blocking. This ensures the platform can handle high concurrency without thread pool exhaustion.

**Tenant Isolation by Default**
Multi-tenancy is not a feature layer applied on top of the platform — it is a foundational constraint. Every data access path enforces tenant context. There is no code path that can return cross-tenant data through correct usage.

**Performance at the Boundary**
The boundary between Python and Rust is the performance boundary. Python is used for orchestration and business logic. Rust is used for computation. The FFI bridge is thin, typed, and minimizes serialization overhead.

**Observability as Infrastructure**
Logging, distributed tracing, metrics collection, and alerting are not optional integrations. They are built into the platform at the middleware and service layers. Every request is traced. Every significant operation is logged. Every subsystem exposes metrics.

**Fail-Safe Defaults**
Default configurations are safe. Authentication is required by default. Tenant isolation is enforced by default. Rate limits are applied by default. Audit logging is enabled by default. Operators must explicitly relax constraints, never explicitly add them.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                    │
│     Web UI (Next.js)     Python SDK     TypeScript SDK     REST API     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                        API Gateway Layer                                  │
│         FastAPI Router    Middleware    Auth    Rate Limiting             │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                       │
┌───────▼───────┐   ┌──────────▼─────────┐   ┌───────▼────────┐
│  RAG Pipeline │   │   Agent Subsystem  │   │  Admin / Mgmt  │
│               │   │                    │   │                │
│  Ingestion    │   │  Agent Manager     │   │  Multi-Tenancy │
│  Chunking     │   │  Agent Runtime     │   │  Billing       │
│  Embedding    │   │  Agent Comms       │   │  Analytics     │
│  Retrieval    │   │  A2A Protocol      │   │  Evaluation    │
│  Reranking    │   │  Workflow Engine   │   │  Monitoring    │
│  Prompt Eng.  │   │  Tool Framework    │   │  Plugins       │
│  Memory       │   │  MCP Layer         │   │                │
└───────┬───────┘   └──────────┬─────────┘   └───────┬────────┘
        │                      │                       │
┌───────▼──────────────────────▼───────────────────────▼────────┐
│                     Core Services Layer                         │
│   Model Gateway    Database Layer    Background Queue           │
│   Vector Stores    Knowledge Graph   Fine-Tuning               │
│   Auth / RBAC      Plugin Registry   Rust Engine               │
└────────────────────────────────────────────────────────────────┘
```

---

## Subsystem Architecture

### API Gateway Layer

The API gateway is the single entry point for all client interactions. It is built with FastAPI and organized through a hierarchical router structure.

**Request lifecycle:**
1. Request arrives at the ASGI server (Uvicorn)
2. Global middleware executes: request ID injection, correlation ID propagation, structured logging, CORS enforcement, compression
3. Authentication middleware validates the Bearer token and resolves the user identity
4. Tenant resolver middleware extracts the tenant context from the authenticated identity and injects it into the request state
5. Rate limiting middleware checks the request against the tenant's quota limits
6. The request is routed to the appropriate domain router
7. Route handler executes with dependency-injected services
8. Response middleware applies final transformations and injects trace headers
9. Response is returned to the client

**Route domains:**

| Route Prefix | Domain |
|---|---|
| `/api/v1/auth` | Authentication and token management |
| `/api/v1/projects` | Project management |
| `/api/v1/knowledge-bases` | Knowledge base CRUD and configuration |
| `/api/v1/ingestion` | Document ingestion and status tracking |
| `/api/v1/embeddings` | Embedding generation and management |
| `/api/v1/retrieval` | Query execution and retrieval |
| `/api/v1/reranking` | Standalone reranking operations |
| `/api/v1/agents` | Agent lifecycle management |
| `/api/v1/workflows` | Workflow definition and execution |
| `/api/v1/memory` | Memory read and write operations |
| `/api/v1/pipelines` | Pipeline configuration |
| `/api/v1/vectorstores` | Vector store management |
| `/api/v1/prompts` | Prompt template management |
| `/api/v1/datasets` | Dataset management for fine-tuning |
| `/api/v1/plugins` | Plugin registration and management |
| `/api/v1/monitoring` | Health, metrics, and trace access |
| `/api/v1/analytics` | Usage and cost analytics |
| `/api/v1/organizations` | Organization and member management |
| `/api/v1/workspaces` | Workspace management |
| `/api/v1/users` | User profile management |
| `/api/v1/admin` | Platform administration |

All routes require authentication unless explicitly exempted. All routes except authentication routes require a resolved tenant context.

---

### Model Gateway

The model gateway is the abstraction layer between the NeuralCore application and external LLM providers. Every LLM call in the platform — from the prompt engine, from agents, from the evaluation framework — flows through the model gateway.

**Base provider interface:**

Every provider implements the `BaseProvider` interface which defines:
- `complete(messages, model, options)` — synchronous completion
- `stream(messages, model, options)` — streaming completion with async generator
- `embed(texts, model)` — embedding generation (for providers that support it)
- `available_models()` — list of models available from this provider
- `health_check()` — provider availability check

**Provider routing:**
The `ProviderFactory` maps model identifiers to their respective provider implementations. Model selection can be explicit (caller specifies provider and model) or automatic (the gateway selects the appropriate provider based on model name pattern matching).

**Supported providers:**

| Provider | Models | Streaming | Embeddings |
|---|---|---|---|
| OpenAI | GPT-4o, GPT-4, GPT-3.5, o1, o3 | Yes | Yes |
| Anthropic | Claude 3.5, Claude 3, Claude 2 | Yes | No |
| Google Gemini | Gemini 1.5 Pro, Gemini 1.5 Flash | Yes | Yes |
| DeepSeek | DeepSeek-V2, DeepSeek-Coder | Yes | No |
| Mistral | Mistral Large, Mistral Medium, Mistral Small | Yes | Yes |
| Llama | Llama 3, Llama 2 (via inference servers) | Yes | No |
| Ollama | All locally hosted models | Yes | Yes |

**Adding a new provider:**
Implement `BaseProvider`, register the class in `ProviderFactory`, and add the configuration schema to `embeddings.yaml`. No other changes required.

---

### Ingestion Pipeline

The ingestion pipeline transforms raw source data into indexed, searchable knowledge. It is designed as a sequential processing pipeline with each stage independently configurable.

**Pipeline stages:**
```
Source Data → Loader → Raw Documents → Preprocessor → Clean Documents
→ Chunker → Chunks → Embedding Generator → Vectors → Vector Store
```

**Loader architecture:**
Every loader extends `BaseLoader` which defines the `load() -> List[Document]` interface. The `LoaderFactory` maps source types to loader implementations. Documents produced by all loaders conform to a common `Document` schema:

```
Document {
  content: str
  metadata: Dict[str, Any]
  source: str
  source_type: SourceType
  doc_id: str
  created_at: datetime
  language: Optional[str]
  mime_type: Optional[str]
}
```

**Supported source types and loaders:**

| Category | Sources |
|---|---|
| Documents | PDF, DOCX, TXT, CSV, XLSX, JSON, XML, Markdown, HTML |
| Web | Websites (single page), Sitemaps (full crawl) |
| Code Platforms | GitHub, GitLab, Bitbucket |
| Productivity | Notion, Confluence |
| Communication | Slack, Discord |
| Issue Tracking | Jira |
| Databases | MySQL, PostgreSQL, MongoDB |
| Communication | Email (IMAP/SMTP) |
| Media | YouTube (transcript extraction), Audio (transcription), Video (transcription) |

**Asynchronous ingestion:**
All ingestion operations are submitted to the background task queue and processed asynchronously by dedicated ingestion workers. The API returns a job ID immediately. Clients poll the job status endpoint or subscribe to webhook notifications for completion events.

---

### Preprocessing Layer

Preprocessing transforms raw document content into clean, structured data ready for chunking. All preprocessing operations are applied in a configurable pipeline.

**Preprocessing modules:**

`Cleaner` — removes HTML artifacts, normalizes whitespace, strips control characters, and removes content that matches configurable noise patterns.

`Deduplicator` — identifies and removes duplicate content using MinHash LSH for near-duplicate detection. Operates at both document and chunk level.

`LanguageDetector` — detects document language using statistical language identification. Metadata is enriched with language codes. Language-specific preprocessing can be configured per tenant.

`MetadataExtractor` — extracts structured metadata from document content and file properties: author, creation date, modification date, title, keywords, and custom metadata fields defined by the tenant.

`Normalizer` — normalizes text encoding, applies Unicode normalization (NFC), standardizes quotes, dashes, and other typographic characters.

`PIIDetector` — detects and optionally redacts personally identifiable information including names, email addresses, phone numbers, credit card numbers, and national identification numbers. PII detection is configurable per tenant and per data source.

---

### Chunking System

Chunking determines how documents are split into retrievable units. The right chunking strategy depends on content type, document structure, and retrieval requirements.

**Chunking strategies:**

| Chunker | Use Case |
|---|---|
| `RecursiveChunker` | General-purpose text; splits on paragraph, sentence, word boundaries in order |
| `TokenChunker` | Token-count-based splitting for precise context window management |
| `SemanticChunker` | Embedding-based splitting; chunks at semantic boundary shifts |
| `MarkdownChunker` | Markdown-aware; respects heading hierarchy and code block boundaries |
| `CodeChunker` | Language-aware code splitting; preserves function and class boundaries |
| `ASTChunker` | AST-based code splitting; guarantees syntactically valid code chunks |
| `HybridChunker` | Combines structural and semantic strategies for complex documents |

**Chunk schema:**

```
Chunk {
  chunk_id: str
  doc_id: str
  content: str
  metadata: Dict[str, Any]
  chunk_index: int
  start_char: int
  end_char: int
  token_count: int
  embedding: Optional[List[float]]
}
```

**Configuration parameters:**
Every chunker accepts `chunk_size` (target size in tokens or characters), `chunk_overlap` (overlap between adjacent chunks), and chunker-specific parameters. Configuration is per-knowledge-base.

---

### Embedding Layer

The embedding layer transforms text chunks into vector representations. It is fully abstracted — the retrieval layer has no knowledge of which embedding model is in use.

**Base embedding interface:**

Every embedding provider implements `BaseEmbedding` which defines:
- `embed(texts: List[str]) -> List[List[float]]` — batch embedding
- `embed_query(text: str) -> List[float]` — single query embedding (may use a different model than document embedding)
- `dimension() -> int` — embedding dimension
- `model_name() -> str` — model identifier

**Supported providers:**

| Provider | Models | Dimension |
|---|---|---|
| OpenAI | text-embedding-3-large, text-embedding-3-small, ada-002 | 256–3072 |
| BGE | bge-large-en, bge-base-en, bge-small-en, bge-m3 | 384–1024 |
| E5 | e5-large-v2, e5-base-v2, e5-mistral-7b | 768–4096 |
| Jina | jina-embeddings-v2-base-en, jina-clip-v1 | 768 |
| Nomic | nomic-embed-text-v1, nomic-embed-vision-v1 | 768 |
| Sentence Transformers | Any SBERT-compatible model | Variable |
| Custom | User-defined HTTP embedding endpoint | Variable |

**Embedding factory:**
The `EmbeddingFactory` resolves the configured embedding provider at knowledge-base creation time and maintains a singleton instance per provider configuration. Embedding providers are thread-safe and support concurrent batch requests.

---

### Vector Store Abstraction

The vector store abstraction provides a unified interface over six vector database backends. All retrieval, indexing, and management operations flow through this layer.

**Base vector store interface:**

Every vector store implements `BaseVectorStore` which defines:
- `upsert(chunks: List[Chunk])` — index or update chunks
- `search(query_vector: List[float], filters: Dict, top_k: int) -> List[SearchResult]` — similarity search
- `delete(chunk_ids: List[str])` — remove chunks
- `delete_collection(collection_id: str)` — drop an entire collection
- `get_collection_stats(collection_id: str) -> CollectionStats` — index health and size

**Supported backends:**

| Backend | Strength | Deployment |
|---|---|---|
| Qdrant | High-performance HNSW, rich filtering | Self-hosted, Qdrant Cloud |
| Milvus | Billion-scale, GPU acceleration, multiple index types | Self-hosted, Zilliz Cloud |
| Weaviate | Native graph + vector, multi-tenancy support | Self-hosted, Weaviate Cloud |
| PGVector | PostgreSQL-native, no additional infrastructure | Existing PostgreSQL instance |
| Elasticsearch | Hybrid BM25 + vector, mature filtering | Self-hosted, Elastic Cloud |
| FAISS | Maximum local throughput, no network overhead | In-process, single-node only |

**Collection isolation:**
Every knowledge base within every tenant has an isolated collection in the vector store. Collection naming encodes tenant ID and knowledge base ID to guarantee namespace separation regardless of which vector store backend is in use.

---

### Retrieval Engine

The retrieval engine is the core query execution layer. It accepts a structured query and returns a ranked list of relevant chunks.

**Retrieval modes:**

`VectorSearch` — dense vector similarity search using cosine, dot product, or Euclidean distance against the configured vector store.

`BM25` — sparse keyword search using BM25 term weighting. Implemented natively for backends that do not provide BM25 (Qdrant, Milvus, FAISS) and uses backend-native BM25 for Elasticsearch.

`HybridRetriever` — fuses dense and sparse retrieval results using Reciprocal Rank Fusion (RRF) or configurable score normalization and weighted combination.

`MetadataSearch` — structured filtering against document and chunk metadata fields. Supports exact match, range queries, set membership, and prefix matching depending on backend capabilities.

`GraphSearch` — retrieval through the knowledge graph layer, using entity-centric traversal to surface chunks connected through graph relationships.

`FederatedSearch` — parallel query execution across multiple knowledge bases and vector store backends, with result merging and deduplication.

`MultimodalSearch` — cross-modal retrieval supporting text-to-image, image-to-text, and text-to-audio search through multimodal embedding models.

`QueryRewriter` — transforms the raw user query before retrieval using LLM-based rewriting strategies: hypothetical document embedding (HyDE), query decomposition, query expansion, and step-back prompting.

**Retrieval pipeline:**
```
User Query
  → Query Rewriter (optional)
  → Parallel Retrieval (multiple modes)
  → Result Fusion (RRF or weighted)
  → Metadata Filter Application
  → Reranker (optional)
  → Context Compressor
  → Final Result Set
```

---

### Reranking Layer

Reranking applies a cross-encoder or learning-to-rank model to rescore the initial retrieval results, improving precision by considering query-document interaction rather than independent similarity scores.

**Base reranker interface:**

Every reranker implements `BaseReranker` which defines:
- `rerank(query: str, chunks: List[Chunk], top_n: int) -> List[RankedChunk]` — score and sort

**Supported rerankers:**

| Reranker | Approach | Latency |
|---|---|---|
| `CrossEncoderReranker` | Cross-encoder transformer models | Medium |
| `BGEReranker` | BGE-Reranker series (base, large) | Medium |
| `JinaReranker` | Jina Reranker v2 via API | Medium (API) |
| `HybridReranker` | Score fusion across multiple reranker outputs | Higher |

The Rust engine accelerates cross-encoder inference for locally hosted reranking models through the FFI bridge, reducing p99 reranking latency significantly for high-throughput workloads.

---

### Prompt Engine

The prompt engine constructs the final prompt sent to the language model. It is responsible for assembling context, managing token budgets, and applying templates.

**Components:**

`ContextBuilder` — assembles the retrieved chunks into a structured context block. Applies source attribution, formats evidence, handles multi-document context assembly, and respects configurable context ordering strategies.

`ContextCompressor` — reduces context length when retrieved evidence exceeds the model's context window. Implements extractive compression (sentence-level scoring and selection) and abstractive compression (LLM-based summarization of evidence blocks).

`PromptBuilder` — combines the system prompt template, compressed context, conversation history, and user query into the final message list sent to the model gateway.

`TemplateEngine` — manages named prompt templates with variable interpolation. Templates are stored per-project and can be versioned. Variables are resolved at prompt construction time.

`TokenOptimizer` — enforces token budget constraints. Given a maximum token budget, the token optimizer prioritizes message components: system prompt, recent conversation, compressed context, and user query — trimming lower-priority components to fit within the budget.

---

### Memory Architecture

NeuralCore replaces flat chat history with a structured five-layer memory system.

**Memory layers:**

`ShortTermMemory` — in-process, in-session context. Holds recent message exchanges, active tool call results, and reasoning chain fragments. Stored in Redis with a configurable TTL. Lost when the session ends.

`LongTermMemory` — persistent across sessions. Stores facts, user preferences, and domain knowledge extracted from past interactions. Backed by the primary database. Retrieved semantically using embedding similarity.

`SemanticMemory` — a vector-indexed knowledge store built from interactions. Encodes what the agent knows about the world, the user, and the domain as embedded representations. Queried during context construction to inject relevant background knowledge.

`EpisodicMemory` — a time-indexed record of past events and interactions. Each episode is stored with a timestamp, a summary, and the key outcomes. Enables agents to reason about history: what was tried, what succeeded, what was learned.

`SessionMemory` — manages the full state of an active user session including the active agent context, in-progress workflow state, multi-turn conversation history, and active tool states. Serializable and recoverable from the session store on reconnection.

**Memory manager:**
The `MemoryManager` provides a unified interface over all five layers. Agents interact with memory exclusively through the memory manager — they do not access individual memory stores directly. The manager applies retrieval strategies across layers and merges results into a coherent context contribution.

---

### Knowledge Graph and GraphRAG

The knowledge graph subsystem builds a structured graph representation from ingested documents and uses it to augment retrieval with relational reasoning.

**Graph construction pipeline:**

```
Document Chunks
  → EntityExtractor (NER + domain models)
  → EntityLinker (entity normalization and disambiguation)
  → EntityResolver (cross-document entity merging)
  → RelationshipExtractor (relation triplet extraction)
  → RelationshipScorer (confidence scoring)
  → RelationshipValidator (consistency checks)
  → GraphBuilder (node and edge construction)
  → GraphIndexer (graph storage and index update)
```

**Graph storage:**
The graph store abstracts over graph database backends. Nodes represent entities. Edges represent typed relationships with confidence scores and provenance metadata linking back to the source chunks.

**GraphRAG retrieval:**

The `GraphRetriever` combines vector similarity search with graph traversal:
1. Identify seed entities in the query through entity linking
2. Retrieve directly relevant chunks through vector search
3. Expand context by traversing the knowledge graph from seed entities — collecting related entities, relationship paths, and connected facts
4. Score and merge graph-derived context with vector-retrieved context
5. Pass enriched context to the prompt engine

**Visualization:**
The `GraphRenderer` exports graph subsets as structured data for frontend visualization. The `GraphMetrics` module computes graph quality indicators: entity coverage, relationship density, and resolution quality.

---

### Agent System

The agent system provides the types, configurations, and implementations for all agent roles in the platform.

**Agent types:**

`PlannerAgent` — decomposes high-level goals into executable subtask sequences. Uses chain-of-thought reasoning with tool-augmented planning. Produces structured task plans consumed by executor agents.

`ExecutorAgent` — executes individual tasks from a plan. Selects and invokes tools, manages retries, handles errors, and reports execution results back to the orchestrator.

`RetrievalAgent` — specializes in knowledge access. Executes multi-stage retrieval strategies, synthesizes retrieved evidence, and produces structured retrieval summaries.

`MemoryAgent` — manages long-term memory operations. Extracts memorable facts from interactions, stores them to long-term and semantic memory, and retrieves relevant memory context on demand.

`ResearchAgent` — performs deep research tasks involving multi-hop reasoning, source synthesis, and structured report generation. Capable of iterative research loops with self-directed query refinement.

`CodingAgent` — specializes in code-related tasks: code generation, code explanation, code review, test generation, bug diagnosis, and repository analysis.

`ToolAgent` — a general-purpose agent that manages tool selection, invocation, and output parsing. Serves as the primary interface between reasoning agents and external systems.

**Agent Manager:**
The `AgentManager` handles agent creation, configuration, lifecycle management, and routing. It maintains an agent registry and provides the agent resolution service used by the orchestrator and the A2A protocol.

**Orchestrator:**
The `Orchestrator` coordinates multi-agent task execution. It receives high-level goals, invokes the planner to produce a task plan, assigns tasks to appropriate agents, manages parallel and sequential execution, aggregates results, and handles failures.

---

### Agent Runtime

The agent runtime provides the execution infrastructure for stateful, long-running agents.

**Runtime components:**

`RuntimeManager` — manages the pool of active agent runtimes. Handles agent startup, warm-up, and shutdown sequences. Enforces concurrency limits per tenant.

`LifecycleManager` — controls agent lifecycle transitions: `CREATED → INITIALIZING → IDLE → RUNNING → SUSPENDED → TERMINATED`. Triggers appropriate hooks at each transition.

`Scheduler` — assigns work to available agent runtime instances. Supports priority-based scheduling and fair-share scheduling across tenants.

`CheckpointManager` — serializes the complete agent state — memory state, tool state, conversation context, task progress — to persistent storage at configurable intervals. Enables full agent recovery after process restart or failure.

`StateManager` — manages in-flight agent state. Provides atomic state transitions with optimistic locking to prevent concurrent state corruption.

`EventBus` — the internal event system for agent-internal coordination. Components within an agent publish and subscribe to typed events. The event bus is synchronous within an agent and asynchronous across agents.

---

### Agent Communication Layer

The agent communication layer provides the infrastructure for agents to exchange messages.

**Components:**

`MessageBroker` — the central routing hub for inter-agent messages. Receives messages, resolves destinations, and dispatches to the appropriate channel.

`Router` — maintains routing tables mapping agent identities to communication endpoints. Handles dynamic routing table updates as agents register and deregister.

`Channels` — typed communication channels:
- `DirectChannel` — point-to-point communication between two specific agents
- `BroadcastChannel` — one-to-many communication to all agents matching a topic subscription
- `MulticastChannel` — one-to-many communication to a specific group of agents
- `QueueChannel` — asynchronous message delivery with persistence and acknowledgment semantics

`Protocols` — defines message schemas, versioning, and serialization contracts for agent communication.

---

### Agent-to-Agent Protocol (A2A)

The A2A protocol defines how agents discover, authenticate, and communicate with each other — including agents running in separate processes or on separate nodes.

**Protocol components:**

`AgentRegistry` — a distributed registry of known agents. Each agent registers its identity, capabilities, and communication endpoint. The registry supports capability-based discovery: find all agents that can perform a specific task type.

`DiscoveryService` — enables agents to locate other agents by identity, by capability, or by proximity. Supports both registry-based discovery and peer-to-peer discovery through heartbeat protocols.

`Heartbeat` — each registered agent emits periodic heartbeats to the discovery service. Agents that stop heartbeating are marked unhealthy and removed from the active registry.

`A2ATransport` — the low-level transport layer for cross-process agent communication. Abstracts over WebSocket, gRPC, and in-process channels.

`A2ASecurity` — mutual authentication between agents using signed tokens. Authorization policies define which agents may communicate with which other agents and what message types they may send.

**Communication patterns:**

| Pattern | Description |
|---|---|
| Direct | Agent A sends a message directly to Agent B by identity |
| Broadcast | Agent A sends a message to all agents subscribed to a topic |
| Queue | Agent A sends a message to a named queue; any available consumer processes it |
| Request-Reply | Agent A sends a request and blocks (with timeout) for a reply from Agent B |

---

### Workflow Orchestration

The workflow system enables complex multi-step, multi-agent processes to be defined as reusable, executable workflows.

**Workflow components:**

`WorkflowEngine` — the core execution engine. Parses workflow definitions, manages step sequencing, handles conditional branching, manages parallel step execution, and aggregates results.

`WorkflowBuilder` — a programmatic API for constructing workflow definitions. Provides a fluent interface for defining steps, transitions, conditions, and error handlers.

`WorkflowRegistry` — stores workflow definitions (both system templates and custom definitions) and resolves workflow references at execution time.

`WorkflowRunner` — manages the execution lifecycle of a workflow instance: start, suspend, resume, cancel, and timeout handling.

`WorkflowExecutor` — executes individual workflow steps by routing to the appropriate agent, tool, or inline function.

**Built-in workflow templates:**

| Template | Purpose |
|---|---|
| `rag.py` | Standard single-stage RAG pipeline |
| `agentic_rag.py` | Multi-step RAG with query reformulation and iterative retrieval |
| `research.py` | Deep research workflow with multi-source synthesis |
| `code_assistant.py` | Code understanding, generation, and review workflow |

---

### Tool Framework

The tool framework provides a structured, validated environment for agent tool use.

**Components:**

`ToolRegistry` — maintains the catalog of available tools. Tools register with their name, description, input schema, output schema, and implementation reference.

`ToolValidator` — validates tool call inputs against the registered JSON schema before execution. Rejects invalid inputs with structured error messages that the calling agent can reason about.

`ToolExecutor` — manages tool invocation including timeout enforcement, retry logic, error handling, and output normalization.

`ToolSchemas` — defines the JSON Schema contracts for all built-in tools.

**Built-in tools:**

| Tool | Capability |
|---|---|
| `WebSearch` | Real-time web search |
| `Retrieval` | Knowledge base retrieval |
| `FileReader` | File content extraction |
| `Calculator` | Mathematical computation |
| `Memory` | Memory read and write operations |

**Custom tools:**
Custom tools implement the base tool interface and register through the `ToolRegistry`. No framework modifications are required to add a custom tool.

---

### Model Context Protocol (MCP)

MCP support enables NeuralCore to participate in the emerging ecosystem of MCP-compatible AI tools and clients.

**MCP components:**

`MCPServer` — exposes NeuralCore capabilities (retrieval, memory, agents, knowledge bases) as MCP resources and tools that any MCP-compatible client can access.

`MCPClient` — connects to external MCP servers, enabling NeuralCore agents to use tools and access resources exposed by third-party MCP providers.

`MCPResources` — defines the resource schemas for NeuralCore MCP resources: knowledge bases, documents, agent configurations, and workflow definitions.

`MCPTools` — defines the tool schemas for NeuralCore MCP tools: retrieval, memory access, agent invocation, and workflow execution.

`MCPTransport` — handles the transport layer for MCP communication, supporting both SSE-based and WebSocket-based MCP transports.

---

### Fine-Tuning Pipeline

The fine-tuning pipeline enables domain adaptation of foundation models using supervised fine-tuning, LoRA, and QLoRA techniques.

**Pipeline stages:**

`DatasetBuilder` — generates instruction-following datasets from existing knowledge base content, Q&A pairs, and conversation logs.

`DatasetCleaner` — removes low-quality examples, deduplicates, and normalizes formatting.

`DatasetValidator` — validates datasets against format requirements, checks for data quality issues, and generates quality reports.

**Dataset formats:**

| Format | Description |
|---|---|
| Alpaca | Instruction-input-output format |
| ShareGPT | Multi-turn conversation format |
| OpenAI | OpenAI fine-tuning JSONL format |
| Custom | User-defined format with conversion utility |

**Training:**

`Trainer` — manages the fine-tuning training loop. Supports full fine-tuning, LoRA adapter training, and QLoRA (quantized LoRA) training.

`LoRAAdapter` — configures LoRA-specific hyperparameters: rank, alpha, target modules, and dropout.

`QLoRAAdapter` — extends LoRA with quantization configuration for memory-efficient training on consumer hardware.

**Job management:**

Fine-tuning jobs are submitted to the job queue, processed by dedicated training workers, tracked through the job scheduler, and results stored in the model registry. Training progress is streamed to the calling client via Server-Sent Events.

---

### Distributed Training Infrastructure

For large-scale model training beyond fine-tuning, NeuralCore provides a distributed training infrastructure.

**Training backends:**

`DDP` — PyTorch DistributedDataParallel for multi-GPU training on a single node or across multiple nodes.

`FSDP` — Fully Sharded Data Parallel for training models that exceed single-GPU memory limits.

`DeepSpeed` — Microsoft DeepSpeed integration for ZeRO-stage optimization, gradient accumulation, and mixed-precision training at scale.

**Supporting infrastructure:**

`Launcher` — handles distributed process group initialization, rank assignment, and inter-process coordination.

`ExperimentTracker` — logs hyperparameters, metrics, and artifacts for each training run. Compatible with MLflow, Weights and Biases, and TensorBoard backends.

`CheckpointManager` — saves and loads distributed training checkpoints. Handles checkpoint sharding for FSDP and DeepSpeed checkpoints.

`ModelRegistry` — stores trained model artifacts with versioning, metadata, and evaluation results. Models can be promoted from development to production through the registry.

---

### Multi-Tenancy System

Multi-tenancy is a foundational architectural constraint in NeuralCore, not an add-on feature.

**Tenant isolation model:**

Data isolation in NeuralCore is enforced at multiple layers:

1. **Database layer** — every tenant-scoped table includes a `tenant_id` foreign key. All repository queries include a mandatory tenant filter applied at the repository base class level. It is not possible to query tenant-scoped data without a tenant context.

2. **Vector store layer** — every knowledge base collection is namespaced with the tenant ID. Cross-tenant collection access is prevented at the vector store abstraction layer.

3. **Cache layer** — all Redis keys for tenant-scoped data include the tenant ID as a prefix. Cache entries from different tenants cannot collide.

4. **Agent runtime layer** — agent instances are isolated by tenant. Inter-tenant agent communication is prohibited at the routing layer.

**Tenant resolution:**
The `TenantResolver` middleware extracts the tenant identity from the authenticated request and injects a `TenantContext` into the request state. All downstream services receive the tenant context through FastAPI dependency injection.

**Organization management:**
Each tenant can contain multiple organizations. Organizations contain members with assigned roles. Role-based access control is enforced at the route handler level using a declarative permission decorator system.

**Quota enforcement:**
The `QuotaEnforcement` middleware checks each request against the tenant's configured resource limits before the request reaches the route handler. Limits cover API request rate, tokens per day, storage capacity, active agent count, and knowledge base count. Enforcement is non-blocking: limit checks use atomic Redis counters with sliding window semantics.

---

### Billing and Monetization

The billing system enables commercial deployment of NeuralCore with complete subscription, usage metering, and payment processing capabilities.

**Plan management:**
Plans define feature flags, resource limits, and pricing tiers. The plan system supports free, usage-based, flat-rate, and enterprise custom pricing models.

**Usage metering:**
Every billable event — API call, token consumed, embedding generated, storage written — emits a metering event that is captured asynchronously and aggregated into the billing ledger. Metering uses high-throughput event buffering to avoid adding latency to the critical path.

**Payment processors:**

| Processor | Region | Features |
|---|---|---|
| Stripe | Global | Cards, ACH, invoicing, metered billing |
| PayPal | Global | PayPal wallet, cards |
| Razorpay | India | UPI, cards, netbanking, wallets |

Webhooks from all payment processors are validated for signature authenticity before processing. Webhook processing is idempotent — duplicate events are detected and ignored.

**Invoice generation:**
Invoices are generated automatically at the end of each billing period. Tax calculation, line item breakdown, and PDF export are all supported.

---

### Evaluation Framework

The evaluation framework provides quantitative quality measurement for every layer of the RAG and agent stack.

**Evaluation modules:**

`RetrievalEval` — measures retrieval quality against ground truth relevance annotations. Metrics: Recall@K, Precision@K, NDCG@K, MRR, Hit Rate.

`RerankingEval` — measures reranking quality improvement over base retrieval. Metrics: NDCG improvement, precision gain, position shift analysis.

`RAGEval` — end-to-end RAG pipeline quality measurement. Metrics: answer faithfulness (is the answer grounded in the retrieved context?), answer relevance (does the answer address the question?), context precision (how relevant are the retrieved chunks?), context recall (does the retrieved context contain the answer?).

`AgentEval` — measures agent task completion quality. Metrics: task success rate, tool call accuracy, multi-step reasoning quality, hallucination rate.

`Benchmark` — manages benchmark datasets and runs systematic evaluations across pipeline configurations. Supports comparison of different retrieval strategies, reranker models, and prompt templates.

`ReportGenerator` — produces structured evaluation reports with metric tables, trend analysis, and configuration recommendations.

---

### Background Processing

Long-running and resource-intensive operations are executed asynchronously outside the API request cycle.

**Technology:**
Celery task queue with Redis as the message broker and result backend.

**Task types:**

| Task | Trigger | Worker |
|---|---|---|
| Document ingestion | Ingestion API call | Ingestion worker |
| Embedding generation | Post-ingestion or on-demand | Embedding worker |
| Reranking | Async retrieval pipelines | Reranking worker |
| Retrieval pre-computation | Schedule or trigger | Retrieval worker |
| Cleanup | Schedule | Maintenance worker |

**Worker deployment:**
Workers are independently scalable. Each worker type can be scaled horizontally based on queue depth. The Kubernetes manifests include horizontal pod autoscaler configurations for each worker type.

---

### Plugin Ecosystem

The plugin system allows NeuralCore to be extended with new capabilities without modifying the core platform.

**Plugin lifecycle:**
1. Plugin code is packaged according to the plugin specification
2. Plugin is submitted to the `PluginRegistry`
3. `PluginValidator` verifies the plugin manifest, interface compliance, and security constraints
4. `PluginManager` loads the plugin into the plugin runtime
5. Plugin capabilities become available to agents, workflows, and tools

**Built-in plugins:**
GitHub, Jira, Notion, and Slack plugins are included and maintained as first-party plugins.

**Plugin marketplace:**
The marketplace registry tracks available plugins, their versions, compatibility requirements, and publisher information. Future public plugin distribution will be managed through the marketplace.

---

### Rust Performance Engine

The Rust engine is a native library compiled from the `rust_engine` crate and loaded by the Python backend via PyO3 FFI bindings.

**Modules:**

`vector_index.rs` — HNSW graph construction and search for local vector indexing. Faster than FAISS for incremental index updates.

`similarity.rs` — SIMD-accelerated cosine similarity, dot product, and Euclidean distance computation. Used for in-memory similarity operations that bypass the vector store.

`reranker.rs` — cross-encoder inference acceleration using ONNX Runtime. Enables sub-10ms reranking for top-20 result sets.

`tokenizer.rs` — high-throughput tokenization for chunking and token counting. Uses tiktoken-compatible vocabulary files.

`compression.rs` — vector quantization (scalar and product quantization) for storage-efficient vector representation.

`cache.rs` — LRU and LFU cache implementations with atomic operations for thread-safe shared caching.

`ffi.rs` — the FFI bridge module. Defines the Python-callable functions exported from the Rust library and handles type conversion between Python and Rust type systems.

**Build:**
The Rust engine is compiled as part of the Docker build process. The compiled `.so` or `.dll` artifact is copied into the Python application image. The Python code imports the compiled extension through the standard Python extension mechanism.

---

### Monitoring and Observability

**Structured logging:**
All log output is structured JSON, emitted to stdout and collected by Loki. Every log entry includes: timestamp, level, service, trace ID, span ID, tenant ID (when applicable), and user ID (when applicable).

**Distributed tracing:**
Every inbound API request receives a trace ID. Trace context is propagated through all downstream calls — to the database, to the vector store, to the model gateway, to the background queue. OpenTelemetry is used for trace instrumentation. Traces are exported to the configured OTLP collector.

**Metrics:**
Prometheus metrics are exposed at `/metrics` from every service. Key metrics include: request rate, latency percentiles (p50, p95, p99), error rate, queue depth, worker utilization, vector store query latency, model gateway latency, and token consumption rate.

**Grafana dashboards:**
Pre-built Grafana dashboards provide operational visibility across all services. Dashboard definitions are stored in `infrastructure/monitoring/grafana.json` and are imported automatically on first deployment.

**Alerting:**
Alert rules are defined in Prometheus alerting rule format. Default alerts cover: high error rate, elevated latency, queue backup, worker health, and disk capacity.

---

### Authentication and Authorization

**Authentication:**
JWT-based authentication with RS256 signing. Access tokens have a short expiry (15 minutes). Refresh tokens have a long expiry (30 days) and are rotated on use.

OAuth 2.0 social login is supported for Google, GitHub, and Microsoft identity providers.

**Authorization:**
Role-based access control (RBAC) is enforced at the route handler level. Roles are defined per organization. Default roles: Owner, Admin, Developer, Viewer. Custom roles with granular permission sets can be defined per organization.

Permissions are evaluated at request time — permission changes take effect immediately without token reissuance.

**API keys:**
Service-to-service authentication uses long-lived API keys. API keys are scoped to a project and a role. Keys are stored as bcrypt hashes — the plaintext key is only shown once at creation time.

---

### Database Layer

**Primary database:** PostgreSQL with async SQLAlchemy ORM.

**Models:**

| Model | Domain |
|---|---|
| `User` | Authentication and identity |
| `Project` | Tenant workspace organization |
| `KnowledgeBase` | Knowledge base configuration and status |
| `Agent` | Agent configuration and state |
| `Workflow` | Workflow definitions |
| `Dataset` | Fine-tuning datasets |
| `Memory` | Long-term memory records |

**Repository pattern:**
All database access goes through typed repository classes. Route handlers and services never use the ORM session directly. Repositories enforce tenant isolation at the query level.

**Migrations:**
Schema migrations are managed with Alembic. Migration files are versioned, sequential, and tested. Rollback migrations are required for every forward migration.

---

### Frontend Application

The frontend is a Next.js 14 application using the App Router, React Server Components, and Tailwind CSS.

**Application sections:**

| Section | Purpose |
|---|---|
| Dashboard | Platform overview, usage metrics, activity feed |
| Projects | Project management and configuration |
| Knowledge Bases | Knowledge base management, document inspection, chunk viewing |
| Agents | Agent configuration, execution, and log streaming |
| Retrieval Debugger | Query inspection, chunk scoring, reranker visualization |
| Monitoring | Logs, distributed traces, and alert management |
| Vector Stores | Per-backend index management and health |
| Settings | API keys, user management, security configuration |

**State management:**
Application state is managed through React Context for global state (authentication, active project, settings) and SWR for server state (data fetching, caching, revalidation).

**API communication:**
All API calls are made through a typed Axios client with automatic token refresh, request retry, and error normalization.

---

### SDK Layer

All SDKs implement the same resource model against the NeuralCore REST API.

**SDK resources (all languages):**
`Agents`, `Auth`, `Datasets`, `Embeddings`, `Ingestion`, `Memory`, `Projects`, `Retrieval`, `VectorStores`, `Workflows`

**Common patterns across SDKs:**
- Configurable base URL and API key at client construction
- Automatic retry with exponential backoff on 5xx and rate limit responses
- Typed error classes mapping HTTP error codes to language-native exception types
- Streaming support for completion and agent execution endpoints

---

## Data Flow Diagrams

Detailed data flow diagrams for the following flows are available in `docs/diagrams/`:

- `system_overview.drawio` — full platform component map
- `ingestion_flow.drawio` — document ingestion pipeline
- `retrieval_flow.drawio` — query to response flow
- `agent_flow.drawio` — multi-agent task execution flow

---

## Deployment Architecture

**Single-node (development/staging):**
Docker Compose orchestrates all services on a single host. Services: API server, frontend, Celery workers (ingestion, embedding, reranking), PostgreSQL, Redis, Qdrant.

**Multi-node (production):**
Kubernetes manages service deployment across a node pool. Each service type runs as an independent Deployment with configurable replica counts. Horizontal Pod Autoscaler configurations scale workers based on queue depth and API pods based on request rate.

**Infrastructure provisioning:**
Terraform modules in `infrastructure/terraform/` provision the cloud infrastructure (VPC, compute instances, managed database, load balancer, object storage).

**Database:**
Production deployments use a managed PostgreSQL service (RDS, Cloud SQL, or equivalent). Connection pooling is managed by PgBouncer.

**Object storage:**
Document artifacts and model checkpoints are stored in S3-compatible object storage.

---

## Security Architecture

Full security documentation is in [SECURITY.md](SECURITY.md). Summary:

- All external communication over TLS 1.3
- Tenant data isolated at every layer of the stack
- JWT RS256 signing with short-lived access tokens
- API keys stored as bcrypt hashes
- PII detection and configurable redaction in the preprocessing pipeline
- Comprehensive audit logging for all significant operations
- Dependency vulnerability scanning in the CI pipeline
- Secret management through environment variables and secret managers (Vault, AWS Secrets Manager, GCP Secret Manager)

---

## Scalability Model

**Horizontal scaling:**
The API layer, background workers, and frontend are all stateless and horizontally scalable. Scaling any of these components requires no application changes — only replica count adjustments.

**Vertical scaling:**
The Rust engine benefits significantly from additional CPU cores through SIMD parallelism. Embedding generation and model inference benefit from GPU instances.

**Vector store scaling:**
Qdrant, Milvus, and Weaviate all support distributed deployment modes for scaling beyond single-node capacity. PGVector scales with PostgreSQL read replicas.

**Database scaling:**
Read-heavy workloads are served by read replicas. Write performance is scaled vertically. For very high write throughput, the metering and logging paths use asynchronous write buffering.

---

## Extension Points

NeuralCore is designed with well-defined extension points at every major integration boundary:

| Extension Point | Interface | Location |
|---|---|---|
| New LLM provider | `BaseProvider` | `model_gateway/` |
| New embedding model | `BaseEmbedding` | `embeddings/` |
| New vector store | `BaseVectorStore` | `vector_stores/` |
| New document loader | `BaseLoader` | `ingestion/` |
| New chunking strategy | `BaseChunker` | `chunking/` |
| New reranker | `BaseReranker` | `reranking/` |
| New agent type | `BaseAgent` | `agents/` |
| New tool | `BaseTool` | `tools/` |
| New payment processor | `BasePaymentProvider` | `billing/payments/` |
| New plugin | Plugin specification | `plugins/` |

---

## Technology Stack Reference

| Layer | Technology |
|---|---|
| API framework | FastAPI, Uvicorn, Starlette |
| Language (backend) | Python 3.11+ |
| Language (performance) | Rust (2021 edition) |
| FFI bridge | PyO3 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Cache / Queue broker | Redis 7 |
| Task queue | Celery 5 |
| Vector stores | Qdrant, Milvus, Weaviate, PGVector, Elasticsearch, FAISS |
| Frontend framework | Next.js 14, React 18 |
| Frontend styling | Tailwind CSS |
| Authentication | JWT (RS256), OAuth 2.0 |
| Containerization | Docker, Docker Compose |
| Orchestration | Kubernetes |
| Infrastructure-as-code | Terraform |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Logging | Loki |
| Tracing | OpenTelemetry |

---
<div align="center">
  
*NeuralCore Architecture Document — Copyright (c) 2026 Sambhav Dwivedi. All Rights Reserved.*
</div>