// lib/constants.js

export const APP_NAME = 'NeuralCore';

export const APP_VERSION = '1.0.0';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const API_PREFIX = '/api/v1';

export const AUTH_COOKIE_NAME = 'nc_access_token';

export const REFRESH_COOKIE_NAME = 'nc_refresh_token';

export const USER_ROLES = {
  SUPER_ADMIN: 'super_admin',
  OWNER: 'owner',
  ADMIN: 'admin',
  DEVELOPER: 'developer',
  VIEWER: 'viewer',
};

export const ROLE_LABELS = {
  [USER_ROLES.SUPER_ADMIN]: 'Super Admin',
  [USER_ROLES.OWNER]: 'Owner',
  [USER_ROLES.ADMIN]: 'Admin',
  [USER_ROLES.DEVELOPER]: 'Developer',
  [USER_ROLES.VIEWER]: 'Viewer',
};

export const AGENT_TYPES = {
  PLANNER: 'planner',
  EXECUTOR: 'executor',
  RETRIEVAL: 'retrieval',
  MEMORY: 'memory',
  RESEARCH: 'research',
  CODING: 'coding',
  TOOL: 'tool',
  ORCHESTRATOR: 'orchestrator',
};

export const AGENT_TYPE_LABELS = {
  [AGENT_TYPES.PLANNER]: 'Planner',
  [AGENT_TYPES.EXECUTOR]: 'Executor',
  [AGENT_TYPES.RETRIEVAL]: 'Retrieval',
  [AGENT_TYPES.MEMORY]: 'Memory',
  [AGENT_TYPES.RESEARCH]: 'Research',
  [AGENT_TYPES.CODING]: 'Coding',
  [AGENT_TYPES.TOOL]: 'Tool',
  [AGENT_TYPES.ORCHESTRATOR]: 'Orchestrator',
};

export const AGENT_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

export const AGENT_STEP_STATE = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETE: 'complete',
  ERROR: 'error',
};

export const DOCUMENT_STATUS = {
  QUEUED: 'queued',
  PROCESSING: 'processing',
  READY: 'ready',
  FAILED: 'failed',
};

export const VECTOR_STORE_PROVIDERS = {
  QDRANT: 'qdrant',
  MILVUS: 'milvus',
  WEAVIATE: 'weaviate',
  PGVECTOR: 'pgvector',
  ELASTICSEARCH: 'elasticsearch',
  FAISS: 'faiss',
};

export const VECTOR_STORE_LABELS = {
  [VECTOR_STORE_PROVIDERS.QDRANT]: 'Qdrant',
  [VECTOR_STORE_PROVIDERS.MILVUS]: 'Milvus',
  [VECTOR_STORE_PROVIDERS.WEAVIATE]: 'Weaviate',
  [VECTOR_STORE_PROVIDERS.PGVECTOR]: 'PGVector',
  [VECTOR_STORE_PROVIDERS.ELASTICSEARCH]: 'Elasticsearch',
  [VECTOR_STORE_PROVIDERS.FAISS]: 'FAISS',
};

export const EMBEDDING_PROVIDERS = {
  OPENAI: 'openai',
  BGE: 'bge',
  E5: 'e5',
  JINA: 'jina',
  NOMIC: 'nomic',
  SENTENCE_TRANSFORMERS: 'sentence_transformers',
  CUSTOM: 'custom',
};

export const LLM_PROVIDERS = {
  OPENAI: 'openai',
  ANTHROPIC: 'anthropic',
  LOCAL: 'local',
  CUSTOM: 'custom',
};

export const LLM_PROVIDER_LABELS = {
  [LLM_PROVIDERS.OPENAI]: 'OpenAI',
  [LLM_PROVIDERS.ANTHROPIC]: 'Anthropic',
  [LLM_PROVIDERS.LOCAL]: 'Local Model',
  [LLM_PROVIDERS.CUSTOM]: 'Custom Endpoint',
};

export const RETRIEVAL_STRATEGIES = {
  VECTOR: 'vector',
  BM25: 'bm25',
  HYBRID: 'hybrid',
  GRAPH: 'graph',
  FEDERATED: 'federated',
};

export const RETRIEVAL_STRATEGY_LABELS = {
  [RETRIEVAL_STRATEGIES.VECTOR]: 'Vector Search',
  [RETRIEVAL_STRATEGIES.BM25]: 'Keyword (BM25)',
  [RETRIEVAL_STRATEGIES.HYBRID]: 'Hybrid',
  [RETRIEVAL_STRATEGIES.GRAPH]: 'Graph (GraphRAG)',
  [RETRIEVAL_STRATEGIES.FEDERATED]: 'Federated',
};

export const RERANK_STRATEGIES = {
  RRF: 'rrf',
  WEIGHTED: 'weighted',
  BORDA: 'borda',
  SOFTMAX: 'softmax',
  SCORE_NORMALIZATION: 'score_normalization',
  LINEAR: 'linear',
};

export const CHUNKING_STRATEGIES = {
  FIXED_SIZE: 'fixed_size',
  RECURSIVE: 'recursive',
  SEMANTIC: 'semantic',
  SENTENCE: 'sentence',
  MARKDOWN: 'markdown',
  CODE: 'code',
  TOKEN: 'token',
  HIERARCHICAL: 'hierarchical',
};

export const LOG_LEVELS = {
  DEBUG: 'debug',
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
};

export const LOG_LEVEL_COLORS = {
  [LOG_LEVELS.DEBUG]: 'text-muted-foreground',
  [LOG_LEVELS.INFO]: 'text-primary',
  [LOG_LEVELS.WARNING]: 'text-warning',
  [LOG_LEVELS.ERROR]: 'text-destructive',
  [LOG_LEVELS.CRITICAL]: 'text-destructive',
};

export const ALERT_SEVERITY = {
  CRITICAL: 'critical',
  WARNING: 'warning',
  INFO: 'info',
};

export const PAGINATION_DEFAULTS = {
  PAGE_SIZE: 20,
  PAGE_SIZES: [10, 20, 50, 100],
};

export const DATE_FORMATS = {
  SHORT: 'MMM d, yyyy',
  LONG: 'MMM d, yyyy HH:mm:ss',
  TIME: 'HH:mm:ss',
  ISO: "yyyy-MM-dd'T'HH:mm:ss",
};

export const TOAST_DURATION = 4000;

export const SUPPORTED_FILE_TYPES = [
  '.pdf',
  '.docx',
  '.doc',
  '.txt',
  '.md',
  '.csv',
  '.json',
  '.html',
  '.pptx',
  '.xlsx',
];

export const MAX_FILE_SIZE_MB = 100;

export const POLLING_INTERVALS = {
  AGENT_STATUS: 2000,
  DOCUMENT_STATUS: 3000,
  METRICS: 10000,
  LOGS: 5000,
  ALERTS: 15000,
};

export const COLOR_PALETTE = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-5))',
];