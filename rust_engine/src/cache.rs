// rust_engine/src/cache.rs

// use crate::error::{EngineError, EngineResult};
use crate::types::CacheStats;
use dashmap::DashMap;
use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::hash::Hash;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EvictionPolicy {
    Lru,
    Lfu,
    Ttl,
    ArcLru,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheConfig {
    pub capacity: usize,
    pub eviction_policy: EvictionPolicy,
    pub default_ttl: Option<Duration>,
    pub max_value_size_bytes: Option<usize>,
    pub track_frequency: bool,
    pub enable_statistics: bool,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            capacity: 10_000,
            eviction_policy: EvictionPolicy::Lru,
            default_ttl: None,
            max_value_size_bytes: None,
            track_frequency: false,
            enable_statistics: true,
        }
    }
}

#[derive(Debug, Clone)]
struct CacheEntry<V> {
    value: V,
    inserted_at: Instant,
    last_accessed: Instant,
    ttl: Option<Duration>,
    access_count: u64,
    size_bytes: usize,
}

impl<V> CacheEntry<V> {
    fn new(value: V, ttl: Option<Duration>, size_bytes: usize) -> Self {
        let now = Instant::now();
        Self {
            value,
            inserted_at: now,
            last_accessed: now,
            ttl,
            access_count: 1,
            size_bytes,
        }
    }

    fn is_expired(&self) -> bool {
        if let Some(ttl) = self.ttl {
            self.inserted_at.elapsed() > ttl
        } else {
            false
        }
    }

    fn touch(&mut self) {
        self.last_accessed = Instant::now();
        self.access_count += 1;
    }
}

pub struct LruCache<K, V>
where
    K: Clone + Eq + Hash + Send + Sync + 'static,
    V: Clone + Send + Sync + 'static,
{
    entries: DashMap<K, CacheEntry<V>>,
    order: RwLock<VecDeque<K>>,
    capacity: usize,
    default_ttl: Option<Duration>,
    hits: AtomicU64,
    misses: AtomicU64,
    evictions: AtomicU64,
    current_size_bytes: AtomicUsize,
}

impl<K, V> LruCache<K, V>
where
    K: Clone + Eq + Hash + Send + Sync + 'static,
    V: Clone + Send + Sync + 'static,
{
    pub fn new(capacity: usize, default_ttl: Option<Duration>) -> Self {
        Self {
            entries: DashMap::with_capacity(capacity),
            order: RwLock::new(VecDeque::with_capacity(capacity)),
            capacity,
            default_ttl,
            hits: AtomicU64::new(0),
            misses: AtomicU64::new(0),
            evictions: AtomicU64::new(0),
            current_size_bytes: AtomicUsize::new(0),
        }
    }

    pub fn get(&self, key: &K) -> Option<V> {
        if let Some(mut entry) = self.entries.get_mut(key) {
            if entry.is_expired() {
                drop(entry);
                self.remove_entry(key);
                self.misses.fetch_add(1, Ordering::Relaxed);
                return None;
            }
            entry.touch();
            let value = entry.value.clone();
            drop(entry);

            let mut order = self.order.write();
            order.retain(|k| k != key);
            order.push_back(key.clone());

            self.hits.fetch_add(1, Ordering::Relaxed);
            Some(value)
        } else {
            self.misses.fetch_add(1, Ordering::Relaxed);
            None
        }
    }

    pub fn insert(&self, key: K, value: V, ttl: Option<Duration>, size_bytes: usize) {
        let effective_ttl = ttl.or(self.default_ttl);
        let entry = CacheEntry::new(value, effective_ttl, size_bytes);

        if let Some(old_entry) = self.entries.insert(key.clone(), entry) {
            self.current_size_bytes
                .fetch_sub(old_entry.size_bytes, Ordering::Relaxed);
            let mut order = self.order.write();
            order.retain(|k| k != &key);
        }

        self.current_size_bytes
            .fetch_add(size_bytes, Ordering::Relaxed);

        {
            let mut order = self.order.write();
            order.push_back(key);
        }

        while self.entries.len() > self.capacity {
            self.evict_lru();
        }
    }

    pub fn remove(&self, key: &K) -> Option<V> {
        self.remove_entry(key)
    }

    pub fn contains(&self, key: &K) -> bool {
        if let Some(entry) = self.entries.get(key) {
            if entry.is_expired() {
                return false;
            }
            return true;
        }
        false
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn clear(&self) {
        self.entries.clear();
        let mut order = self.order.write();
        order.clear();
        self.current_size_bytes.store(0, Ordering::Relaxed);
    }

    pub fn evict_expired(&self) -> usize {
        let expired_keys: Vec<K> = self
            .entries
            .iter()
            .filter(|e| e.is_expired())
            .map(|e| e.key().clone())
            .collect();

        let count = expired_keys.len();
        for key in &expired_keys {
            self.remove_entry(key);
        }
        count
    }

    pub fn stats(&self) -> CacheStats {
        let hits = self.hits.load(Ordering::Relaxed);
        let misses = self.misses.load(Ordering::Relaxed);
        let total = hits + misses;
        let hit_rate = if total > 0 {
            hits as f64 / total as f64
        } else {
            0.0
        };
        CacheStats {
            hits,
            misses,
            evictions: self.evictions.load(Ordering::Relaxed),
            current_size: self.entries.len(),
            capacity: self.capacity,
            hit_rate,
            memory_bytes: self.current_size_bytes.load(Ordering::Relaxed),
        }
    }

    fn evict_lru(&self) {
        let key_to_evict = {
            let mut order = self.order.write();
            order.pop_front()
        };
        if let Some(key) = key_to_evict {
            self.remove_entry(&key);
            self.evictions.fetch_add(1, Ordering::Relaxed);
        }
    }

    fn remove_entry(&self, key: &K) -> Option<V> {
        if let Some((_, entry)) = self.entries.remove(key) {
            self.current_size_bytes
                .fetch_sub(entry.size_bytes, Ordering::Relaxed);
            let mut order = self.order.write();
            order.retain(|k| k != key);
            Some(entry.value)
        } else {
            None
        }
    }
}

pub struct LfuCache<K, V>
where
    K: Clone + Eq + Hash + Send + Sync + 'static,
    V: Clone + Send + Sync + 'static,
{
    entries: DashMap<K, CacheEntry<V>>,
    capacity: usize,
    default_ttl: Option<Duration>,
    hits: AtomicU64,
    misses: AtomicU64,
    evictions: AtomicU64,
    current_size_bytes: AtomicUsize,
}

impl<K, V> LfuCache<K, V>
where
    K: Clone + Eq + Hash + Send + Sync + 'static,
    V: Clone + Send + Sync + 'static,
{
    pub fn new(capacity: usize, default_ttl: Option<Duration>) -> Self {
        Self {
            entries: DashMap::with_capacity(capacity),
            capacity,
            default_ttl,
            hits: AtomicU64::new(0),
            misses: AtomicU64::new(0),
            evictions: AtomicU64::new(0),
            current_size_bytes: AtomicUsize::new(0),
        }
    }

    pub fn get(&self, key: &K) -> Option<V> {
        if let Some(mut entry) = self.entries.get_mut(key) {
            if entry.is_expired() {
                drop(entry);
                self.entries.remove(key);
                self.misses.fetch_add(1, Ordering::Relaxed);
                return None;
            }
            entry.touch();
            let value = entry.value.clone();
            self.hits.fetch_add(1, Ordering::Relaxed);
            Some(value)
        } else {
            self.misses.fetch_add(1, Ordering::Relaxed);
            None
        }
    }

    pub fn insert(&self, key: K, value: V, ttl: Option<Duration>, size_bytes: usize) {
        let effective_ttl = ttl.or(self.default_ttl);

        if let Some(old) = self
            .entries
            .insert(key, CacheEntry::new(value, effective_ttl, size_bytes))
        {
            self.current_size_bytes
                .fetch_sub(old.size_bytes, Ordering::Relaxed);
        }
        self.current_size_bytes
            .fetch_add(size_bytes, Ordering::Relaxed);

        while self.entries.len() > self.capacity {
            self.evict_lfu();
        }
    }

    pub fn remove(&self, key: &K) -> Option<V> {
        self.entries.remove(key).map(|(_, e)| {
            self.current_size_bytes
                .fetch_sub(e.size_bytes, Ordering::Relaxed);
            e.value
        })
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    pub fn clear(&self) {
        self.entries.clear();
        self.current_size_bytes.store(0, Ordering::Relaxed);
    }

    pub fn stats(&self) -> CacheStats {
        let hits = self.hits.load(Ordering::Relaxed);
        let misses = self.misses.load(Ordering::Relaxed);
        let total = hits + misses;
        CacheStats {
            hits,
            misses,
            evictions: self.evictions.load(Ordering::Relaxed),
            current_size: self.entries.len(),
            capacity: self.capacity,
            hit_rate: if total > 0 {
                hits as f64 / total as f64
            } else {
                0.0
            },
            memory_bytes: self.current_size_bytes.load(Ordering::Relaxed),
        }
    }

    fn evict_lfu(&self) {
        let min_key = self
            .entries
            .iter()
            .min_by_key(|e| e.access_count)
            .map(|e| e.key().clone());

        if let Some(key) = min_key {
            if let Some((_, entry)) = self.entries.remove(&key) {
                self.current_size_bytes
                    .fetch_sub(entry.size_bytes, Ordering::Relaxed);
                self.evictions.fetch_add(1, Ordering::Relaxed);
            }
        }
    }
}

pub struct EmbeddingCache {
    inner: Arc<LruCache<String, Vec<f32>>>,
}

impl EmbeddingCache {
    pub fn new(capacity: usize, ttl_seconds: u64) -> Self {
        let ttl = if ttl_seconds > 0 {
            Some(Duration::from_secs(ttl_seconds))
        } else {
            None
        };
        Self {
            inner: Arc::new(LruCache::new(capacity, ttl)),
        }
    }

    pub fn get(&self, text: &str, model: &str) -> Option<Vec<f32>> {
        let key = Self::make_key(text, model);
        self.inner.get(&key)
    }

    pub fn insert(&self, text: &str, model: &str, embedding: Vec<f32>) {
        let key = Self::make_key(text, model);
        let size = embedding.len() * std::mem::size_of::<f32>() + key.len();
        self.inner.insert(key, embedding, None, size);
    }

    pub fn contains(&self, text: &str, model: &str) -> bool {
        let key = Self::make_key(text, model);
        self.inner.contains(&key)
    }

    pub fn invalidate(&self, text: &str, model: &str) {
        let key = Self::make_key(text, model);
        self.inner.remove(&key);
    }

    pub fn clear(&self) {
        self.inner.clear();
    }

    pub fn stats(&self) -> CacheStats {
        self.inner.stats()
    }

    pub fn evict_expired(&self) -> usize {
        self.inner.evict_expired()
    }

    pub fn len(&self) -> usize {
        self.inner.len()
    }

    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    fn make_key(text: &str, model: &str) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        text.hash(&mut hasher);
        model.hash(&mut hasher);
        format!("{}:{:016x}", model, hasher.finish())
    }
}

pub struct SimilarityCache {
    inner: Arc<LruCache<(String, String), f32>>,
}

impl SimilarityCache {
    pub fn new(capacity: usize, ttl_seconds: u64) -> Self {
        let ttl = if ttl_seconds > 0 {
            Some(Duration::from_secs(ttl_seconds))
        } else {
            None
        };
        Self {
            inner: Arc::new(LruCache::new(capacity, ttl)),
        }
    }

    pub fn get(&self, id_a: &str, id_b: &str) -> Option<f32> {
        let key = Self::normalize_key(id_a, id_b);
        self.inner.get(&key)
    }

    pub fn insert(&self, id_a: &str, id_b: &str, score: f32) {
        let key = Self::normalize_key(id_a, id_b);
        let size = key.0.len() + key.1.len() + std::mem::size_of::<f32>();
        self.inner.insert(key, score, None, size);
    }

    pub fn stats(&self) -> CacheStats {
        self.inner.stats()
    }

    fn normalize_key(a: &str, b: &str) -> (String, String) {
        if a <= b {
            (a.to_string(), b.to_string())
        } else {
            (b.to_string(), a.to_string())
        }
    }
}

pub struct QueryResultCache {
    inner: Arc<LruCache<String, Vec<crate::types::SearchResult>>>,
}

impl QueryResultCache {
    pub fn new(capacity: usize, ttl_seconds: u64) -> Self {
        let ttl = if ttl_seconds > 0 {
            Some(Duration::from_secs(ttl_seconds))
        } else {
            None
        };
        Self {
            inner: Arc::new(LruCache::new(capacity, ttl)),
        }
    }

    pub fn get(
        &self,
        query: &str,
        kb_id: &str,
        top_k: usize,
    ) -> Option<Vec<crate::types::SearchResult>> {
        let key = format!("{}:{}:{}", kb_id, top_k, Self::hash_query(query));
        self.inner.get(&key)
    }

    pub fn insert(
        &self,
        query: &str,
        kb_id: &str,
        top_k: usize,
        results: Vec<crate::types::SearchResult>,
    ) {
        let key = format!("{}:{}:{}", kb_id, top_k, Self::hash_query(query));
        let size = results.len() * 128 + key.len();
        self.inner.insert(key, results, None, size);
    }

    pub fn invalidate_kb(&self, kb_id: &str) {
        let keys_to_remove: Vec<String> = self
            .inner
            .entries
            .iter()
            .filter(|e| e.key().starts_with(kb_id))
            .map(|e| e.key().clone())
            .collect();
        for key in keys_to_remove {
            self.inner.remove(&key);
        }
    }

    pub fn stats(&self) -> CacheStats {
        self.inner.stats()
    }

    pub fn evict_expired(&self) -> usize {
        self.inner.evict_expired()
    }

    fn hash_query(query: &str) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        query.hash(&mut hasher);
        format!("{:016x}", hasher.finish())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lru_insert_and_get() {
        let cache: LruCache<String, i32> = LruCache::new(10, None);
        cache.insert("key1".to_string(), 42, None, 8);
        assert_eq!(cache.get(&"key1".to_string()), Some(42));
    }

    #[test]
    fn test_lru_eviction_on_capacity() {
        let cache: LruCache<String, i32> = LruCache::new(3, None);
        cache.insert("a".to_string(), 1, None, 4);
        cache.insert("b".to_string(), 2, None, 4);
        cache.insert("c".to_string(), 3, None, 4);
        cache.get(&"a".to_string());
        cache.insert("d".to_string(), 4, None, 4);
        assert_eq!(cache.len(), 3);
    }

    #[test]
    fn test_lru_ttl_expiry() {
        let cache: LruCache<String, i32> = LruCache::new(10, Some(Duration::from_millis(1)));
        cache.insert("key".to_string(), 99, None, 4);
        std::thread::sleep(Duration::from_millis(5));
        assert_eq!(cache.get(&"key".to_string()), None);
    }

    #[test]
    fn test_lru_remove() {
        let cache: LruCache<String, i32> = LruCache::new(10, None);
        cache.insert("k".to_string(), 1, None, 4);
        assert!(cache.remove(&"k".to_string()).is_some());
        assert_eq!(cache.get(&"k".to_string()), None);
    }

    #[test]
    fn test_lru_stats_hit_rate() {
        let cache: LruCache<String, i32> = LruCache::new(10, None);
        cache.insert("x".to_string(), 5, None, 4);
        cache.get(&"x".to_string());
        cache.get(&"missing".to_string());
        let stats = cache.stats();
        assert_eq!(stats.hits, 1);
        assert_eq!(stats.misses, 1);
        assert!((stats.hit_rate - 0.5).abs() < 1e-6);
    }

    #[test]
    fn test_embedding_cache_key_consistency() {
        let cache = EmbeddingCache::new(100, 3600);
        let embedding = vec![0.1f32, 0.2, 0.3];
        cache.insert("hello world", "text-embedding-3-small", embedding.clone());
        let result = cache.get("hello world", "text-embedding-3-small");
        assert_eq!(result, Some(embedding));
        assert_eq!(cache.get("hello world", "different-model"), None);
    }

    #[test]
    fn test_similarity_cache_symmetric() {
        let cache = SimilarityCache::new(100, 3600);
        cache.insert("doc_a", "doc_b", 0.85);
        assert_eq!(cache.get("doc_a", "doc_b"), Some(0.85));
        assert_eq!(cache.get("doc_b", "doc_a"), Some(0.85));
    }

    #[test]
    fn test_lfu_evicts_least_frequent() {
        let cache: LfuCache<String, i32> = LfuCache::new(2, None);
        cache.insert("a".to_string(), 1, None, 4);
        cache.insert("b".to_string(), 2, None, 4);
        cache.get(&"b".to_string());
        cache.get(&"b".to_string());
        cache.insert("c".to_string(), 3, None, 4);
        assert_eq!(cache.len(), 2);
        assert!(cache.get(&"b".to_string()).is_some());
    }

    #[test]
    fn test_clear_resets_cache() {
        let cache: LruCache<String, i32> = LruCache::new(10, None);
        cache.insert("a".to_string(), 1, None, 4);
        cache.insert("b".to_string(), 2, None, 4);
        cache.clear();
        assert!(cache.is_empty());
        assert_eq!(cache.stats().current_size, 0);
    }
}
