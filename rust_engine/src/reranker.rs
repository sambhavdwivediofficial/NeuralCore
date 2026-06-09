// rust_engine/src/reranker.rs

use crate::error::{EngineError, EngineResult};
use crate::types::{RankedResult, Score};
// use crate::utils::{min_max_normalize, reciprocal_rank_fusion, softmax};
use crate::utils::{min_max_normalize, softmax};
// use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RerankerType {
    ScoreNormalization,
    ReciprocalRankFusion,
    WeightedFusion,
    Borda,
    LinearCombination,
    SoftmaxFusion,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RerankerConfig {
    pub reranker_type: RerankerType,
    pub rrf_k: f32,
    pub weights: Vec<f32>,
    pub normalize_before_fusion: bool,
    pub normalization_method: NormalizationMethod,
    pub top_n: usize,
    pub min_score_threshold: f32,
    pub score_clip_min: f32,
    pub score_clip_max: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NormalizationMethod {
    MinMax,
    Softmax,
    Sigmoid,
    ZScore,
    None,
}

impl Default for RerankerConfig {
    fn default() -> Self {
        Self {
            reranker_type: RerankerType::ReciprocalRankFusion,
            rrf_k: 60.0,
            weights: vec![0.5, 0.5],
            normalize_before_fusion: true,
            normalization_method: NormalizationMethod::MinMax,
            top_n: 10,
            min_score_threshold: 0.0,
            score_clip_min: -1.0,
            score_clip_max: 1.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredDocument {
    pub id: String,
    pub score: Score,
    pub rank: usize,
    pub source_scores: Vec<Score>,
    pub source_ranks: Vec<usize>,
    pub metadata: Option<serde_json::Value>,
}

impl ScoredDocument {
    pub fn new(id: String, score: Score, rank: usize) -> Self {
        Self {
            id,
            score,
            rank,
            source_scores: Vec::new(),
            source_ranks: Vec::new(),
            metadata: None,
        }
    }
}

pub struct ScoreFusion {
    config: RerankerConfig,
}

impl ScoreFusion {
    pub fn new(config: RerankerConfig) -> Self {
        Self { config }
    }

    pub fn fuse(
        &self,
        ranked_lists: &[Vec<(String, Score)>],
    ) -> EngineResult<Vec<ScoredDocument>> {
        if ranked_lists.is_empty() {
            return Ok(Vec::new());
        }

        for (i, list) in ranked_lists.iter().enumerate() {
            if list.is_empty() {
                continue;
            }
            if !list.iter().all(|(_, s)| s.is_finite()) {
                return Err(EngineError::InvalidParameter {
                    name: "ranked_lists",
                    value: format!("list[{}]", i),
                    reason: "all scores must be finite",
                });
            }
        }

        match &self.config.reranker_type {
            RerankerType::ReciprocalRankFusion => self.rrf_fusion(ranked_lists),
            RerankerType::WeightedFusion => self.weighted_fusion(ranked_lists),
            RerankerType::ScoreNormalization => self.score_normalization_fusion(ranked_lists),
            RerankerType::Borda => self.borda_fusion(ranked_lists),
            RerankerType::LinearCombination => self.linear_combination_fusion(ranked_lists),
            RerankerType::SoftmaxFusion => self.softmax_fusion(ranked_lists),
        }
    }

    fn rrf_fusion(
        &self,
        ranked_lists: &[Vec<(String, Score)>],
    ) -> EngineResult<Vec<ScoredDocument>> {
        let k = self.config.rrf_k;
        let mut id_to_scores: std::collections::HashMap<String, (f32, Vec<Score>, Vec<usize>)> =
            std::collections::HashMap::new();

        for list in ranked_lists {
            for (rank, (id, score)) in list.iter().enumerate() {
                let rrf = 1.0 / (k + rank as f32 + 1.0);
                let entry = id_to_scores
                    .entry(id.clone())
                    .or_insert((0.0, Vec::new(), Vec::new()));
                entry.0 += rrf;
                entry.1.push(*score);
                entry.2.push(rank + 1);
            }
        }

        let mut results: Vec<ScoredDocument> = id_to_scores
            .into_iter()
            .map(|(id, (score, source_scores, source_ranks))| ScoredDocument {
                id,
                score,
                rank: 0,
                source_scores,
                source_ranks,
                metadata: None,
            })
            .collect();

        self.finalize_results(&mut results);
        Ok(results)
    }

    fn weighted_fusion(
        &self,
        ranked_lists: &[Vec<(String, Score)>],
    ) -> EngineResult<Vec<ScoredDocument>> {
        let weights = self.resolve_weights(ranked_lists.len());
        let mut id_to_data: std::collections::HashMap<String, (f32, Vec<Score>, Vec<usize>)> =
            std::collections::HashMap::new();

        let normalized_lists: Vec<Vec<(String, Score)>> = if self.config.normalize_before_fusion {
            ranked_lists
                .iter()
                .map(|list| {
                    let scores: Vec<Score> = list.iter().map(|(_, s)| *s).collect();
                    let normalized = self.normalize_scores(&scores);
                    list.iter()
                        .zip(normalized.iter())
                        .map(|((id, _), &norm_score)| (id.clone(), norm_score))
                        .collect()
                })
                .collect()
        } else {
            ranked_lists.to_vec()
        };

        for (list_idx, list) in normalized_lists.iter().enumerate() {
            let w = weights[list_idx];
            for (rank, (id, score)) in list.iter().enumerate() {
                let entry = id_to_data
                    .entry(id.clone())
                    .or_insert((0.0, Vec::new(), Vec::new()));
                entry.0 += w * score;
                entry.1.push(*score);
                entry.2.push(rank + 1);
            }
        }

        let mut results: Vec<ScoredDocument> = id_to_data
            .into_iter()
            .map(|(id, (score, source_scores, source_ranks))| ScoredDocument {
                id,
                score,
                rank: 0,
                source_scores,
                source_ranks,
                metadata: None,
            })
            .collect();

        self.finalize_results(&mut results);
        Ok(results)
    }

    fn score_normalization_fusion(
        &self,
        ranked_lists: &[Vec<(String, Score)>],
    ) -> EngineResult<Vec<ScoredDocument>> {
        let mut id_to_data: std::collections::HashMap<String, (f32, Vec<Score>, Vec<usize>)> =
            std::collections::HashMap::new();

        for list in ranked_lists {
            let scores: Vec<Score> = list.iter().map(|(_, s)| *s).collect();
            let normalized = self.normalize_scores(&scores);
            for (rank, ((id, _original), norm_score)) in
                list.iter().zip(normalized.iter()).enumerate()
            {
                let entry = id_to_data
                    .entry(id.clone())
                    .or_insert((0.0, Vec::new(), Vec::new()));
                entry.0 += norm_score;
                entry.1.push(*norm_score);
                entry.2.push(rank + 1);
            }
        }

        let num_lists = ranked_lists.len() as f32;
        for (_, data) in id_to_data.iter_mut() {
            data.0 /= num_lists;
        }

        let mut results: Vec<ScoredDocument> = id_to_data
            .into_iter()
            .map(|(id, (score, source_scores, source_ranks))| ScoredDocument {
                id,
                score,
                rank: 0,
                source_scores,
                source_ranks,
                metadata: None,
            })
            .collect();

        self.finalize_results(&mut results);
        Ok(results)
    }

    fn borda_fusion(
        &self,
        ranked_lists: &[Vec<(String, Score)>],
    ) -> EngineResult<Vec<ScoredDocument>> {
        let mut id_to_data: std::collections::HashMap<String, (f32, Vec<Score>, Vec<usize>)> =
            std::collections::HashMap::new();

        for list in ranked_lists {
            let n = list.len();
            for (rank, (id, score)) in list.iter().enumerate() {
                let borda_score = (n - rank) as f32;
                let entry = id_to_data
                    .entry(id.clone())
                    .or_insert((0.0, Vec::new(), Vec::new()));
                entry.0 += borda_score;
                entry.1.push(*score);
                entry.2.push(rank + 1);
            }
        }

        let mut results: Vec<ScoredDocument> = id_to_data
            .into_iter()
            .map(|(id, (score, source_scores, source_ranks))| ScoredDocument {
                id,
                score,
                rank: 0,
                source_scores,
                source_ranks,
                metadata: None,
            })
            .collect();

        self.finalize_results(&mut results);
        Ok(results)
    }

    fn linear_combination_fusion(
        &self,
        ranked_lists: &[Vec<(String, Score)>],
    ) -> EngineResult<Vec<ScoredDocument>> {
        self.weighted_fusion(ranked_lists)
    }

    fn softmax_fusion(
        &self,
        ranked_lists: &[Vec<(String, Score)>],
    ) -> EngineResult<Vec<ScoredDocument>> {
        let mut id_to_data: std::collections::HashMap<String, (f32, Vec<Score>, Vec<usize>)> =
            std::collections::HashMap::new();

        for list in ranked_lists {
            let scores: Vec<Score> = list.iter().map(|(_, s)| *s).collect();
            let softmax_scores = softmax(&scores);
            for (rank, ((id, _), sm_score)) in list.iter().zip(softmax_scores.iter()).enumerate() {
                let entry = id_to_data
                    .entry(id.clone())
                    .or_insert((0.0, Vec::new(), Vec::new()));
                entry.0 += sm_score;
                entry.1.push(*sm_score);
                entry.2.push(rank + 1);
            }
        }

        let mut results: Vec<ScoredDocument> = id_to_data
            .into_iter()
            .map(|(id, (score, source_scores, source_ranks))| ScoredDocument {
                id,
                score,
                rank: 0,
                source_scores,
                source_ranks,
                metadata: None,
            })
            .collect();

        self.finalize_results(&mut results);
        Ok(results)
    }

    fn normalize_scores(&self, scores: &[Score]) -> Vec<Score> {
        match &self.config.normalization_method {
            NormalizationMethod::MinMax => min_max_normalize(scores),
            NormalizationMethod::Softmax => softmax(scores),
            NormalizationMethod::Sigmoid => {
                scores.iter().map(|&s| crate::utils::sigmoid(s)).collect()
            }
            NormalizationMethod::ZScore => {
                if scores.is_empty() {
                    return Vec::new();
                }
                let mean = scores.iter().sum::<f32>() / scores.len() as f32;
                let variance = scores.iter().map(|&s| (s - mean).powi(2)).sum::<f32>()
                    / scores.len() as f32;
                let std_dev = variance.sqrt();
                if std_dev < f32::EPSILON {
                    return vec![0.0; scores.len()];
                }
                scores.iter().map(|&s| (s - mean) / std_dev).collect()
            }
            NormalizationMethod::None => scores.to_vec(),
        }
    }

    fn resolve_weights(&self, n: usize) -> Vec<f32> {
        if self.config.weights.len() >= n {
            let w = &self.config.weights[..n];
            let sum: f32 = w.iter().sum();
            if sum > f32::EPSILON {
                return w.iter().map(|&x| x / sum).collect();
            }
        }
        vec![1.0 / n as f32; n]
    }

    fn finalize_results(&self, results: &mut Vec<ScoredDocument>) {
        results.retain(|r| r.score >= self.config.min_score_threshold);

        results.sort_unstable_by(|a, b| {
            b.score
                .partial_cmp(&a.score)
                .unwrap_or(Ordering::Equal)
        });

        results.truncate(self.config.top_n);

        for (rank, result) in results.iter_mut().enumerate() {
            result.rank = rank + 1;
        }
    }
}

pub fn rerank_with_cross_scores(
    query_doc_scores: Vec<(String, Score)>,
    top_n: usize,
    min_threshold: f32,
) -> Vec<RankedResult> {
    let mut indexed: Vec<(usize, &(String, Score))> =
        query_doc_scores.iter().enumerate().collect();

    indexed.sort_unstable_by(|a, b| {
        b.1 .1.partial_cmp(&a.1 .1).unwrap_or(Ordering::Equal)
    });

    indexed
        .into_iter()
        .enumerate()
        .filter(|(_, (_original_rank, (_, score)))| *score >= min_threshold)
        .take(top_n)
        .map(|(new_rank, (original_rank, (id, score)))| RankedResult {
            id: id.clone(),
            rank: new_rank + 1,
            score: *score,
            original_score: None,
            original_rank: Some(original_rank + 1),
        })
        .collect()
}

pub fn compute_mrr(ranked_results: &[RankedResult], relevant_ids: &std::collections::HashSet<String>) -> f32 {
    for result in ranked_results {
        if relevant_ids.contains(&result.id) {
            return 1.0 / result.rank as f32;
        }
    }
    0.0
}

pub fn compute_ndcg(
    ranked_results: &[RankedResult],
    relevant_ids: &std::collections::HashSet<String>,
    k: usize,
) -> f32 {
    let k = k.min(ranked_results.len());
    if k == 0 {
        return 0.0;
    }

    let dcg: f32 = ranked_results[..k]
        .iter()
        .enumerate()
        .map(|(i, r)| {
            let rel = if relevant_ids.contains(&r.id) { 1.0f32 } else { 0.0 };
            rel / (i as f32 + 2.0).log2()
        })
        .sum();

    let ideal_k = k.min(relevant_ids.len());
    let idcg: f32 = (0..ideal_k)
        .map(|i| 1.0f32 / (i as f32 + 2.0).log2())
        .sum();

    if idcg < f32::EPSILON {
        return 0.0;
    }

    (dcg / idcg).clamp(0.0, 1.0)
}

pub fn compute_precision_at_k(
    ranked_results: &[RankedResult],
    relevant_ids: &std::collections::HashSet<String>,
    k: usize,
) -> f32 {
    let k = k.min(ranked_results.len());
    if k == 0 {
        return 0.0;
    }
    let relevant_count = ranked_results[..k]
        .iter()
        .filter(|r| relevant_ids.contains(&r.id))
        .count();
    relevant_count as f32 / k as f32
}

pub fn compute_recall_at_k(
    ranked_results: &[RankedResult],
    relevant_ids: &std::collections::HashSet<String>,
    k: usize,
) -> f32 {
    if relevant_ids.is_empty() {
        return 0.0;
    }
    let k = k.min(ranked_results.len());
    let relevant_count = ranked_results[..k]
        .iter()
        .filter(|r| relevant_ids.contains(&r.id))
        .count();
    relevant_count as f32 / relevant_ids.len() as f32
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_rrf_fusion() -> ScoreFusion {
        ScoreFusion::new(RerankerConfig {
            reranker_type: RerankerType::ReciprocalRankFusion,
            top_n: 10,
            ..Default::default()
        })
    }

    #[test]
    fn test_rrf_fusion_combines_lists() {
        let fusion = make_rrf_fusion();
        let list1 = vec![
            ("doc_a".to_string(), 0.9),
            ("doc_b".to_string(), 0.7),
            ("doc_c".to_string(), 0.5),
        ];
        let list2 = vec![
            ("doc_b".to_string(), 0.95),
            ("doc_a".to_string(), 0.6),
            ("doc_d".to_string(), 0.4),
        ];
        let results = fusion.fuse(&[list1, list2]).unwrap();
        assert!(results.len() <= 4);
        assert!(results[0].score >= results[1].score);
    }

    #[test]
    fn test_rrf_rank_assignment() {
        let fusion = make_rrf_fusion();
        let list = vec![
            ("a".to_string(), 0.9),
            ("b".to_string(), 0.5),
        ];
        let results = fusion.fuse(&[list]).unwrap();
        assert_eq!(results[0].rank, 1);
        assert_eq!(results[1].rank, 2);
    }

    #[test]
    fn test_weighted_fusion_respects_weights() {
        let fusion = ScoreFusion::new(RerankerConfig {
            reranker_type: RerankerType::WeightedFusion,
            weights: vec![0.8, 0.2],
            normalize_before_fusion: false,
            top_n: 10,
            ..Default::default()
        });
        let list1 = vec![("doc_a".to_string(), 1.0f32)];
        let list2 = vec![("doc_b".to_string(), 1.0f32)];
        let results = fusion.fuse(&[list1, list2]).unwrap();
        let score_a = results.iter().find(|r| r.id == "doc_a").map(|r| r.score).unwrap_or(0.0);
        let score_b = results.iter().find(|r| r.id == "doc_b").map(|r| r.score).unwrap_or(0.0);
        assert!(score_a > score_b);
    }

    #[test]
    fn test_empty_input_returns_empty() {
        let fusion = make_rrf_fusion();
        let results = fusion.fuse(&[]).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn test_top_n_limit_respected() {
        let fusion = ScoreFusion::new(RerankerConfig {
            reranker_type: RerankerType::ReciprocalRankFusion,
            top_n: 2,
            ..Default::default()
        });
        let list: Vec<(String, f32)> = (0..10)
            .map(|i| (format!("doc_{}", i), 1.0 - i as f32 * 0.1))
            .collect();
        let results = fusion.fuse(&[list]).unwrap();
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_ndcg_perfect_ranking() {
        let results = vec![
            RankedResult { id: "a".to_string(), rank: 1, score: 1.0, original_score: None, original_rank: None },
            RankedResult { id: "b".to_string(), rank: 2, score: 0.8, original_score: None, original_rank: None },
        ];
        let relevant: std::collections::HashSet<String> =
            vec!["a".to_string(), "b".to_string()].into_iter().collect();
        let ndcg = compute_ndcg(&results, &relevant, 2);
        assert!((ndcg - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_precision_at_k() {
        let results = vec![
            RankedResult { id: "a".to_string(), rank: 1, score: 1.0, original_score: None, original_rank: None },
            RankedResult { id: "b".to_string(), rank: 2, score: 0.8, original_score: None, original_rank: None },
            RankedResult { id: "c".to_string(), rank: 3, score: 0.6, original_score: None, original_rank: None },
        ];
        let relevant: std::collections::HashSet<String> =
            vec!["a".to_string(), "c".to_string()].into_iter().collect();
        let p2 = compute_precision_at_k(&results, &relevant, 2);
        assert!((p2 - 0.5).abs() < 1e-5);
    }

    #[test]
    fn test_mrr_first_relevant() {
        let results = vec![
            RankedResult { id: "a".to_string(), rank: 1, score: 1.0, original_score: None, original_rank: None },
        ];
        let relevant: std::collections::HashSet<String> =
            vec!["a".to_string()].into_iter().collect();
        let mrr = compute_mrr(&results, &relevant);
        assert!((mrr - 1.0).abs() < 1e-5);
    }
}