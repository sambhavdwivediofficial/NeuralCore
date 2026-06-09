// rust_engine/src/lib.rs

pub mod cache;
pub mod compression;
pub mod ffi;
pub mod reranker;
pub mod similarity;
pub mod tokenizer;
pub mod vector_index;

pub mod error {
    use thiserror::Error;

    #[derive(Debug, Error)]
    pub enum EngineError {
        #[error("Dimension mismatch: expected {expected}, got {actual}")]
        DimensionMismatch { expected: usize, actual: usize },

        #[error("Empty input: {context}")]
        EmptyInput { context: &'static str },

        #[error("Invalid parameter: {name} = {value}, reason: {reason}")]
        InvalidParameter {
            name: &'static str,
            value: String,
            reason: &'static str,
        },

        #[error("Index error: {0}")]
        IndexError(String),

        #[error("Serialization error: {0}")]
        SerializationError(String),

        #[error("Compression error: {0}")]
        CompressionError(String),

        #[error("Tokenization error: {0}")]
        TokenizationError(String),

        #[error("Cache error: {0}")]
        CacheError(String),

        #[error("Reranker error: {0}")]
        RerankerError(String),

        #[error("IO error: {0}")]
        IoError(#[from] std::io::Error),

        #[error("Arithmetic overflow in {context}")]
        ArithmeticOverflow { context: &'static str },

        #[error("NaN detected in vector at index {index}")]
        NanDetected { index: usize },

        #[error("Infinite value detected in vector at index {index}")]
        InfDetected { index: usize },

        #[error("Zero vector detected")]
        ZeroVector,

        #[error("Capacity exceeded: {resource} capacity is {capacity}, attempted {attempted}")]
        CapacityExceeded {
            resource: &'static str,
            capacity: usize,
            attempted: usize,
        },

        #[error("Not found: {key}")]
        NotFound { key: String },

        #[error("Poisoned lock in {context}")]
        PoisonedLock { context: &'static str },

        #[error("ONNX runtime error: {0}")]
        OnnxError(String),
    }

    pub type EngineResult<T> = Result<T, EngineError>;
}

pub mod types {
    use serde::{Deserialize, Serialize};
    use std::fmt;

    pub type Vector = Vec<f32>;
    pub type VectorSlice<'a> = &'a [f32];
    pub type DocumentId = String;
    pub type Score = f32;
    pub type TokenId = u32;

    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub enum DistanceMetric {
        Cosine,
        DotProduct,
        Euclidean,
        Manhattan,
    }

    impl fmt::Display for DistanceMetric {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            match self {
                DistanceMetric::Cosine => write!(f, "cosine"),
                DistanceMetric::DotProduct => write!(f, "dot_product"),
                DistanceMetric::Euclidean => write!(f, "euclidean"),
                DistanceMetric::Manhattan => write!(f, "manhattan"),
            }
        }
    }

    impl std::str::FromStr for DistanceMetric {
        type Err = crate::error::EngineError;

        fn from_str(s: &str) -> Result<Self, Self::Err> {
            match s.to_lowercase().as_str() {
                "cosine" => Ok(DistanceMetric::Cosine),
                "dot_product" | "dot" | "inner_product" => Ok(DistanceMetric::DotProduct),
                "euclidean" | "l2" => Ok(DistanceMetric::Euclidean),
                "manhattan" | "l1" => Ok(DistanceMetric::Manhattan),
                other => Err(crate::error::EngineError::InvalidParameter {
                    name: "distance_metric",
                    value: other.to_string(),
                    reason: "must be one of: cosine, dot_product, euclidean, manhattan",
                }),
            }
        }
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct SearchResult {
        pub id: DocumentId,
        pub score: Score,
        pub vector: Option<Vector>,
        pub metadata: Option<serde_json::Value>,
    }

    impl SearchResult {
        pub fn new(id: DocumentId, score: Score) -> Self {
            Self {
                id,
                score,
                vector: None,
                metadata: None,
            }
        }

        pub fn with_vector(mut self, vector: Vector) -> Self {
            self.vector = Some(vector);
            self
        }

        pub fn with_metadata(mut self, metadata: serde_json::Value) -> Self {
            self.metadata = Some(metadata);
            self
        }
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct RankedResult {
        pub id: DocumentId,
        pub rank: usize,
        pub score: Score,
        pub original_score: Option<Score>,
        pub original_rank: Option<usize>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct TokenizerOutput {
        pub input_ids: Vec<TokenId>,
        pub attention_mask: Vec<u8>,
        pub token_type_ids: Option<Vec<u8>>,
        pub special_tokens_mask: Option<Vec<u8>>,
        pub offsets: Option<Vec<(usize, usize)>>,
        pub tokens: Option<Vec<String>>,
        pub num_tokens: usize,
        pub was_truncated: bool,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct BatchTokenizerOutput {
        pub input_ids: Vec<Vec<TokenId>>,
        pub attention_mask: Vec<Vec<u8>>,
        pub token_type_ids: Option<Vec<Vec<u8>>>,
        pub num_tokens: Vec<usize>,
        pub was_truncated: Vec<bool>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct IndexStats {
        pub num_vectors: usize,
        pub dimension: usize,
        pub metric: DistanceMetric,
        pub index_type: String,
        pub memory_bytes: usize,
        pub num_levels: Option<usize>,
        pub ef_construction: Option<usize>,
        pub m: Option<usize>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct CompressionStats {
        pub original_size_bytes: usize,
        pub compressed_size_bytes: usize,
        pub compression_ratio: f64,
        pub algorithm: String,
        pub duration_micros: u64,
    }

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct CacheStats {
        pub hits: u64,
        pub misses: u64,
        pub evictions: u64,
        pub current_size: usize,
        pub capacity: usize,
        pub hit_rate: f64,
        pub memory_bytes: usize,
    }
}

pub mod utils {
    use crate::error::{EngineError, EngineResult};
    use crate::types::Vector;

    pub fn validate_vector(v: &[f32], context: &'static str) -> EngineResult<()> {
        if v.is_empty() {
            return Err(EngineError::EmptyInput { context });
        }
        for (i, &val) in v.iter().enumerate() {
            if val.is_nan() {
                return Err(EngineError::NanDetected { index: i });
            }
            if val.is_infinite() {
                return Err(EngineError::InfDetected { index: i });
            }
        }
        Ok(())
    }

    pub fn validate_dimension_match(
        a_dim: usize,
        b_dim: usize,
    ) -> EngineResult<()> {
        if a_dim != b_dim {
            return Err(EngineError::DimensionMismatch {
                expected: a_dim,
                actual: b_dim,
            });
        }
        Ok(())
    }

    pub fn l2_norm(v: &[f32]) -> f32 {
        v.iter().map(|x| x * x).sum::<f32>().sqrt()
    }

    pub fn normalize_vector(v: &mut [f32]) {
        let norm = l2_norm(v);
        if norm > f32::EPSILON {
            let inv_norm = 1.0 / norm;
            for x in v.iter_mut() {
                *x *= inv_norm;
            }
        }
    }

    pub fn normalize_vector_new(v: &[f32]) -> Vector {
        let mut result = v.to_vec();
        normalize_vector(&mut result);
        result
    }

    pub fn is_zero_vector(v: &[f32]) -> bool {
        v.iter().all(|&x| x.abs() < f32::EPSILON)
    }

    pub fn clamp_score(score: f32) -> f32 {
        score.clamp(-1.0, 1.0)
    }

    pub fn sigmoid(x: f32) -> f32 {
        1.0 / (1.0 + (-x).exp())
    }

    pub fn softmax(scores: &[f32]) -> Vec<f32> {
        if scores.is_empty() {
            return Vec::new();
        }
        let max_score = scores.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let exps: Vec<f32> = scores.iter().map(|&s| (s - max_score).exp()).collect();
        let sum: f32 = exps.iter().sum();
        if sum < f32::EPSILON {
            vec![1.0 / scores.len() as f32; scores.len()]
        } else {
            exps.iter().map(|&e| e / sum).collect()
        }
    }

    pub fn min_max_normalize(scores: &[f32]) -> Vec<f32> {
        if scores.is_empty() {
            return Vec::new();
        }
        let min = scores.iter().cloned().fold(f32::INFINITY, f32::min);
        let max = scores.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let range = max - min;
        if range < f32::EPSILON {
            return vec![1.0; scores.len()];
        }
        scores.iter().map(|&s| (s - min) / range).collect()
    }

    pub fn reciprocal_rank_fusion(
        ranked_lists: &[Vec<(String, usize)>],
        k: f32,
    ) -> Vec<(String, f32)> {
        let mut scores: std::collections::HashMap<String, f32> =
            std::collections::HashMap::new();
        for list in ranked_lists {
            for (id, rank) in list {
                let rrf_score = 1.0 / (k + *rank as f32);
                *scores.entry(id.clone()).or_insert(0.0) += rrf_score;
            }
        }
        let mut result: Vec<(String, f32)> = scores.into_iter().collect();
        result.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        result
    }
}

pub const VERSION: &str = env!("CARGO_PKG_VERSION");
pub const NAME: &str = env!("CARGO_PKG_NAME");

#[cfg(test)]
mod tests {
    use super::utils::*;

    #[test]
    fn test_l2_norm_unit_vector() {
        let v = vec![1.0f32, 0.0, 0.0];
        let norm = l2_norm(&v);
        assert!((norm - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_normalize_vector_is_unit() {
        let mut v = vec![3.0f32, 4.0, 0.0];
        normalize_vector(&mut v);
        let norm = l2_norm(&v);
        assert!((norm - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_softmax_sums_to_one() {
        let scores = vec![1.0f32, 2.0, 3.0];
        let result = softmax(&scores);
        let sum: f32 = result.iter().sum();
        assert!((sum - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_min_max_normalize_bounds() {
        let scores = vec![1.0f32, 2.0, 3.0, 4.0, 5.0];
        let result = min_max_normalize(&scores);
        assert!((result[0] - 0.0).abs() < 1e-6);
        assert!((result[4] - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_rrf_combines_lists() {
        let list1 = vec![("a".to_string(), 1), ("b".to_string(), 2)];
        let list2 = vec![("b".to_string(), 1), ("a".to_string(), 2)];
        let result = reciprocal_rank_fusion(&[list1, list2], 60.0);
        assert_eq!(result.len(), 2);
        assert!((result[0].1 - result[1].1).abs() < 1e-6);
    }

    #[test]
    fn test_validate_vector_nan_rejected() {
        let v = vec![1.0f32, f32::NAN, 0.0];
        assert!(validate_vector(&v, "test").is_err());
    }

    #[test]
    fn test_validate_vector_inf_rejected() {
        let v = vec![1.0f32, f32::INFINITY, 0.0];
        assert!(validate_vector(&v, "test").is_err());
    }

    #[test]
    fn test_is_zero_vector() {
        let v = vec![0.0f32, 0.0, 0.0];
        assert!(is_zero_vector(&v));
        let v2 = vec![0.0f32, 0.001, 0.0];
        assert!(!is_zero_vector(&v2));
    }
}