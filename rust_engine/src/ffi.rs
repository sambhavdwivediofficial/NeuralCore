// rust_engine/src/ffi.rs

use crate::cache::{EmbeddingCache, QueryResultCache};
use crate::compression::{
    compress, compress_vectors, decompress, decompress_vectors, dequantize_scalar_i8,
    quantize_scalar_i8, CompressionConfig,
};
use crate::reranker::{
    compute_mrr, compute_ndcg, compute_precision_at_k, NormalizationMethod, RerankerConfig,
    RerankerType, ScoreFusion,
};
use crate::similarity::{
    batch_cosine_similarity, batch_dot_product, cosine_similarity, cosine_similarity_prenormalized,
    dot_product, euclidean_distance, euclidean_similarity, top_k_by_similarity,
};
use crate::tokenizer::{batch_count_tokens_approximate, count_tokens_approximate, fits_in_context};
use crate::types::{DistanceMetric, RankedResult};
use crate::utils::{min_max_normalize, normalize_vector_new, reciprocal_rank_fusion, softmax};
use crate::vector_index::{IndexConfig, VectorIndex};
use once_cell::sync::Lazy;
use parking_lot::Mutex;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::Bound;
use std::collections::HashMap;
use std::sync::Arc;

static VECTOR_INDEXES: Lazy<Mutex<HashMap<String, Arc<VectorIndex>>>> =
    Lazy::new(|| Mutex::new(HashMap::new()));

static EMBEDDING_CACHE: Lazy<EmbeddingCache> = Lazy::new(|| EmbeddingCache::new(50_000, 86400));

#[allow(dead_code)]
static QUERY_CACHE: Lazy<QueryResultCache> = Lazy::new(|| QueryResultCache::new(10_000, 300));

fn engine_err_to_py(e: crate::error::EngineError) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

#[pyfunction]
#[pyo3(signature = (a, b, prenormalized = false))]
fn py_cosine_similarity(a: Vec<f32>, b: Vec<f32>, prenormalized: bool) -> PyResult<f32> {
    if prenormalized {
        cosine_similarity_prenormalized(&a, &b).map_err(engine_err_to_py)
    } else {
        cosine_similarity(&a, &b).map_err(engine_err_to_py)
    }
}

#[pyfunction]
fn py_dot_product(a: Vec<f32>, b: Vec<f32>) -> PyResult<f32> {
    dot_product(&a, &b).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_euclidean_distance(a: Vec<f32>, b: Vec<f32>) -> PyResult<f32> {
    euclidean_distance(&a, &b).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_euclidean_similarity(a: Vec<f32>, b: Vec<f32>) -> PyResult<f32> {
    euclidean_similarity(&a, &b).map_err(engine_err_to_py)
}

#[pyfunction]
#[pyo3(signature = (query, vectors, prenormalized = false))]
fn py_batch_cosine_similarity(
    query: Vec<f32>,
    vectors: Vec<Vec<f32>>,
    prenormalized: bool,
) -> PyResult<Vec<f32>> {
    batch_cosine_similarity(&query, &vectors, prenormalized).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_batch_dot_product(query: Vec<f32>, vectors: Vec<Vec<f32>>) -> PyResult<Vec<f32>> {
    batch_dot_product(&query, &vectors).map_err(engine_err_to_py)
}

#[pyfunction]
#[pyo3(signature = (query, vectors, ids, k, metric = "cosine", prenormalized = false))]
fn py_top_k_by_similarity(
    query: Vec<f32>,
    vectors: Vec<Vec<f32>>,
    ids: Vec<String>,
    k: usize,
    metric: &str,
    prenormalized: bool,
) -> PyResult<Vec<(String, f32)>> {
    let dist: DistanceMetric = metric.parse().map_err(engine_err_to_py)?;
    top_k_by_similarity(&query, &vectors, &ids, k, dist, prenormalized).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_normalize_vector(v: Vec<f32>) -> Vec<f32> {
    normalize_vector_new(&v)
}

#[pyfunction]
fn py_batch_normalize_vectors(vectors: Vec<Vec<f32>>) -> Vec<Vec<f32>> {
    vectors.iter().map(|v| normalize_vector_new(v)).collect()
}

#[pyfunction]
fn py_min_max_normalize(scores: Vec<f32>) -> Vec<f32> {
    min_max_normalize(&scores)
}

#[pyfunction]
fn py_softmax(scores: Vec<f32>) -> Vec<f32> {
    softmax(&scores)
}

#[pyfunction]
#[pyo3(signature = (ranked_lists, k = 60.0))]
fn py_reciprocal_rank_fusion(
    ranked_lists: Vec<Vec<(String, usize)>>,
    k: f32,
) -> Vec<(String, f32)> {
    reciprocal_rank_fusion(&ranked_lists, k)
}

#[pyfunction]
#[pyo3(signature = (
    index_id,
    dimension,
    metric = "cosine",
    m = 16usize,
    ef_construction = 200usize,
    ef_search = 128usize,
    index_type = "hnsw"
))]
fn py_create_index(
    index_id: String,
    dimension: usize,
    metric: &str,
    m: usize,
    ef_construction: usize,
    ef_search: usize,
    index_type: &str,
) -> PyResult<()> {
    let dist: DistanceMetric = metric.parse().map_err(engine_err_to_py)?;
    let config = match index_type {
        "flat" => IndexConfig::flat(dimension, dist),
        _ => {
            let mut cfg = IndexConfig::hnsw(dimension, dist);
            cfg.m = m;
            cfg.ef_construction = ef_construction;
            cfg.ef_search = ef_search;
            cfg
        }
    };
    let index = Arc::new(VectorIndex::new(config));
    VECTOR_INDEXES.lock().insert(index_id, index);
    Ok(())
}

#[pyfunction]
fn py_drop_index(index_id: &str) -> bool {
    VECTOR_INDEXES.lock().remove(index_id).is_some()
}

#[pyfunction]
fn py_index_exists(index_id: &str) -> bool {
    VECTOR_INDEXES.lock().contains_key(index_id)
}

#[pyfunction]
fn py_index_add(
    index_id: &str,
    id: String,
    vector: Vec<f32>,
    metadata: Option<String>,
) -> PyResult<()> {
    let indexes = VECTOR_INDEXES.lock();
    let index = indexes
        .get(index_id)
        .ok_or_else(|| PyValueError::new_err(format!("Index '{}' not found", index_id)))?;
    let meta: Option<serde_json::Value> = metadata
        .map(|s| serde_json::from_str(&s))
        .transpose()
        .map_err(|e| PyValueError::new_err(format!("Invalid metadata JSON: {}", e)))?;
    index.add(id, vector, meta).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_index_add_batch(
    index_id: &str,
    ids: Vec<String>,
    vectors: Vec<Vec<f32>>,
    metadata: Option<Vec<Option<String>>>,
) -> PyResult<usize> {
    let indexes = VECTOR_INDEXES.lock();
    let index = indexes
        .get(index_id)
        .ok_or_else(|| PyValueError::new_err(format!("Index '{}' not found", index_id)))?;

    let parsed_meta: Option<Vec<Option<serde_json::Value>>> = metadata
        .map(|list| {
            list.into_iter()
                .map(|m| {
                    m.map(|s| serde_json::from_str(&s))
                        .transpose()
                        .map_err(|e| PyValueError::new_err(format!("Invalid metadata JSON: {}", e)))
                })
                .collect::<PyResult<Vec<_>>>()
        })
        .transpose()?;

    index
        .add_batch(ids, vectors, parsed_meta)
        .map_err(engine_err_to_py)
}

#[pyfunction]
#[pyo3(signature = (index_id, query, k, ef = None, _filter_json = None))]
fn py_index_search(
    index_id: &str,
    query: Vec<f32>,
    k: usize,
    ef: Option<usize>,
    _filter_json: Option<String>,
) -> PyResult<Vec<(String, f32)>> {
    let indexes = VECTOR_INDEXES.lock();
    let index = indexes
        .get(index_id)
        .ok_or_else(|| PyValueError::new_err(format!("Index '{}' not found", index_id)))?;

    let results = index
        .search(&query, k, ef, None)
        .map_err(engine_err_to_py)?;
    Ok(results.into_iter().map(|r| (r.id, r.score)).collect())
}

#[pyfunction]
fn py_index_delete(index_id: &str, id: &str) -> PyResult<bool> {
    let indexes = VECTOR_INDEXES.lock();
    let index = indexes
        .get(index_id)
        .ok_or_else(|| PyValueError::new_err(format!("Index '{}' not found", index_id)))?;
    index.delete(id).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_index_len(index_id: &str) -> PyResult<usize> {
    let indexes = VECTOR_INDEXES.lock();
    let index = indexes
        .get(index_id)
        .ok_or_else(|| PyValueError::new_err(format!("Index '{}' not found", index_id)))?;
    Ok(index.len())
}

#[pyfunction]
fn py_index_stats(py: Python, index_id: &str) -> PyResult<PyObject> {
    let indexes = VECTOR_INDEXES.lock();
    let index = indexes
        .get(index_id)
        .ok_or_else(|| PyValueError::new_err(format!("Index '{}' not found", index_id)))?;
    let stats = index.stats();
    let dict = PyDict::new_bound(py);
    dict.set_item("num_vectors", stats.num_vectors)?;
    dict.set_item("dimension", stats.dimension)?;
    dict.set_item("metric", stats.metric.to_string())?;
    dict.set_item("index_type", stats.index_type)?;
    dict.set_item("memory_bytes", stats.memory_bytes)?;
    dict.set_item("ef_construction", stats.ef_construction)?;
    dict.set_item("m", stats.m)?;
    Ok(dict.into())
}

#[pyfunction]
#[pyo3(signature = (
    ranked_lists,
    strategy = "rrf",
    weights = None,
    rrf_k = 60.0f32,
    top_n = 10usize,
    normalize = true
))]
fn py_fuse_ranked_lists(
    ranked_lists: Vec<Vec<(String, f32)>>,
    strategy: &str,
    weights: Option<Vec<f32>>,
    rrf_k: f32,
    top_n: usize,
    normalize: bool,
) -> PyResult<Vec<(String, f32, usize)>> {
    let reranker_type = match strategy {
        "rrf" | "reciprocal_rank_fusion" => RerankerType::ReciprocalRankFusion,
        "weighted" => RerankerType::WeightedFusion,
        "borda" => RerankerType::Borda,
        "softmax" => RerankerType::SoftmaxFusion,
        "score_norm" | "score_normalization" => RerankerType::ScoreNormalization,
        other => {
            return Err(PyValueError::new_err(format!(
                "Unknown fusion strategy: {}. Use: rrf, weighted, borda, softmax, score_norm",
                other
            )))
        }
    };

    let config = RerankerConfig {
        reranker_type,
        rrf_k,
        weights: weights
            .unwrap_or_else(|| vec![1.0 / ranked_lists.len() as f32; ranked_lists.len()]),
        normalize_before_fusion: normalize,
        normalization_method: NormalizationMethod::MinMax,
        top_n,
        min_score_threshold: 0.0,
        score_clip_min: f32::NEG_INFINITY,
        score_clip_max: f32::INFINITY,
    };

    let fusion = ScoreFusion::new(config);
    let results = fusion.fuse(&ranked_lists).map_err(engine_err_to_py)?;

    Ok(results
        .into_iter()
        .map(|r| (r.id, r.score, r.rank))
        .collect())
}

#[pyfunction]
fn py_compute_ndcg(
    ranked_ids: Vec<String>,
    ranked_scores: Vec<f32>,
    relevant_ids: Vec<String>,
    k: usize,
) -> f32 {
    let results: Vec<RankedResult> = ranked_ids
        .into_iter()
        .zip(ranked_scores)
        .enumerate()
        .map(|(i, (id, score))| RankedResult {
            id,
            rank: i + 1,
            score,
            original_score: None,
            original_rank: None,
        })
        .collect();
    let relevant: std::collections::HashSet<String> = relevant_ids.into_iter().collect();
    compute_ndcg(&results, &relevant, k)
}

#[pyfunction]
fn py_compute_mrr(
    ranked_ids: Vec<String>,
    ranked_scores: Vec<f32>,
    relevant_ids: Vec<String>,
) -> f32 {
    let results: Vec<RankedResult> = ranked_ids
        .into_iter()
        .zip(ranked_scores)
        .enumerate()
        .map(|(i, (id, score))| RankedResult {
            id,
            rank: i + 1,
            score,
            original_score: None,
            original_rank: None,
        })
        .collect();
    let relevant: std::collections::HashSet<String> = relevant_ids.into_iter().collect();
    compute_mrr(&results, &relevant)
}

#[pyfunction]
fn py_compute_precision_at_k(
    ranked_ids: Vec<String>,
    ranked_scores: Vec<f32>,
    relevant_ids: Vec<String>,
    k: usize,
) -> f32 {
    let results: Vec<RankedResult> = ranked_ids
        .into_iter()
        .zip(ranked_scores)
        .enumerate()
        .map(|(i, (id, score))| RankedResult {
            id,
            rank: i + 1,
            score,
            original_score: None,
            original_rank: None,
        })
        .collect();
    let relevant: std::collections::HashSet<String> = relevant_ids.into_iter().collect();
    compute_precision_at_k(&results, &relevant, k)
}

#[pyfunction]
fn py_count_tokens_approximate(text: &str) -> usize {
    count_tokens_approximate(text)
}

#[pyfunction]
fn py_batch_count_tokens_approximate(texts: Vec<String>) -> Vec<usize> {
    batch_count_tokens_approximate(&texts)
}

#[pyfunction]
fn py_fits_in_context(text: &str, max_tokens: usize, overhead: usize) -> bool {
    fits_in_context(text, max_tokens, overhead)
}

#[pyfunction]
fn py_compress(data: Vec<u8>, algorithm: &str, zstd_level: Option<i32>) -> PyResult<Vec<u8>> {
    let alg = match algorithm {
        "lz4" => crate::compression::CompressionAlgorithm::Lz4,
        "zstd" => crate::compression::CompressionAlgorithm::Zstd,
        "snappy" => crate::compression::CompressionAlgorithm::Snappy,
        "none" => crate::compression::CompressionAlgorithm::None,
        other => {
            return Err(PyValueError::new_err(format!(
                "Unknown algorithm: {}",
                other
            )))
        }
    };
    let config = CompressionConfig {
        algorithm: alg,
        zstd_level: zstd_level.unwrap_or(3),
        min_size_to_compress: 0,
        max_decompressed_size: 256 * 1024 * 1024,
    };
    let (compressed, _) = compress(&data, &config).map_err(engine_err_to_py)?;
    Ok(compressed)
}

#[pyfunction]
fn py_decompress(data: Vec<u8>, algorithm: &str) -> PyResult<Vec<u8>> {
    let alg = match algorithm {
        "lz4" => crate::compression::CompressionAlgorithm::Lz4,
        "zstd" => crate::compression::CompressionAlgorithm::Zstd,
        "snappy" => crate::compression::CompressionAlgorithm::Snappy,
        "none" => crate::compression::CompressionAlgorithm::None,
        other => {
            return Err(PyValueError::new_err(format!(
                "Unknown algorithm: {}",
                other
            )))
        }
    };
    let config = CompressionConfig {
        algorithm: alg,
        zstd_level: 3,
        min_size_to_compress: 0,
        max_decompressed_size: 256 * 1024 * 1024,
    };
    decompress(&data, &config).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_compress_vectors(vectors: Vec<Vec<f32>>, algorithm: &str) -> PyResult<Vec<u8>> {
    let alg = match algorithm {
        "lz4" => crate::compression::CompressionAlgorithm::Lz4,
        "zstd" => crate::compression::CompressionAlgorithm::Zstd,
        "snappy" => crate::compression::CompressionAlgorithm::Snappy,
        _ => crate::compression::CompressionAlgorithm::Lz4,
    };
    let config = CompressionConfig {
        algorithm: alg,
        ..Default::default()
    };
    let (compressed, _) = compress_vectors(&vectors, &config).map_err(engine_err_to_py)?;
    Ok(compressed)
}

#[pyfunction]
fn py_decompress_vectors(data: Vec<u8>, algorithm: &str) -> PyResult<Vec<Vec<f32>>> {
    let alg = match algorithm {
        "lz4" => crate::compression::CompressionAlgorithm::Lz4,
        "zstd" => crate::compression::CompressionAlgorithm::Zstd,
        "snappy" => crate::compression::CompressionAlgorithm::Snappy,
        _ => crate::compression::CompressionAlgorithm::Lz4,
    };
    let config = CompressionConfig {
        algorithm: alg,
        ..Default::default()
    };
    decompress_vectors(&data, &config).map_err(engine_err_to_py)
}

#[pyfunction]
#[pyo3(signature = (vectors, quantile = 0.99f32))]
fn py_quantize_scalar_i8(
    vectors: Vec<Vec<f32>>,
    quantile: f32,
) -> PyResult<(Vec<Vec<i8>>, f32, f32)> {
    quantize_scalar_i8(&vectors, quantile).map_err(engine_err_to_py)
}

#[pyfunction]
fn py_dequantize_scalar_i8(quantized: Vec<Vec<i8>>, min_val: f32, max_val: f32) -> Vec<Vec<f32>> {
    dequantize_scalar_i8(&quantized, min_val, max_val)
}

#[pyfunction]
fn py_embedding_cache_get(text: &str, model: &str) -> Option<Vec<f32>> {
    EMBEDDING_CACHE.get(text, model)
}

#[pyfunction]
fn py_embedding_cache_set(text: &str, model: &str, embedding: Vec<f32>) {
    EMBEDDING_CACHE.insert(text, model, embedding);
}

#[pyfunction]
fn py_embedding_cache_contains(text: &str, model: &str) -> bool {
    EMBEDDING_CACHE.contains(text, model)
}

#[pyfunction]
fn py_embedding_cache_invalidate(text: &str, model: &str) {
    EMBEDDING_CACHE.invalidate(text, model);
}

#[pyfunction]
fn py_embedding_cache_clear() {
    EMBEDDING_CACHE.clear();
}

#[pyfunction]
fn py_embedding_cache_stats(py: Python) -> PyResult<PyObject> {
    let stats = EMBEDDING_CACHE.stats();
    let dict = PyDict::new_bound(py);
    dict.set_item("hits", stats.hits)?;
    dict.set_item("misses", stats.misses)?;
    dict.set_item("evictions", stats.evictions)?;
    dict.set_item("current_size", stats.current_size)?;
    dict.set_item("capacity", stats.capacity)?;
    dict.set_item("hit_rate", stats.hit_rate)?;
    dict.set_item("memory_bytes", stats.memory_bytes)?;
    Ok(dict.into())
}

#[pyfunction]
fn py_engine_version() -> &'static str {
    crate::VERSION
}

#[pyfunction]
fn py_engine_name() -> &'static str {
    crate::NAME
}

#[pymodule]
fn neuralcore_engine(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_cosine_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(py_dot_product, m)?)?;
    m.add_function(wrap_pyfunction!(py_euclidean_distance, m)?)?;
    m.add_function(wrap_pyfunction!(py_euclidean_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_cosine_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_dot_product, m)?)?;
    m.add_function(wrap_pyfunction!(py_top_k_by_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(py_normalize_vector, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_normalize_vectors, m)?)?;
    m.add_function(wrap_pyfunction!(py_min_max_normalize, m)?)?;
    m.add_function(wrap_pyfunction!(py_softmax, m)?)?;
    m.add_function(wrap_pyfunction!(py_reciprocal_rank_fusion, m)?)?;

    m.add_function(wrap_pyfunction!(py_create_index, m)?)?;
    m.add_function(wrap_pyfunction!(py_drop_index, m)?)?;
    m.add_function(wrap_pyfunction!(py_index_exists, m)?)?;
    m.add_function(wrap_pyfunction!(py_index_add, m)?)?;
    m.add_function(wrap_pyfunction!(py_index_add_batch, m)?)?;
    m.add_function(wrap_pyfunction!(py_index_search, m)?)?;
    m.add_function(wrap_pyfunction!(py_index_delete, m)?)?;
    m.add_function(wrap_pyfunction!(py_index_len, m)?)?;
    m.add_function(wrap_pyfunction!(py_index_stats, m)?)?;

    m.add_function(wrap_pyfunction!(py_fuse_ranked_lists, m)?)?;
    m.add_function(wrap_pyfunction!(py_compute_ndcg, m)?)?;
    m.add_function(wrap_pyfunction!(py_compute_mrr, m)?)?;
    m.add_function(wrap_pyfunction!(py_compute_precision_at_k, m)?)?;

    m.add_function(wrap_pyfunction!(py_count_tokens_approximate, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_count_tokens_approximate, m)?)?;
    m.add_function(wrap_pyfunction!(py_fits_in_context, m)?)?;

    m.add_function(wrap_pyfunction!(py_compress, m)?)?;
    m.add_function(wrap_pyfunction!(py_decompress, m)?)?;
    m.add_function(wrap_pyfunction!(py_compress_vectors, m)?)?;
    m.add_function(wrap_pyfunction!(py_decompress_vectors, m)?)?;
    m.add_function(wrap_pyfunction!(py_quantize_scalar_i8, m)?)?;
    m.add_function(wrap_pyfunction!(py_dequantize_scalar_i8, m)?)?;

    m.add_function(wrap_pyfunction!(py_embedding_cache_get, m)?)?;
    m.add_function(wrap_pyfunction!(py_embedding_cache_set, m)?)?;
    m.add_function(wrap_pyfunction!(py_embedding_cache_contains, m)?)?;
    m.add_function(wrap_pyfunction!(py_embedding_cache_invalidate, m)?)?;
    m.add_function(wrap_pyfunction!(py_embedding_cache_clear, m)?)?;
    m.add_function(wrap_pyfunction!(py_embedding_cache_stats, m)?)?;

    m.add_function(wrap_pyfunction!(py_engine_version, m)?)?;
    m.add_function(wrap_pyfunction!(py_engine_name, m)?)?;

    m.add("__version__", crate::VERSION)?;
    m.add("__name__", crate::NAME)?;

    Ok(())
}
