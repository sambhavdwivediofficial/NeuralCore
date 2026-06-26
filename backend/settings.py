# settings.py
from __future__ import annotations

import os
import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "configs"
_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}")


def _resolve_env_placeholders(value: Any) -> Any:
    if isinstance(value, str):
        def _replace(match: re.Match[str]) -> str:
            var_name, default = match.group(1), match.group(2)
            return os.environ.get(var_name, default if default is not None else "")
        return _ENV_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {key: _resolve_env_placeholders(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(item) for item in value]
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        return {}
    return _resolve_env_placeholders(data)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    DOT_PRODUCT = "dot_product"
    EUCLIDEAN = "euclidean"
    MANHATTAN = "manhattan"


class AgentType(str, Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    RETRIEVAL = "retrieval"
    MEMORY = "memory"
    RESEARCH = "research"
    CODING = "coding"
    TOOL = "tool"


class CommunicationPattern(str, Enum):
    DIRECT = "direct"
    BROADCAST = "broadcast"
    MULTICAST = "multicast"
    QUEUE = "queue"


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class VectorDBBackend(str, Enum):
    QDRANT = "qdrant"
    MILVUS = "milvus"
    WEAVIATE = "weaviate"
    PGVECTOR = "pgvector"
    ELASTICSEARCH = "elasticsearch"
    FAISS = "faiss"


class EmbeddingProviderName(str, Enum):
    OPENAI = "openai"
    BGE = "bge"
    E5 = "e5"
    JINA = "jina"
    NOMIC = "nomic"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    CUSTOM = "custom"


class LLMProviderName(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    LLAMA = "llama"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    LOCAL = "local"


class StorageBackend(str, Enum):
    S3 = "s3"
    LOCAL = "local"
    GCS = "gcs"
    AZURE = "azure"


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    root_path: str = ""
    proxy_headers: bool = True
    forwarded_allow_ips: str = "*"


class CORSSettings(BaseModel):
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5242"])
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    allow_credentials: bool = True
    max_age: int = 600


class SecurityHeadersSettings(BaseModel):
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = "geolocation=(), microphone=(), camera=()"
    content_security_policy: str = "default-src 'self'"
    strict_transport_security: str = "max-age=63072000; includeSubDomains; preload"


class RateLimitSettings(BaseModel):
    enabled: bool = True
    requests_per_minute: int = 120
    burst: int = 20
    storage: str = "redis"
    key_prefix: str = "ratelimit"


class PaginationSettings(BaseModel):
    default_page_size: int = 20
    max_page_size: int = 100


class UploadSettings(BaseModel):
    max_file_size_mb: int = 100
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [
            "pdf", "docx", "txt", "md", "csv", "json", "xml", "xlsx",
            "html", "pptx", "mp3", "wav", "mp4", "mov",
        ]
    )
    temp_dir: str = "/tmp/neuralcore-uploads"


class StorageSettings(BaseModel):
    backend: StorageBackend = StorageBackend.S3
    bucket: str = "neuralcore-uploads"
    region: str = "us-east-1"
    endpoint_url: Optional[str] = None
    access_key_id: Optional[SecretStr] = None
    secret_access_key: Optional[SecretStr] = None
    use_path_style: bool = False
    local_path: str = "/data/storage"


class AppCacheSettings(BaseModel):
    backend: str = "redis"
    default_ttl_seconds: int = 300
    embedding_cache_ttl_seconds: int = 86400
    query_result_cache_ttl_seconds: int = 600
    similarity_cache_ttl_seconds: int = 3600


class HealthCheckSettings(BaseModel):
    path: str = "/health"
    ready_path: str = "/ready"
    live_path: str = "/live"


class TelemetrySettings(BaseModel):
    enabled: bool = True
    service_name: str = "neuralcore-backend"
    environment_tag: str = "production"


class AppSettings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    security_headers: SecurityHeadersSettings = Field(default_factory=SecurityHeadersSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    pagination: PaginationSettings = Field(default_factory=PaginationSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    cache: AppCacheSettings = Field(default_factory=AppCacheSettings)
    health_check: HealthCheckSettings = Field(default_factory=HealthCheckSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    feature_flags: dict[str, bool] = Field(default_factory=dict)


class JWTSettings(BaseModel):
    algorithm: str = "RS256"
    private_key: Optional[SecretStr] = None
    public_key: Optional[SecretStr] = None
    private_key_path: Optional[Path] = None
    public_key_path: Optional[Path] = None
    access_token_expire_minutes: int = 43200
    refresh_token_expire_days: int = 30
    issuer: str = "neuralcore"
    audience: str = "neuralcore-api"
    leeway_seconds: int = 10

    @model_validator(mode="after")
    def _load_key_files(self) -> "JWTSettings":
        if self.private_key is None and self.private_key_path and self.private_key_path.is_file():
            self.private_key = SecretStr(self.private_key_path.read_text(encoding="utf-8"))
        if self.public_key is None and self.public_key_path and self.public_key_path.is_file():
            self.public_key = SecretStr(self.public_key_path.read_text(encoding="utf-8"))
        return self


class PasswordPolicySettings(BaseModel):
    bcrypt_rounds: int = 12
    min_length: int = 10
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_number: bool = True
    require_special: bool = True


class SessionSettings(BaseModel):
    cookie_name: str = "nc_session"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    max_concurrent_sessions: int = 5
    idle_timeout_minutes: int = 60


class MFASettings(BaseModel):
    enabled: bool = True
    issuer_name: str = "NeuralCore"
    digits: int = 6
    period_seconds: int = 30
    recovery_codes_count: int = 10


class OAuthProviderConfig(BaseModel):
    enabled: bool = False
    client_id: Optional[str] = None
    client_secret: Optional[SecretStr] = None
    redirect_uri: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""


class OAuthSettings(BaseModel):
    providers: dict[str, OAuthProviderConfig] = Field(
        default_factory=lambda: {
            "google": OAuthProviderConfig(
                scopes=["openid", "email", "profile"],
                authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            ),
            "github": OAuthProviderConfig(
                scopes=["read:user", "user:email"],
                authorize_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                userinfo_url="https://api.github.com/user",
            ),
            "microsoft": OAuthProviderConfig(
                scopes=["openid", "email", "profile", "User.Read"],
                authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
                userinfo_url="https://graph.microsoft.com/oidc/userinfo",
            ),
        }
    )


class APIKeySettings(BaseModel):
    prefix: str = "nc_"
    length: int = 48
    default_expire_days: Optional[int] = 365
    hash_algorithm: str = "sha256"


class AccountLockoutSettings(BaseModel):
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15
    reset_after_minutes: int = 60


class EmailVerificationSettings(BaseModel):
    enabled: bool = True
    token_expire_hours: int = 24
    resend_cooldown_seconds: int = 60


class AuthSettings(BaseModel):
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    password_policy: PasswordPolicySettings = Field(default_factory=PasswordPolicySettings)
    session: SessionSettings = Field(default_factory=SessionSettings)
    mfa: MFASettings = Field(default_factory=MFASettings)
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)
    api_keys: APIKeySettings = Field(default_factory=APIKeySettings)
    account_lockout: AccountLockoutSettings = Field(default_factory=AccountLockoutSettings)
    email_verification: EmailVerificationSettings = Field(default_factory=EmailVerificationSettings)
    roles: list[Role] = Field(default_factory=lambda: list(Role))
    default_role: Role = Role.VIEWER


class AgentLimitsSettings(BaseModel):
    max_agents_per_tenant: int = 50
    max_agents_global: int = 500
    max_concurrent_tasks_per_agent: int = 5
    max_task_retries: int = 3


class SchedulerSettings(BaseModel):
    poll_interval_seconds: float = 1.0
    max_queue_size: int = 1000
    priority_levels: int = 5
    task_timeout_seconds: int = 600


class A2ASettings(BaseModel):
    protocol_version: str = "1.0"
    patterns: list[CommunicationPattern] = Field(default_factory=lambda: list(CommunicationPattern))
    message_ttl_seconds: int = 300
    max_message_size_bytes: int = 1048576
    delivery_retries: int = 3


class MemoryLayerConfig(BaseModel):
    backend: str = "redis"
    ttl_seconds: Optional[int] = None
    max_entries: Optional[int] = None


class MemoryArchitectureSettings(BaseModel):
    short_term: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(backend="redis", ttl_seconds=3600, max_entries=200)
    )
    long_term: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(backend="postgres", ttl_seconds=None, max_entries=None)
    )
    semantic: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(backend="vector", ttl_seconds=None, max_entries=None)
    )
    episodic: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(backend="postgres", ttl_seconds=None, max_entries=1000)
    )
    session: MemoryLayerConfig = Field(
        default_factory=lambda: MemoryLayerConfig(backend="redis", ttl_seconds=86400, max_entries=50)
    )


class ContextWindowBudgetSettings(BaseModel):
    total_tokens: int = 32768
    system_prompt_ratio: float = 0.05
    memory_ratio: float = 0.25
    retrieval_ratio: float = 0.35
    conversation_ratio: float = 0.25
    tool_output_ratio: float = 0.10


class AgentSettings(BaseModel):
    limits: AgentLimitsSettings = Field(default_factory=AgentLimitsSettings)
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    a2a: A2ASettings = Field(default_factory=A2ASettings)
    memory: MemoryArchitectureSettings = Field(default_factory=MemoryArchitectureSettings)
    context_window: ContextWindowBudgetSettings = Field(default_factory=ContextWindowBudgetSettings)
    agent_types: list[AgentType] = Field(default_factory=lambda: list(AgentType))
    default_lifecycle_timeout_seconds: int = 3600


class EmbeddingProviderConfig(BaseModel):
    enabled: bool = True
    models: dict[str, Any] = Field(default_factory=dict)
    default_model: str = ""
    api_key: Optional[SecretStr] = None
    base_url: Optional[str] = None
    dimension: Optional[int] = None
    max_input_tokens: Optional[int] = None
    batch_size: int = 32
    device: str = "cpu"


class EmbeddingPipelineSettings(BaseModel):
    batch_size: int = 64
    max_parallel_requests: int = 8
    retry_attempts: int = 3
    retry_backoff_seconds: float = 1.0


class EmbeddingQualitySettings(BaseModel):
    enabled: bool = True
    reject_zero_vectors: bool = True
    reject_nan_vectors: bool = True
    min_norm: float = 1e-6


class EmbeddingSettings(BaseModel):
    default_provider: EmbeddingProviderName = EmbeddingProviderName.OPENAI
    providers: dict[str, EmbeddingProviderConfig] = Field(
        default_factory=lambda: {
            "openai": EmbeddingProviderConfig(
                models={
                    "text-embedding-3-large": {"dimension": 3072, "max_input_tokens": 8191},
                    "text-embedding-3-small": {"dimension": 1536, "max_input_tokens": 8191},
                    "text-embedding-ada-002": {"dimension": 1536, "max_input_tokens": 8191},
                },
                default_model="text-embedding-3-large",
                dimension=3072,
                max_input_tokens=8191,
            ),
            "bge": EmbeddingProviderConfig(
                models={
                    "bge-large-en-v1.5": {"dimension": 1024, "max_input_tokens": 512},
                    "bge-base-en-v1.5": {"dimension": 768, "max_input_tokens": 512},
                    "bge-small-en-v1.5": {"dimension": 384, "max_input_tokens": 512},
                    "bge-m3": {"dimension": 1024, "max_input_tokens": 8192},
                },
                default_model="bge-m3",
                dimension=1024,
                max_input_tokens=8192,
                device="cpu",
            ),
            "e5": EmbeddingProviderConfig(
                models={
                    "e5-large-v2": {"dimension": 1024, "max_input_tokens": 512},
                    "e5-base-v2": {"dimension": 768, "max_input_tokens": 512},
                    "e5-small-v2": {"dimension": 384, "max_input_tokens": 512},
                    "e5-multilingual-large": {"dimension": 1024, "max_input_tokens": 512},
                    "e5-mistral-7b": {"dimension": 4096, "max_input_tokens": 32768},
                },
                default_model="e5-large-v2",
                dimension=1024,
                max_input_tokens=512,
            ),
            "jina": EmbeddingProviderConfig(
                models={
                    "jina-embeddings-v3": {"dimension": 1024, "max_input_tokens": 8192},
                    "jina-embeddings-v2": {"dimension": 768, "max_input_tokens": 8192},
                    "jina-clip-v2": {"dimension": 1024, "max_input_tokens": 8192, "multimodal": True},
                },
                default_model="jina-embeddings-v3",
                dimension=1024,
                max_input_tokens=8192,
            ),
            "nomic": EmbeddingProviderConfig(
                models={
                    "nomic-embed-text-v1.5": {"dimension": 768, "max_input_tokens": 8192},
                    "nomic-embed-vision-v1.5": {"dimension": 768, "max_input_tokens": 8192, "multimodal": True},
                },
                default_model="nomic-embed-text-v1.5",
                dimension=768,
                max_input_tokens=8192,
            ),
            "sentence_transformers": EmbeddingProviderConfig(
                models={
                    "all-MiniLM-L6-v2": {"dimension": 384, "max_input_tokens": 256},
                    "all-mpnet-base-v2": {"dimension": 768, "max_input_tokens": 384},
                },
                default_model="all-mpnet-base-v2",
                dimension=768,
                max_input_tokens=384,
                device="cpu",
            ),
            "custom": EmbeddingProviderConfig(enabled=False, models={}, default_model="", dimension=None),
        }
    )
    pipeline: EmbeddingPipelineSettings = Field(default_factory=EmbeddingPipelineSettings)
    quality_validation: EmbeddingQualitySettings = Field(default_factory=EmbeddingQualitySettings)


class PaymentProviderConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[SecretStr] = None
    api_secret: Optional[SecretStr] = None
    webhook_secret: Optional[SecretStr] = None
    sandbox_mode: bool = True


class BillingSettings(BaseModel):
    default_currency: str = "USD"
    trial_days: int = 14
    invoice_due_days: int = 7
    tax_inclusive_pricing: bool = False
    providers: dict[str, PaymentProviderConfig] = Field(
        default_factory=lambda: {
            "stripe": PaymentProviderConfig(),
            "razorpay": PaymentProviderConfig(),
            "paypal": PaymentProviderConfig(),
        }
    )
    default_provider: str = "razorpay"


class VectorSearchSettings(BaseModel):
    default_top_k: int = 10
    max_top_k: int = 100
    score_threshold: float = 0.0
    metric: DistanceMetric = DistanceMetric.COSINE


class BM25Settings(BaseModel):
    enabled: bool = True
    k1: float = 1.5
    b: float = 0.75
    stemmer: str = "porter"


class HybridSearchSettings(BaseModel):
    enabled: bool = True
    rrf_k: int = 60
    vector_weight: float = 0.6
    bm25_weight: float = 0.4


class MetadataSearchSettings(BaseModel):
    operators: list[str] = Field(
        default_factory=lambda: [
            "equals", "not_equals", "gt", "lt", "gte", "lte",
            "in", "not_in", "contains", "starts_with", "ends_with", "exists",
        ]
    )


class GraphSearchSettings(BaseModel):
    enabled: bool = True
    max_hops: int = 3
    max_entities_per_hop: int = 50


class FederatedSearchSettings(BaseModel):
    enabled: bool = True
    max_knowledge_bases: int = 10
    timeout_seconds: float = 10.0


class MultimodalSearchSettings(BaseModel):
    enabled: bool = True
    image_embedding_provider: str = "jina"


class QueryRewritingSettings(BaseModel):
    hyde_enabled: bool = True
    step_back_enabled: bool = True
    decomposition_enabled: bool = True
    expansion_enabled: bool = True
    splade_enabled: bool = False
    rewriting_provider: LLMProviderName = LLMProviderName.OLLAMA


class RerankingDefaultsSettings(BaseModel):
    enabled: bool = True
    default_provider: str = "bge"
    default_model: str = "bge-reranker-large"
    top_n: int = 5
    providers: list[str] = Field(default_factory=lambda: ["cross_encoder", "bge", "jina", "hybrid"])


class ContextCompressionSettings(BaseModel):
    enabled: bool = True
    method: str = "extractive"
    max_output_tokens: int = 2000


class RetrievalSettings(BaseModel):
    vector_search: VectorSearchSettings = Field(default_factory=VectorSearchSettings)
    bm25: BM25Settings = Field(default_factory=BM25Settings)
    hybrid: HybridSearchSettings = Field(default_factory=HybridSearchSettings)
    metadata_search: MetadataSearchSettings = Field(default_factory=MetadataSearchSettings)
    graph_search: GraphSearchSettings = Field(default_factory=GraphSearchSettings)
    federated_search: FederatedSearchSettings = Field(default_factory=FederatedSearchSettings)
    multimodal_search: MultimodalSearchSettings = Field(default_factory=MultimodalSearchSettings)
    query_rewriting: QueryRewritingSettings = Field(default_factory=QueryRewritingSettings)
    reranking: RerankingDefaultsSettings = Field(default_factory=RerankingDefaultsSettings)
    context_compression: ContextCompressionSettings = Field(default_factory=ContextCompressionSettings)


class QdrantConfig(BaseModel):
    host: str = "qdrant"
    port: int = 6333
    grpc_port: int = 6334
    prefer_grpc: bool = True
    https: bool = False
    api_key: Optional[SecretStr] = None
    hnsw_m: int = 16
    hnsw_ef_construct: int = 100
    quantization: str = "scalar"
    distance: DistanceMetric = DistanceMetric.COSINE
    timeout: float = 30.0


class MilvusConfig(BaseModel):
    host: str = "milvus"
    port: int = 19530
    index_type: str = "HNSW"
    metric: DistanceMetric = DistanceMetric.COSINE
    nlist: int = 1024
    hnsw_m: int = 16
    hnsw_ef_construct: int = 200


class WeaviateConfig(BaseModel):
    url: str = "http://weaviate:8080"
    api_key: Optional[SecretStr] = None
    multi_tenancy: bool = True
    bm25: bool = True
    timeout_seconds: float = 30.0


class PGVectorConfig(BaseModel):
    index_type: str = "hnsw"
    lists: int = 100
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64
    metric: DistanceMetric = DistanceMetric.COSINE


class ElasticsearchConfig(BaseModel):
    hosts: list[str] = Field(default_factory=lambda: ["http://elasticsearch:9200"])
    api_key: Optional[SecretStr] = None
    index_prefix: str = "neuralcore"
    dense_vector_dims: int = 1536
    hnsw_m: int = 16
    hnsw_ef_construction: int = 100


class FAISSConfig(BaseModel):
    index_type: str = "ivfflat"
    nlist: int = 100
    pq_m: int = 8
    pq_bits: int = 8
    storage_path: str = "/data/faiss"


class VectorDBSettings(BaseModel):
    default: VectorDBBackend = VectorDBBackend.QDRANT
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    weaviate: WeaviateConfig = Field(default_factory=WeaviateConfig)
    pgvector: PGVectorConfig = Field(default_factory=PGVectorConfig)
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    faiss: FAISSConfig = Field(default_factory=FAISSConfig)


class LoggingSettings(BaseModel):
    level: str = "INFO"
    json_format: bool = True
    sanitize_patterns: list[str] = Field(
        default_factory=lambda: [
            r"Bearer\s+[A-Za-z0-9\-_\.]+",
            r"sk-[A-Za-z0-9]{20,}",
            r"nc_[A-Za-z0-9]{20,}",
            r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+",
            r"\b(?:\d[ -]*?){13,16}\b",
        ]
    )
    per_module_levels: dict[str, str] = Field(default_factory=dict)
    sentry_dsn: Optional[SecretStr] = None
    sentry_traces_sample_rate: float = 0.1
    slow_query_threshold_ms: int = 500
    slow_llm_call_threshold_ms: int = 3000


class PrometheusSettings(BaseModel):
    enabled: bool = True
    port: int = 9090
    path: str = "/metrics"


class OTLPSettings(BaseModel):
    enabled: bool = True
    endpoint: str = "http://otel-collector:4317"
    sample_rate: float = 0.1
    service_name: str = "neuralcore-backend"


class AlertDestinationSettings(BaseModel):
    slack_webhook_url: Optional[SecretStr] = None
    pagerduty_routing_key: Optional[SecretStr] = None
    alert_email: Optional[str] = None


class HealthCheckTargets(BaseModel):
    database: bool = True
    redis: bool = True
    vector_db: bool = True
    disk: bool = True
    memory: bool = True
    disk_threshold_percent: float = 90.0
    memory_threshold_percent: float = 90.0


class MonitoringSettings(BaseModel):
    prometheus: PrometheusSettings = Field(default_factory=PrometheusSettings)
    otlp: OTLPSettings = Field(default_factory=OTLPSettings)
    alert_destinations: AlertDestinationSettings = Field(default_factory=AlertDestinationSettings)
    health_check_targets: HealthCheckTargets = Field(default_factory=HealthCheckTargets)
    alerting_enabled: bool = True


class ModelProviderConfig(BaseModel):
    enabled: bool = True
    api_key: Optional[SecretStr] = None
    base_url: Optional[str] = None
    default_model: str = ""
    context_window: int = 8192
    timeout_seconds: float = 60.0
    max_retries: int = 3
    supports_streaming: bool = True
    supports_tools: bool = True


class ModelGatewaySettings(BaseModel):
    default_provider: LLMProviderName = LLMProviderName.OLLAMA
    fallback_chain: list[LLMProviderName] = Field(
        # default_factory=lambda: [LLMProviderName.LOCAL, LLMProviderName.OLLAMA, LLMProviderName.OPENAI]
        default_factory=lambda: [LLMProviderName.OLLAMA]
    )
    providers: dict[str, ModelProviderConfig] = Field(
        default_factory=lambda: {
            "local": ModelProviderConfig(
                base_url="http://localhost:11434",
                default_model="Roxan",
                context_window=32768,
                timeout_seconds=180.0,
                enabled=True,
            ),
            "ollama": ModelProviderConfig(
                base_url="http://localhost:11434",
                default_model="Roxan",
                context_window=32768,
                timeout_seconds=180.0,
                enabled=True,
            ),
            "openai": ModelProviderConfig(
                default_model="gpt-4o",
                context_window=128000,
                enabled=False,
            ),
            "anthropic": ModelProviderConfig(
                default_model="claude-sonnet-4-6",
                context_window=200000,
                enabled=False,
            ),
            "deepseek": ModelProviderConfig(
                base_url="https://api.deepseek.com",
                default_model="deepseek-chat",
                context_window=64000,
                enabled=False,
            ),
            "gemini": ModelProviderConfig(
                default_model="gemini-1.5-pro",
                context_window=1000000,
                enabled=False,
            ),
            "mistral": ModelProviderConfig(
                default_model="mistral-large-latest",
                context_window=128000,
                enabled=False,
            ),
            "llama": ModelProviderConfig(
                base_url="http://localhost:11434",
                default_model="qwen3-coder:30b",
                context_window=32768,
                timeout_seconds=180.0,
                enabled=True,
            ),
        }
    )


class DatabaseSettings(BaseModel):
    url: SecretStr = SecretStr("postgresql+asyncpg://neuralcore:neuralcore@postgres:5432/neuralcore")
    sync_url: Optional[SecretStr] = None
    pool_size: int = 20
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False


class RedisSettings(BaseModel):
    url: str = "redis://redis:6379/0"
    max_connections: int = 50
    socket_timeout: float = 5.0
    decode_responses: bool = True


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    project_name: str = "NeuralCore"
    version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    secret_key: SecretStr = SecretStr("change-me-in-production")
    config_dir: Path = DEFAULT_CONFIG_DIR

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    vector_db: VectorDBSettings = Field(default_factory=VectorDBSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    model_gateway: ModelGatewaySettings = Field(default_factory=ModelGatewaySettings)
    billing: BillingSettings = Field(default_factory=BillingSettings)

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def database_url(self) -> str:
        return self.database.url.get_secret_value()

    @property
    def database_sync_url(self) -> str:
        if self.database.sync_url is not None:
            return self.database.sync_url.get_secret_value()
        return self.database_url.replace("+asyncpg", "+psycopg")


DOMAIN_CONFIG_FILES: dict[str, str] = {
    "app": "app.yaml",
    "auth": "auth.yaml",
    "agents": "agents.yaml",
    "embeddings": "embeddings.yaml",
    "retrieval": "retrieval.yaml",
    "vector_db": "vector_db.yaml",
    "logging": "logging.yaml",
    "monitoring": "monitoring.yaml",
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    base = Settings()
    config_dir = base.config_dir
    if not config_dir.is_dir():
        fallback = BASE_DIR / "configs"
        if fallback.is_dir():
            config_dir = fallback
    merged = base.model_dump(mode="python")
    for domain, filename in DOMAIN_CONFIG_FILES.items():
        overrides = _load_yaml(config_dir / filename)
        if overrides:
            merged[domain] = _deep_merge(merged.get(domain, {}), overrides)
    merged["config_dir"] = config_dir
    return Settings.model_validate(merged)


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


settings = get_settings()