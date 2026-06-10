// rust_engine/benches/tokenizer_bench.rs

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use neuralcore_engine::tokenizer::{
    batch_count_tokens_approximate, count_tokens_approximate, fits_in_context, TokenizerConfig,
    WhitespaceTokenizer,
};

static SHORT_TEXT: &str = "The quick brown fox jumps over the lazy dog.";

static MEDIUM_TEXT: &str = "NeuralCore is a large-scale, production-grade AI infrastructure platform \
    designed to serve as a complete foundation for modern AI systems. It unifies Retrieval-Augmented \
    Generation, Agentic AI, Multi-Agent Orchestration, Knowledge Management, Model Integration, \
    Fine-Tuning, and AI Platform infrastructure into a single, cohesive, modular architecture. \
    The platform supports OpenAI, Anthropic, Google Gemini, DeepSeek, Mistral, Llama, and Ollama \
    through a dedicated model gateway abstraction layer. Six vector store backends are supported: \
    Qdrant, Milvus, Weaviate, PGVector, Elasticsearch, and FAISS.";

static LONG_TEXT: &str = "In the rapidly evolving landscape of artificial intelligence, the need \
    for robust, scalable, and production-ready infrastructure has never been more critical. \
    Organizations across industries — from technology startups to Fortune 500 enterprises — are \
    increasingly recognizing that the success of their AI initiatives depends not just on the \
    quality of their models, but on the underlying infrastructure that supports them. NeuralCore \
    addresses this fundamental challenge by providing a comprehensive, modular AI platform that \
    serves as the backbone for intelligent systems at any scale. The platform architecture is built \
    around the principle of strict modularity — every subsystem operates independently with \
    well-defined interfaces, enabling teams to swap components, scale individual services, and \
    evolve the system over time without introducing cascading dependencies. The retrieval subsystem \
    alone encompasses seven distinct retrieval modes: dense vector search, BM25 sparse retrieval, \
    hybrid fusion, metadata-filtered search, graph-based retrieval, federated multi-source search, \
    and multimodal cross-modal retrieval. Each mode is independently configurable and can be \
    combined in arbitrary ways to construct optimal retrieval pipelines for any use case. The agent \
    system extends beyond simple function calling to provide a complete multi-agent runtime with \
    stateful execution, checkpoint-based recovery, cross-agent communication protocols, and \
    autonomous planning capabilities. Agents can discover each other through the A2A registry, \
    communicate through typed message channels, and collaborate on complex multi-step tasks that \
    would be impossible for a single agent to complete alone. The memory architecture replaces \
    naive chat history with a five-layer cognitive memory system that mirrors human memory patterns: \
    short-term working memory for immediate context, long-term persistent memory across sessions, \
    semantic conceptual memory indexed by meaning, episodic event memory with temporal reasoning, \
    and session state management for multi-turn interactions.";

static CODE_TEXT: &str = r#"
async def hybrid_retriever(
    query: str,
    knowledge_base_id: str,
    top_k: int = 10,
    vector_weight: float = 0.6,
    bm25_weight: float = 0.4,
    rerank: bool = True,
    rerank_top_n: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> List[RetrievalResult]:
    embedding = await embedding_service.embed_query(query)
    vector_results = await vector_store.search(
        collection_id=knowledge_base_id,
        query_vector=embedding,
        top_k=top_k * 2,
        filters=filters,
    )
    bm25_results = await bm25_service.search(
        knowledge_base_id=knowledge_base_id,
        query=query,
        top_k=top_k * 2,
        filters=filters,
    )
    fused = reciprocal_rank_fusion(
        [vector_results, bm25_results],
        weights=[vector_weight, bm25_weight],
        k=60,
    )
    if rerank and len(fused) > rerank_top_n:
        fused = await reranker.rerank(
            query=query,
            results=fused,
            top_n=rerank_top_n,
        )
    return fused[:top_k]
"#;

static MULTILINGUAL_TEXT: &str = "人工知能は現代の技術において重要な役割を果たしています。\
    The system supports multilingual content through specialized embedding models. \
    人工智能基础设施平台必须支持多语言内容处理和检索。\
    Les modèles d'intelligence artificielle nécessitent une infrastructure robuste. \
    La plataforma NeuralCore soporta múltiples idiomas y modelos de embeddings multilingues.";

fn make_batch(text: &str, n: usize) -> Vec<String> {
    (0..n).map(|_| text.to_string()).collect()
}

fn bench_count_tokens_approximate_by_length(c: &mut Criterion) {
    let mut group = c.benchmark_group("count_tokens_approximate/by_text_length");

    let texts = [
        ("short_44_chars", SHORT_TEXT),
        ("medium_480_chars", MEDIUM_TEXT),
        ("long_2000_chars", LONG_TEXT),
        ("code_600_chars", CODE_TEXT),
        ("multilingual_400_chars", MULTILINGUAL_TEXT),
    ];

    for (name, text) in texts {
        group.throughput(Throughput::Bytes(text.len() as u64));
        group.bench_function(name, |bench| {
            bench.iter(|| count_tokens_approximate(black_box(text)))
        });
    }
    group.finish();
}

fn bench_count_tokens_approximate_vs_unicode(c: &mut Criterion) {
    let mut group = c.benchmark_group("count_tokens/text_type_comparison");
    group.sample_size(100);

    group.bench_function("ascii_medium", |bench| {
        bench.iter(|| count_tokens_approximate(black_box(MEDIUM_TEXT)))
    });

    group.bench_function("code_medium", |bench| {
        bench.iter(|| count_tokens_approximate(black_box(CODE_TEXT)))
    });

    group.bench_function("multilingual", |bench| {
        bench.iter(|| count_tokens_approximate(black_box(MULTILINGUAL_TEXT)))
    });

    group.finish();
}

fn bench_batch_count_tokens_by_batch_size(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_count_tokens/by_batch_size");

    for batch_size in [1, 10, 50, 100, 500, 1000] {
        let texts = make_batch(MEDIUM_TEXT, batch_size);

        group.throughput(Throughput::Elements(batch_size as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(batch_size),
            &batch_size,
            |bench, _| bench.iter(|| batch_count_tokens_approximate(black_box(&texts))),
        );
    }
    group.finish();
}

fn bench_batch_count_tokens_by_text_length(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_count_tokens/by_text_length");

    let batch_size = 100;

    group.throughput(Throughput::Elements(batch_size as u64));

    group.bench_function("short_x100", |bench| {
        let texts = make_batch(SHORT_TEXT, batch_size);
        bench.iter(|| batch_count_tokens_approximate(black_box(&texts)))
    });

    group.bench_function("medium_x100", |bench| {
        let texts = make_batch(MEDIUM_TEXT, batch_size);
        bench.iter(|| batch_count_tokens_approximate(black_box(&texts)))
    });

    group.bench_function("long_x100", |bench| {
        let texts = make_batch(LONG_TEXT, batch_size);
        bench.iter(|| batch_count_tokens_approximate(black_box(&texts)))
    });

    group.bench_function("code_x100", |bench| {
        let texts = make_batch(CODE_TEXT, batch_size);
        bench.iter(|| batch_count_tokens_approximate(black_box(&texts)))
    });

    group.finish();
}

fn bench_fits_in_context(c: &mut Criterion) {
    let mut group = c.benchmark_group("fits_in_context");
    group.sample_size(100);

    let overhead = 10;

    let token_limits = [512, 1024, 2048, 4096, 8192, 16384, 32768, 128000];

    for limit in token_limits {
        group.bench_with_input(BenchmarkId::new("limit", limit), &limit, |bench, &lim| {
            bench
                .iter(|| fits_in_context(black_box(LONG_TEXT), black_box(lim), black_box(overhead)))
        });
    }
    group.finish();
}

fn bench_whitespace_tokenizer(c: &mut Criterion) {
    let mut group = c.benchmark_group("whitespace_tokenizer/count");

    let config = TokenizerConfig::default();
    let tokenizer = WhitespaceTokenizer::new(config);

    let texts = [
        ("short", SHORT_TEXT),
        ("medium", MEDIUM_TEXT),
        ("long", LONG_TEXT),
        ("code", CODE_TEXT),
    ];

    for (name, text) in texts {
        group.throughput(Throughput::Bytes(text.len() as u64));
        group.bench_function(name, |bench| {
            bench.iter(|| tokenizer.count_tokens(black_box(text)))
        });
    }
    group.finish();
}

fn bench_throughput_tokens_per_second(c: &mut Criterion) {
    let mut group = c.benchmark_group("throughput/tokens_per_second");
    group.sample_size(50);

    let large_batch_size = 1000;
    let texts_medium = make_batch(MEDIUM_TEXT, large_batch_size);
    let approx_tokens_per_text = count_tokens_approximate(MEDIUM_TEXT);
    let total_tokens = approx_tokens_per_text * large_batch_size;

    group.throughput(Throughput::Elements(total_tokens as u64));
    group.bench_function(
        format!(
            "batch_approx_count_{}docs_~{}tokens",
            large_batch_size, total_tokens
        ),
        |bench| bench.iter(|| batch_count_tokens_approximate(black_box(&texts_medium))),
    );

    group.finish();
}

fn bench_mixed_batch(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_count_tokens/mixed_lengths");
    group.sample_size(30);

    let texts: Vec<String> = (0..200)
        .map(|i| match i % 4 {
            0 => SHORT_TEXT.to_string(),
            1 => MEDIUM_TEXT.to_string(),
            2 => CODE_TEXT.to_string(),
            _ => LONG_TEXT.to_string(),
        })
        .collect();

    group.throughput(Throughput::Elements(texts.len() as u64));
    group.bench_function("mixed_200_docs", |bench| {
        bench.iter(|| batch_count_tokens_approximate(black_box(&texts)))
    });

    group.finish();
}

criterion_group!(
    tokenizer_benches,
    bench_count_tokens_approximate_by_length,
    bench_count_tokens_approximate_vs_unicode,
    bench_batch_count_tokens_by_batch_size,
    bench_batch_count_tokens_by_text_length,
    bench_fits_in_context,
    bench_whitespace_tokenizer,
    bench_throughput_tokens_per_second,
    bench_mixed_batch,
);
criterion_main!(tokenizer_benches);
