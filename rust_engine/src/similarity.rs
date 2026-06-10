// rust_engine/src/similarity.rs

use crate::error::{EngineError, EngineResult};
use crate::types::{DistanceMetric, Score, VectorSlice};
use crate::utils::{l2_norm, validate_dimension_match, validate_vector};
use rayon::prelude::*;

#[inline(always)]
pub fn cosine_similarity(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    validate_dimension_match(a.len(), b.len())?;
    validate_vector(a, "cosine_similarity:a")?;
    validate_vector(b, "cosine_similarity:b")?;

    let (dot, norm_a, norm_b) = compute_dot_and_norms(a, b);

    if norm_a < f32::EPSILON || norm_b < f32::EPSILON {
        return Ok(0.0);
    }

    Ok((dot / (norm_a * norm_b)).clamp(-1.0, 1.0))
}

#[inline(always)]
pub fn cosine_similarity_prenormalized(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    validate_dimension_match(a.len(), b.len())?;
    let dot = dot_product_raw(a, b);
    Ok(dot.clamp(-1.0, 1.0))
}

#[inline(always)]
pub fn dot_product(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    validate_dimension_match(a.len(), b.len())?;
    validate_vector(a, "dot_product:a")?;
    validate_vector(b, "dot_product:b")?;
    Ok(dot_product_raw(a, b))
}

#[inline(always)]
pub fn euclidean_distance(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    validate_dimension_match(a.len(), b.len())?;
    validate_vector(a, "euclidean_distance:a")?;
    validate_vector(b, "euclidean_distance:b")?;
    let dist_sq: f32 = a.iter().zip(b.iter()).map(|(x, y)| (x - y).powi(2)).sum();
    Ok(dist_sq.sqrt())
}

#[inline(always)]
pub fn euclidean_similarity(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    let dist = euclidean_distance(a, b)?;
    Ok(1.0 / (1.0 + dist))
}

#[inline(always)]
pub fn squared_euclidean_distance(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    validate_dimension_match(a.len(), b.len())?;
    validate_vector(a, "squared_euclidean:a")?;
    validate_vector(b, "squared_euclidean:b")?;
    Ok(a.iter().zip(b.iter()).map(|(x, y)| (x - y).powi(2)).sum())
}

#[inline(always)]
pub fn manhattan_distance(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    validate_dimension_match(a.len(), b.len())?;
    validate_vector(a, "manhattan_distance:a")?;
    validate_vector(b, "manhattan_distance:b")?;
    Ok(a.iter().zip(b.iter()).map(|(x, y)| (x - y).abs()).sum())
}

#[inline(always)]
pub fn manhattan_similarity(a: VectorSlice, b: VectorSlice) -> EngineResult<Score> {
    let dist = manhattan_distance(a, b)?;
    Ok(1.0 / (1.0 + dist))
}

pub fn compute_similarity(
    a: VectorSlice,
    b: VectorSlice,
    metric: DistanceMetric,
    prenormalized: bool,
) -> EngineResult<Score> {
    match metric {
        DistanceMetric::Cosine => {
            if prenormalized {
                cosine_similarity_prenormalized(a, b)
            } else {
                cosine_similarity(a, b)
            }
        }
        DistanceMetric::DotProduct => dot_product(a, b),
        DistanceMetric::Euclidean => euclidean_similarity(a, b),
        DistanceMetric::Manhattan => manhattan_similarity(a, b),
    }
}

pub fn batch_cosine_similarity(
    query: VectorSlice,
    vectors: &[Vec<f32>],
    prenormalized: bool,
) -> EngineResult<Vec<Score>> {
    if vectors.is_empty() {
        return Ok(Vec::new());
    }

    validate_vector(query, "batch_cosine:query")?;

    if let Some(first) = vectors.first() {
        validate_dimension_match(query.len(), first.len())?;
    }

    let query_norm = if prenormalized {
        1.0f32
    } else {
        let n = l2_norm(query);
        if n < f32::EPSILON {
            return Ok(vec![0.0; vectors.len()]);
        }
        n
    };

    let scores: Vec<Score> = vectors
        .par_iter()
        .map(|v| {
            let dot: f32 = query.iter().zip(v.iter()).map(|(a, b)| a * b).sum();
            if prenormalized {
                dot.clamp(-1.0, 1.0)
            } else {
                let v_norm = l2_norm(v);
                if v_norm < f32::EPSILON {
                    0.0
                } else {
                    (dot / (query_norm * v_norm)).clamp(-1.0, 1.0)
                }
            }
        })
        .collect();

    Ok(scores)
}

pub fn batch_dot_product(query: VectorSlice, vectors: &[Vec<f32>]) -> EngineResult<Vec<Score>> {
    if vectors.is_empty() {
        return Ok(Vec::new());
    }
    validate_vector(query, "batch_dot_product:query")?;
    if let Some(first) = vectors.first() {
        validate_dimension_match(query.len(), first.len())?;
    }
    let scores: Vec<Score> = vectors
        .par_iter()
        .map(|v| query.iter().zip(v.iter()).map(|(a, b)| a * b).sum())
        .collect();
    Ok(scores)
}

pub fn batch_euclidean_similarity(
    query: VectorSlice,
    vectors: &[Vec<f32>],
) -> EngineResult<Vec<Score>> {
    if vectors.is_empty() {
        return Ok(Vec::new());
    }
    validate_vector(query, "batch_euclidean:query")?;
    if let Some(first) = vectors.first() {
        validate_dimension_match(query.len(), first.len())?;
    }
    let scores: Vec<Score> = vectors
        .par_iter()
        .map(|v| {
            let dist_sq: f32 = query
                .iter()
                .zip(v.iter())
                .map(|(a, b)| (a - b).powi(2))
                .sum();
            1.0 / (1.0 + dist_sq.sqrt())
        })
        .collect();
    Ok(scores)
}

pub fn batch_similarity(
    query: VectorSlice,
    vectors: &[Vec<f32>],
    metric: DistanceMetric,
    prenormalized: bool,
) -> EngineResult<Vec<Score>> {
    match metric {
        DistanceMetric::Cosine => batch_cosine_similarity(query, vectors, prenormalized),
        DistanceMetric::DotProduct => batch_dot_product(query, vectors),
        DistanceMetric::Euclidean => batch_euclidean_similarity(query, vectors),
        DistanceMetric::Manhattan => {
            if vectors.is_empty() {
                return Ok(Vec::new());
            }
            validate_vector(query, "batch_manhattan:query")?;
            let scores: Vec<Score> = vectors
                .par_iter()
                .map(|v| {
                    let dist: f32 = query.iter().zip(v.iter()).map(|(a, b)| (a - b).abs()).sum();
                    1.0 / (1.0 + dist)
                })
                .collect();
            Ok(scores)
        }
    }
}

pub fn top_k_by_similarity(
    query: VectorSlice,
    vectors: &[Vec<f32>],
    ids: &[String],
    k: usize,
    metric: DistanceMetric,
    prenormalized: bool,
) -> EngineResult<Vec<(String, Score)>> {
    if vectors.len() != ids.len() {
        return Err(EngineError::InvalidParameter {
            name: "ids",
            value: format!("len={}", ids.len()),
            reason: "ids length must equal vectors length",
        });
    }

    let k = k.min(vectors.len());
    if k == 0 {
        return Ok(Vec::new());
    }

    let scores = batch_similarity(query, vectors, metric, prenormalized)?;

    let mut indexed: Vec<(usize, Score)> = scores.into_iter().enumerate().collect();

    if k < indexed.len() {
        indexed.select_nth_unstable_by(k - 1, |a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
        });
        indexed.truncate(k);
    }

    indexed.sort_unstable_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    Ok(indexed
        .into_iter()
        .map(|(idx, score)| (ids[idx].clone(), score))
        .collect())
}

pub fn pairwise_similarity_matrix(
    vectors_a: &[Vec<f32>],
    vectors_b: &[Vec<f32>],
    metric: DistanceMetric,
    prenormalized: bool,
) -> EngineResult<Vec<Vec<Score>>> {
    if vectors_a.is_empty() || vectors_b.is_empty() {
        return Ok(Vec::new());
    }

    let dim_a = vectors_a[0].len();
    let dim_b = vectors_b[0].len();
    validate_dimension_match(dim_a, dim_b)?;

    let matrix: EngineResult<Vec<Vec<Score>>> = vectors_a
        .par_iter()
        .map(|a| batch_similarity(a, vectors_b, metric, prenormalized))
        .collect();

    matrix
}

pub fn self_similarity_matrix(
    vectors: &[Vec<f32>],
    metric: DistanceMetric,
    prenormalized: bool,
) -> EngineResult<Vec<Vec<Score>>> {
    pairwise_similarity_matrix(vectors, vectors, metric, prenormalized)
}

pub fn average_similarity(
    query: VectorSlice,
    vectors: &[Vec<f32>],
    metric: DistanceMetric,
    prenormalized: bool,
) -> EngineResult<Score> {
    if vectors.is_empty() {
        return Ok(0.0);
    }
    let scores = batch_similarity(query, vectors, metric, prenormalized)?;
    Ok(scores.iter().sum::<f32>() / scores.len() as f32)
}

pub fn max_similarity(
    query: VectorSlice,
    vectors: &[Vec<f32>],
    metric: DistanceMetric,
    prenormalized: bool,
) -> EngineResult<Score> {
    if vectors.is_empty() {
        return Ok(f32::NEG_INFINITY);
    }
    let scores = batch_similarity(query, vectors, metric, prenormalized)?;
    Ok(scores.iter().cloned().fold(f32::NEG_INFINITY, f32::max))
}

#[inline(always)]
fn dot_product_raw(a: &[f32], b: &[f32]) -> f32 {
    let mut dot = 0.0f32;
    let chunks = a.len() / 8;
    let remainder = a.len() % 8;

    for i in 0..chunks {
        let base = i * 8;
        dot += a[base] * b[base]
            + a[base + 1] * b[base + 1]
            + a[base + 2] * b[base + 2]
            + a[base + 3] * b[base + 3]
            + a[base + 4] * b[base + 4]
            + a[base + 5] * b[base + 5]
            + a[base + 6] * b[base + 6]
            + a[base + 7] * b[base + 7];
    }

    let base = chunks * 8;
    for i in 0..remainder {
        dot += a[base + i] * b[base + i];
    }

    dot
}

#[inline(always)]
fn compute_dot_and_norms(a: &[f32], b: &[f32]) -> (f32, f32, f32) {
    let mut dot = 0.0f32;
    let mut norm_a_sq = 0.0f32;
    let mut norm_b_sq = 0.0f32;

    let chunks = a.len() / 4;
    let remainder = a.len() % 4;

    for i in 0..chunks {
        let base = i * 4;
        let a0 = a[base];
        let a1 = a[base + 1];
        let a2 = a[base + 2];
        let a3 = a[base + 3];
        let b0 = b[base];
        let b1 = b[base + 1];
        let b2 = b[base + 2];
        let b3 = b[base + 3];
        dot += a0 * b0 + a1 * b1 + a2 * b2 + a3 * b3;
        norm_a_sq += a0 * a0 + a1 * a1 + a2 * a2 + a3 * a3;
        norm_b_sq += b0 * b0 + b1 * b1 + b2 * b2 + b3 * b3;
    }

    let base = chunks * 4;
    for i in 0..remainder {
        dot += a[base + i] * b[base + i];
        norm_a_sq += a[base + i] * a[base + i];
        norm_b_sq += b[base + i] * b[base + i];
    }

    (dot, norm_a_sq.sqrt(), norm_b_sq.sqrt())
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    #[test]
    fn test_cosine_similarity_identical_vectors() {
        let v = vec![1.0f32, 2.0, 3.0, 4.0];
        let result = cosine_similarity(&v, &v).unwrap();
        assert_relative_eq!(result, 1.0, epsilon = 1e-6);
    }

    #[test]
    fn test_cosine_similarity_orthogonal_vectors() {
        let a = vec![1.0f32, 0.0];
        let b = vec![0.0f32, 1.0];
        let result = cosine_similarity(&a, &b).unwrap();
        assert_relative_eq!(result, 0.0, epsilon = 1e-6);
    }

    #[test]
    fn test_cosine_similarity_opposite_vectors() {
        let a = vec![1.0f32, 0.0];
        let b = vec![-1.0f32, 0.0];
        let result = cosine_similarity(&a, &b).unwrap();
        assert_relative_eq!(result, -1.0, epsilon = 1e-6);
    }

    #[test]
    fn test_dot_product_known_result() {
        let a = vec![1.0f32, 2.0, 3.0];
        let b = vec![4.0f32, 5.0, 6.0];
        let result = dot_product(&a, &b).unwrap();
        assert_relative_eq!(result, 32.0, epsilon = 1e-5);
    }

    #[test]
    fn test_euclidean_distance_known_result() {
        let a = vec![0.0f32, 0.0, 0.0];
        let b = vec![3.0f32, 4.0, 0.0];
        let result = euclidean_distance(&a, &b).unwrap();
        assert_relative_eq!(result, 5.0, epsilon = 1e-5);
    }

    #[test]
    fn test_dimension_mismatch_error() {
        let a = vec![1.0f32, 2.0];
        let b = vec![1.0f32, 2.0, 3.0];
        let result = cosine_similarity(&a, &b);
        assert!(result.is_err());
        assert!(matches!(result, Err(EngineError::DimensionMismatch { .. })));
    }

    #[test]
    fn test_batch_cosine_similarity_correctness() {
        let query = vec![1.0f32, 0.0, 0.0];
        let vectors = vec![
            vec![1.0f32, 0.0, 0.0],
            vec![0.0f32, 1.0, 0.0],
            vec![-1.0f32, 0.0, 0.0],
        ];
        let scores = batch_cosine_similarity(&query, &vectors, false).unwrap();
        assert_relative_eq!(scores[0], 1.0, epsilon = 1e-6);
        assert_relative_eq!(scores[1], 0.0, epsilon = 1e-6);
        assert_relative_eq!(scores[2], -1.0, epsilon = 1e-6);
    }

    #[test]
    fn test_top_k_by_similarity_ordering() {
        let query = vec![1.0f32, 0.0];
        let vectors = vec![vec![0.5f32, 0.0], vec![1.0f32, 0.0], vec![0.1f32, 0.0]];
        let ids = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        let results =
            top_k_by_similarity(&query, &vectors, &ids, 2, DistanceMetric::DotProduct, false)
                .unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].0, "b");
        assert_eq!(results[1].0, "a");
    }

    #[test]
    fn test_nan_in_vector_rejected() {
        let a = vec![1.0f32, f32::NAN];
        let b = vec![1.0f32, 0.0];
        let result = cosine_similarity(&a, &b);
        assert!(result.is_err());
    }
}
