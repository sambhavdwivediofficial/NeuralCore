// rust_engine/src/vector_index.rs

use crate::error::{EngineError, EngineResult};
// use crate::similarity::{batch_similarity, top_k_by_similarity};
use crate::similarity::batch_similarity;
use crate::types::{DistanceMetric, IndexStats, SearchResult, Vector};
use crate::utils::{normalize_vector, validate_vector};
use dashmap::DashMap;
use parking_lot::RwLock;
use priority_queue::PriorityQueue;
use ordered_float::OrderedFloat;
// use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use smallvec::SmallVec;
use std::collections::{HashMap, HashSet};
use std::sync::Arc;

const HNSW_DEFAULT_M: usize = 16;
const HNSW_DEFAULT_M_MAX_0: usize = 32;
const HNSW_DEFAULT_EF_CONSTRUCTION: usize = 200;
const HNSW_DEFAULT_EF_SEARCH: usize = 128;
const HNSW_ML_FACTOR: f64 = 1.0 / std::f64::consts::LN_2;
const FLAT_MAX_VECTORS_DEFAULT: usize = 10_000;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum IndexType {
    Flat,
    Hnsw,
    IvfFlat { n_lists: usize },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexConfig {
    pub index_type: IndexType,
    pub dimension: usize,
    pub metric: DistanceMetric,
    pub normalize_on_add: bool,
    pub m: usize,
    pub m_max0: usize,
    pub ef_construction: usize,
    pub ef_search: usize,
    pub flat_threshold: usize,
    pub allow_replace_deleted: bool,
    pub seed: u64,
}

impl IndexConfig {
    pub fn hnsw(dimension: usize, metric: DistanceMetric) -> Self {
        Self {
            index_type: IndexType::Hnsw,
            dimension,
            metric,
            normalize_on_add: matches!(metric, DistanceMetric::Cosine),
            m: HNSW_DEFAULT_M,
            m_max0: HNSW_DEFAULT_M_MAX_0,
            ef_construction: HNSW_DEFAULT_EF_CONSTRUCTION,
            ef_search: HNSW_DEFAULT_EF_SEARCH,
            flat_threshold: FLAT_MAX_VECTORS_DEFAULT,
            allow_replace_deleted: true,
            seed: 42,
        }
    }

    pub fn flat(dimension: usize, metric: DistanceMetric) -> Self {
        Self {
            index_type: IndexType::Flat,
            dimension,
            metric,
            normalize_on_add: matches!(metric, DistanceMetric::Cosine),
            m: HNSW_DEFAULT_M,
            m_max0: HNSW_DEFAULT_M_MAX_0,
            ef_construction: HNSW_DEFAULT_EF_CONSTRUCTION,
            ef_search: HNSW_DEFAULT_EF_SEARCH,
            flat_threshold: usize::MAX,
            allow_replace_deleted: true,
            seed: 42,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct HnswNode {
    id: u64,
    vector: Vector,
    external_id: String,
    level: usize,
    neighbors: Vec<SmallVec<[u64; 32]>>,
    deleted: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FlatEntry {
    id: u64,
    external_id: String,
    vector: Vector,
    deleted: bool,
    metadata: Option<serde_json::Value>,
}

struct HnswGraph {
    nodes: Vec<HnswNode>,
    entry_point: Option<u64>,
    max_level: usize,
    id_to_internal: HashMap<String, u64>,
    next_id: u64,
    config: IndexConfig,
    rng_state: u64,
}

impl HnswGraph {
    fn new(config: IndexConfig) -> Self {
        Self {
            nodes: Vec::new(),
            entry_point: None,
            max_level: 0,
            id_to_internal: HashMap::new(),
            next_id: 0,
            rng_state: config.seed,
            config,
        }
    }

    fn random_level(&mut self) -> usize {
        self.rng_state ^= self.rng_state << 13;
        self.rng_state ^= self.rng_state >> 7;
        self.rng_state ^= self.rng_state << 17;
        let r = (self.rng_state as f64) / (u64::MAX as f64);
        let level = (-r.ln() * HNSW_ML_FACTOR).floor() as usize;
        level
    }

    fn add(&mut self, external_id: String, mut vector: Vector) -> EngineResult<u64> {
        if vector.len() != self.config.dimension {
            return Err(EngineError::DimensionMismatch {
                expected: self.config.dimension,
                actual: vector.len(),
            });
        }
        validate_vector(&vector, "hnsw_add")?;

        if self.config.normalize_on_add {
            normalize_vector(&mut vector);
        }

        if let Some(&existing_id) = self.id_to_internal.get(&external_id) {
            if self.config.allow_replace_deleted {
                self.nodes[existing_id as usize].vector = vector;
                self.nodes[existing_id as usize].deleted = false;
                return Ok(existing_id);
            }
            return Ok(existing_id);
        }

        let internal_id = self.next_id;
        self.next_id += 1;

        let level = self.random_level();
        let m_at_level = |l: usize| if l == 0 { self.config.m_max0 } else { self.config.m };

        let mut neighbors = Vec::with_capacity(level + 1);
        for l in 0..=level {
            neighbors.push(SmallVec::with_capacity(m_at_level(l)));
        }

        let node = HnswNode {
            id: internal_id,
            vector: vector.clone(),
            external_id: external_id.clone(),
            level,
            neighbors,
            deleted: false,
        };

        self.nodes.push(node);
        self.id_to_internal.insert(external_id, internal_id);

        if self.entry_point.is_none() {
            self.entry_point = Some(internal_id);
            self.max_level = level;
            return Ok(internal_id);
        }

        let entry = self.entry_point.unwrap();
        let mut ep = vec![entry];

        for lc in (level + 1..=self.max_level).rev() {
            ep = self.greedy_search_layer(&vector, ep, 1, lc);
        }

        for lc in (0..=level.min(self.max_level)).rev() {
            let candidates = self.search_layer(&vector, ep.clone(), self.config.ef_construction, lc);
            let m = m_at_level(lc);
            let selected = self.select_neighbors(&vector, &candidates, m, lc, true);

            {
                let node = &mut self.nodes[internal_id as usize];
                if lc < node.neighbors.len() {
                    for &neighbor_id in &selected {
                        node.neighbors[lc].push(neighbor_id);
                    }
                }
            }

            for &neighbor_id in &selected {
                if (neighbor_id as usize) < self.nodes.len() {
                    let neighbor_m = m_at_level(lc);
            
                    let neighbor_vec;
                    let neighbor_list;
            
                    {
                        let neighbor = &mut self.nodes[neighbor_id as usize];
            
                        if lc < neighbor.neighbors.len() {
                            if !neighbor.neighbors[lc].contains(&internal_id) {
                                neighbor.neighbors[lc].push(internal_id);
                            }
            
                            if neighbor.neighbors[lc].len() <= neighbor_m {
                                continue;
                            }
            
                            neighbor_vec = neighbor.vector.clone();
                            neighbor_list = neighbor.neighbors[lc].clone();
                        } else {
                            continue;
                        }
                    }
            
                    let to_keep = self.select_neighbors_prune(
                        &neighbor_vec,
                        &neighbor_list,
                        neighbor_m,
                    );
            
                    self.nodes[neighbor_id as usize].neighbors[lc] =
                        to_keep.into_iter().collect();
                }
            }

            ep = selected;
        }

        if level > self.max_level {
            self.max_level = level;
            self.entry_point = Some(internal_id);
        }

        Ok(internal_id)
    }

    fn search(&self, query: &[f32], k: usize, ef: usize) -> EngineResult<Vec<(u64, f32)>> {
        if self.nodes.is_empty() || self.entry_point.is_none() {
            return Ok(Vec::new());
        }

        let mut query_vec = query.to_vec();
        if self.config.normalize_on_add {
            normalize_vector(&mut query_vec);
        }

        let entry = self.entry_point.unwrap();
        let mut ep = vec![entry];

        for lc in (1..=self.max_level).rev() {
            ep = self.greedy_search_layer(&query_vec, ep, 1, lc);
        }

        let candidates = self.search_layer(&query_vec, ep, ef, 0);

        let mut results: Vec<(u64, f32)> = candidates
            .into_iter()
            .filter(|&id| {
                let idx = id as usize;
                idx < self.nodes.len() && !self.nodes[idx].deleted
            })
            .map(|id| {
                let score = self
                    .compute_score(&query_vec, &self.nodes[id as usize].vector)
                    .unwrap_or(0.0);
                (id, score)
            })
            .collect();

        results.sort_unstable_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
        });
        results.truncate(k);

        Ok(results)
    }

    fn greedy_search_layer(
        &self,
        query: &[f32],
        entry_points: Vec<u64>,
        ef: usize,
        level: usize,
    ) -> Vec<u64> {
        self.search_layer(query, entry_points, ef, level)
    }

    fn search_layer(
        &self,
        query: &[f32],
        entry_points: Vec<u64>,
        ef: usize,
        level: usize,
    ) -> Vec<u64> {
        let mut visited: HashSet<u64> = HashSet::new();
        let mut candidates: PriorityQueue<u64, OrderedFloat<f32>> = PriorityQueue::new();
        let mut results: PriorityQueue<u64, OrderedFloat<f32>> = PriorityQueue::new();

        for ep in &entry_points {
            if visited.contains(ep) {
                continue;
            }
            visited.insert(*ep);
            let idx = *ep as usize;
            if idx >= self.nodes.len() {
                continue;
            }
            let score = self
                .compute_score(query, &self.nodes[idx].vector)
                .unwrap_or(0.0);
            candidates.push(*ep, OrderedFloat(score));
            results.push(*ep, OrderedFloat(score));
        }

        while let Some((current, current_score)) = candidates.pop() {
            let worst_result_score = results
                .peek()
                .map(|(_, s)| *s)
                .unwrap_or(OrderedFloat(f32::NEG_INFINITY));

            if results.len() >= ef && current_score < worst_result_score {
                break;
            }

            let current_idx = current as usize;
            if current_idx >= self.nodes.len() {
                continue;
            }

            let neighbors_at_level = if level < self.nodes[current_idx].neighbors.len() {
                self.nodes[current_idx].neighbors[level].clone()
            } else {
                SmallVec::new()
            };

            for neighbor_id in neighbors_at_level {
                if visited.contains(&neighbor_id) {
                    continue;
                }
                visited.insert(neighbor_id);
                let n_idx = neighbor_id as usize;
                if n_idx >= self.nodes.len() || self.nodes[n_idx].deleted {
                    continue;
                }
                let score = self
                    .compute_score(query, &self.nodes[n_idx].vector)
                    .unwrap_or(0.0);

                let worst = results
                    .peek()
                    .map(|(_, s)| *s)
                    .unwrap_or(OrderedFloat(f32::NEG_INFINITY));

                if results.len() < ef || OrderedFloat(score) > worst {
                    candidates.push(neighbor_id, OrderedFloat(score));
                    results.push(neighbor_id, OrderedFloat(score));
                    if results.len() > ef {
                        results.pop();
                    }
                }
            }
        }

        results.into_sorted_vec()
    }

    fn select_neighbors(
        &self,
        query: &[f32],
        candidates: &[u64],
        m: usize,
        _level: usize,
        _extend_candidates: bool,
    ) -> Vec<u64> {
        self.select_neighbors_prune(query, candidates, m)
    }

    fn select_neighbors_prune(&self, query: &[f32], candidates: &[u64], m: usize) -> Vec<u64> {
        let mut scored: Vec<(u64, f32)> = candidates
            .iter()
            .filter_map(|&id| {
                let idx = id as usize;
                if idx < self.nodes.len() && !self.nodes[idx].deleted {
                    let score = self
                        .compute_score(query, &self.nodes[idx].vector)
                        .unwrap_or(0.0);
                    Some((id, score))
                } else {
                    None
                }
            })
            .collect();

        scored.sort_unstable_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
        });
        scored.truncate(m);
        scored.into_iter().map(|(id, _)| id).collect()
    }

    fn compute_score(&self, a: &[f32], b: &[f32]) -> EngineResult<f32> {
        match self.config.metric {
            DistanceMetric::Cosine => crate::similarity::cosine_similarity_prenormalized(a, b),
            DistanceMetric::DotProduct => crate::similarity::dot_product(a, b),
            DistanceMetric::Euclidean => crate::similarity::euclidean_similarity(a, b),
            DistanceMetric::Manhattan => crate::similarity::manhattan_similarity(a, b),
        }
    }

    fn delete(&mut self, external_id: &str) -> bool {
        if let Some(&internal_id) = self.id_to_internal.get(external_id) {
            if (internal_id as usize) < self.nodes.len() {
                self.nodes[internal_id as usize].deleted = true;
                return true;
            }
        }
        false
    }

    fn len(&self) -> usize {
        self.nodes.iter().filter(|n| !n.deleted).count()
    }
}

pub struct VectorIndex {
    config: IndexConfig,
    hnsw: Option<RwLock<HnswGraph>>,
    flat_entries: Option<RwLock<Vec<FlatEntry>>>,
    external_to_metadata: DashMap<String, serde_json::Value>,
    total_adds: Arc<std::sync::atomic::AtomicU64>,
    total_searches: Arc<std::sync::atomic::AtomicU64>,
}

impl VectorIndex {
    pub fn new(config: IndexConfig) -> Self {
        let (hnsw, flat) = match &config.index_type {
            IndexType::Hnsw | IndexType::IvfFlat { .. } => {
                (Some(RwLock::new(HnswGraph::new(config.clone()))), None)
            }
            IndexType::Flat => (
                None,
                Some(RwLock::new(Vec::new())),
            ),
        };

        Self {
            config,
            hnsw,
            flat_entries: flat,
            external_to_metadata: DashMap::new(),
            total_adds: Arc::new(std::sync::atomic::AtomicU64::new(0)),
            total_searches: Arc::new(std::sync::atomic::AtomicU64::new(0)),
        }
    }

    pub fn add(
        &self,
        id: String,
        vector: Vector,
        metadata: Option<serde_json::Value>,
    ) -> EngineResult<()> {
        if vector.len() != self.config.dimension {
            return Err(EngineError::DimensionMismatch {
                expected: self.config.dimension,
                actual: vector.len(),
            });
        }
        validate_vector(&vector, "vector_index_add")?;

        if let Some(meta) = metadata {
            self.external_to_metadata.insert(id.clone(), meta);
        }

        self.total_adds
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

        if let Some(hnsw) = &self.hnsw {
            let mut graph = hnsw.write();
            graph.add(id, vector)?;
            return Ok(());
        }

        if let Some(flat) = &self.flat_entries {
            let mut entries = flat.write();
            if let Some(existing) = entries.iter_mut().find(|e| e.external_id == id) {
                existing.vector = vector;
                existing.deleted = false;
                return Ok(());
            }
            let internal_id = entries.len() as u64;
            entries.push(FlatEntry {
                id: internal_id,
                external_id: id,
                vector,
                deleted: false,
                metadata: None,
            });
            return Ok(());
        }

        Err(EngineError::IndexError("No index backend initialized".to_string()))
    }

    pub fn add_batch(
        &self,
        ids: Vec<String>,
        vectors: Vec<Vector>,
        metadata: Option<Vec<Option<serde_json::Value>>>,
    ) -> EngineResult<usize> {
        if ids.len() != vectors.len() {
            return Err(EngineError::InvalidParameter {
                name: "ids",
                value: format!("len={}", ids.len()),
                reason: "ids and vectors must have equal length",
            });
        }

        let count = ids.len();
        let metadata_list: Vec<Option<serde_json::Value>> =
            metadata.unwrap_or_else(|| vec![None; count]);

        for ((id, vector), meta) in ids.into_iter().zip(vectors.into_iter()).zip(metadata_list) {
            self.add(id, vector, meta)?;
        }

        Ok(count)
    }

    pub fn search(
        &self,
        query: &[f32],
        k: usize,
        ef: Option<usize>,
        filter: Option<&dyn Fn(&str, Option<&serde_json::Value>) -> bool>,
    ) -> EngineResult<Vec<SearchResult>> {
        if query.len() != self.config.dimension {
            return Err(EngineError::DimensionMismatch {
                expected: self.config.dimension,
                actual: query.len(),
            });
        }
        validate_vector(query, "vector_index_search")?;

        self.total_searches
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

        let effective_ef = ef.unwrap_or(self.config.ef_search).max(k);

        if let Some(hnsw) = &self.hnsw {
            let graph = hnsw.read();
            let raw_results = graph.search(query, effective_ef, effective_ef)?;

            let mut results: Vec<SearchResult> = raw_results
                .into_iter()
                .filter_map(|(internal_id, score)| {
                    let idx = internal_id as usize;
                    if idx >= graph.nodes.len() {
                        return None;
                    }
                    let node = &graph.nodes[idx];
                    if node.deleted {
                        return None;
                    }
                    let meta = self.external_to_metadata.get(&node.external_id).map(|r| r.clone());
                    if let Some(ref f) = filter {
                        if !f(&node.external_id, meta.as_ref()) {
                            return None;
                        }
                    }
                    Some(
                        SearchResult::new(node.external_id.clone(), score)
                            .with_metadata(meta.unwrap_or(serde_json::Value::Null)),
                    )
                })
                .take(k)
                .collect();

            results.sort_unstable_by(|a, b| {
                b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal)
            });
            return Ok(results);
        }

        if let Some(flat) = &self.flat_entries {
            let entries = flat.read();
            let active: Vec<&FlatEntry> = entries.iter().filter(|e| !e.deleted).collect();

            if active.is_empty() {
                return Ok(Vec::new());
            }

            let vectors: Vec<&Vec<f32>> = active.iter().map(|e| &e.vector).collect();
            let ids: Vec<String> = active.iter().map(|e| e.external_id.clone()).collect();

            let scores = batch_similarity(
                query,
                &vectors.iter().map(|v| v.to_vec()).collect::<Vec<_>>(),
                self.config.metric,
                self.config.normalize_on_add,
            )?;

            let mut indexed: Vec<(usize, f32)> = scores.into_iter().enumerate().collect();
            indexed.sort_unstable_by(|a, b| {
                b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
            });

            let results: Vec<SearchResult> = indexed
                .into_iter()
                .filter_map(|(idx, score)| {
                    let id = &ids[idx];
                    let meta = self.external_to_metadata.get(id).map(|r| r.clone());
                    if let Some(ref f) = filter {
                        if !f(id, meta.as_ref()) {
                            return None;
                        }
                    }
                    Some(
                        SearchResult::new(id.clone(), score)
                            .with_metadata(meta.unwrap_or(serde_json::Value::Null)),
                    )
                })
                .take(k)
                .collect();

            return Ok(results);
        }

        Err(EngineError::IndexError("No index backend initialized".to_string()))
    }

    pub fn delete(&self, id: &str) -> EngineResult<bool> {
        self.external_to_metadata.remove(id);

        if let Some(hnsw) = &self.hnsw {
            let mut graph = hnsw.write();
            return Ok(graph.delete(id));
        }

        if let Some(flat) = &self.flat_entries {
            let mut entries = flat.write();
            if let Some(entry) = entries.iter_mut().find(|e| e.external_id == id) {
                entry.deleted = true;
                return Ok(true);
            }
            return Ok(false);
        }

        Ok(false)
    }

    pub fn delete_batch(&self, ids: &[String]) -> EngineResult<usize> {
        let mut count = 0;
        for id in ids {
            if self.delete(id)? {
                count += 1;
            }
        }
        Ok(count)
    }

    pub fn contains(&self, id: &str) -> bool {
        if let Some(hnsw) = &self.hnsw {
            let graph = hnsw.read();
            return graph.id_to_internal.contains_key(id)
                && !graph.nodes[*graph.id_to_internal.get(id).unwrap() as usize].deleted;
        }
        if let Some(flat) = &self.flat_entries {
            let entries = flat.read();
            return entries
                .iter()
                .any(|e| e.external_id == id && !e.deleted);
        }
        false
    }

    pub fn len(&self) -> usize {
        if let Some(hnsw) = &self.hnsw {
            return hnsw.read().len();
        }
        if let Some(flat) = &self.flat_entries {
            return flat.read().iter().filter(|e| !e.deleted).count();
        }
        0
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    pub fn dimension(&self) -> usize {
        self.config.dimension
    }

    pub fn metric(&self) -> DistanceMetric {
        self.config.metric
    }

    pub fn stats(&self) -> IndexStats {
        let num_vectors = self.len();

        let (num_levels, m) = if let Some(hnsw) = &self.hnsw {
            let graph = hnsw.read();
            (Some(graph.max_level), Some(graph.config.m))
        } else {
            (None, None)
        };

        let memory_bytes = num_vectors * self.config.dimension * std::mem::size_of::<f32>()
            + num_vectors * 64;

        IndexStats {
            num_vectors,
            dimension: self.config.dimension,
            metric: self.config.metric,
            index_type: format!("{:?}", self.config.index_type),
            memory_bytes,
            num_levels,
            ef_construction: Some(self.config.ef_construction),
            m,
        }
    }

    pub fn rebuild(&self) -> EngineResult<()> {
        if let Some(hnsw) = &self.hnsw {
            let mut graph = hnsw.write();
            let live_entries: Vec<(String, Vector)> = graph
                .nodes
                .iter()
                .filter(|n| !n.deleted)
                .map(|n| (n.external_id.clone(), n.vector.clone()))
                .collect();

            *graph = HnswGraph::new(self.config.clone());

            for (id, vector) in live_entries {
                graph.add(id, vector)?;
            }
        }
        Ok(())
    }

    pub fn total_adds(&self) -> u64 {
        self.total_adds.load(std::sync::atomic::Ordering::Relaxed)
    }

    pub fn total_searches(&self) -> u64 {
        self.total_searches.load(std::sync::atomic::Ordering::Relaxed)
    }
}

unsafe impl Send for VectorIndex {}
unsafe impl Sync for VectorIndex {}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    fn make_index(dim: usize) -> VectorIndex {
        VectorIndex::new(IndexConfig::hnsw(dim, DistanceMetric::Cosine))
    }

    fn make_flat_index(dim: usize) -> VectorIndex {
        VectorIndex::new(IndexConfig::flat(dim, DistanceMetric::Cosine))
    }

    #[test]
    fn test_flat_add_and_search() {
        let index = make_flat_index(3);
        index.add("a".to_string(), vec![1.0, 0.0, 0.0], None).unwrap();
        index.add("b".to_string(), vec![0.0, 1.0, 0.0], None).unwrap();
        index.add("c".to_string(), vec![0.0, 0.0, 1.0], None).unwrap();

        let results = index.search(&[1.0, 0.0, 0.0], 1, None, None).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].id, "a");
        assert_relative_eq!(results[0].score, 1.0, epsilon = 1e-5);
    }

    #[test]
    fn test_flat_delete() {
        let index = make_flat_index(3);
        index.add("a".to_string(), vec![1.0, 0.0, 0.0], None).unwrap();
        index.add("b".to_string(), vec![1.0, 0.0, 0.0], None).unwrap();
        assert!(index.delete("a").unwrap());
        assert!(!index.contains("a"));
        assert!(index.contains("b"));
        assert_eq!(index.len(), 1);
    }

    #[test]
    fn test_dimension_mismatch_on_add() {
        let index = make_flat_index(3);
        let result = index.add("x".to_string(), vec![1.0, 0.0], None);
        assert!(result.is_err());
    }

    #[test]
    fn test_dimension_mismatch_on_search() {
        let index = make_flat_index(3);
        index.add("a".to_string(), vec![1.0, 0.0, 0.0], None).unwrap();
        let result = index.search(&[1.0, 0.0], 1, None, None);
        assert!(result.is_err());
    }

    #[test]
    fn test_empty_index_search_returns_empty() {
        let index = make_flat_index(3);
        let results = index.search(&[1.0, 0.0, 0.0], 5, None, None).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn test_batch_add() {
        let index = make_flat_index(2);
        let ids = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        let vectors = vec![
            vec![1.0f32, 0.0],
            vec![0.0f32, 1.0],
            vec![0.707f32, 0.707],
        ];
        let count = index.add_batch(ids, vectors, None).unwrap();
        assert_eq!(count, 3);
        assert_eq!(index.len(), 3);
    }

    #[test]
    fn test_hnsw_add_and_search() {
        let index = make_index(3);
        for i in 0..100 {
            let v = vec![i as f32, (i * 2) as f32, (i * 3) as f32];
            index.add(format!("id_{}", i), v, None).unwrap();
        }
        let query = vec![50.0f32, 100.0, 150.0];
        let results = index.search(&query, 5, None, None).unwrap();
        assert!(!results.is_empty());
        assert!(results.len() <= 5);
    }

    #[test]
    fn test_stats_accuracy() {
        let index = make_flat_index(4);
        index.add("a".to_string(), vec![1.0, 0.0, 0.0, 0.0], None).unwrap();
        index.add("b".to_string(), vec![0.0, 1.0, 0.0, 0.0], None).unwrap();
        let stats = index.stats();
        assert_eq!(stats.num_vectors, 2);
        assert_eq!(stats.dimension, 4);
    }
}