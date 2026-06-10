// rust_engine/benches/vector_index_bench.rs

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use neuralcore_engine::types::DistanceMetric;
use neuralcore_engine::utils::normalize_vector_new;
use neuralcore_engine::vector_index::{IndexConfig, VectorIndex};

fn make_vector(dim: usize, seed: u64) -> Vec<f32> {
    let mut state = seed ^ 0xdeadbeefcafebabe;
    let v: Vec<f32> = (0..dim)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            ((state as f32) / (u64::MAX as f32)) * 2.0 - 1.0
        })
        .collect();
    normalize_vector_new(&v)
}

fn make_vectors(n: usize, dim: usize) -> Vec<Vec<f32>> {
    (0..n)
        .map(|i| make_vector(dim, i as u64 * 6364136223846793005 + 1442695040888963407))
        .collect()
}

fn build_hnsw_index(n: usize, dim: usize) -> VectorIndex {
    let config = IndexConfig::hnsw(dim, DistanceMetric::Cosine);
    let index = VectorIndex::new(config);
    let vectors = make_vectors(n, dim);
    for (i, v) in vectors.into_iter().enumerate() {
        index.add(format!("doc_{:08}", i), v, None).unwrap();
    }
    index
}

fn build_flat_index(n: usize, dim: usize) -> VectorIndex {
    let config = IndexConfig::flat(dim, DistanceMetric::Cosine);
    let index = VectorIndex::new(config);
    let vectors = make_vectors(n, dim);
    for (i, v) in vectors.into_iter().enumerate() {
        index.add(format!("doc_{:08}", i), v, None).unwrap();
    }
    index
}

fn bench_hnsw_build_by_size(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/build_by_corpus_size");
    group.sample_size(10);

    let dim = 1536;

    for n in [1000, 5000, 10000, 50000, 100000] {
        let vectors = make_vectors(n, dim);
        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| {
                let config = IndexConfig::hnsw(dim, DistanceMetric::Cosine);
                let index = VectorIndex::new(config);
                for (i, v) in vectors.iter().enumerate() {
                    index.add(format!("doc_{}", i), v.clone(), None).unwrap();
                }
                black_box(index.len())
            })
        });
    }
    group.finish();
}

fn bench_hnsw_build_by_dimension(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/build_by_dimension");
    group.sample_size(10);

    let n = 5000;
    for dim in [128, 256, 384, 512, 768, 1024, 1536] {
        let vectors = make_vectors(n, dim);
        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(dim), &dim, |bench, _| {
            bench.iter(|| {
                let config = IndexConfig::hnsw(dim, DistanceMetric::Cosine);
                let index = VectorIndex::new(config);
                for (i, v) in vectors.iter().enumerate() {
                    index.add(format!("doc_{}", i), v.clone(), None).unwrap();
                }
                black_box(index.len())
            })
        });
    }
    group.finish();
}

fn bench_hnsw_search_by_corpus_size(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/search_by_corpus_size");
    group.sample_size(20);

    let dim = 1536;
    let k = 10;
    let query = make_vector(dim, 999_999_999);

    for n in [1000, 5000, 10000, 50000, 100000] {
        let index = build_hnsw_index(n, dim);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| index.search(black_box(&query), black_box(k), None, None))
        });
    }
    group.finish();
}

fn bench_hnsw_search_by_k(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/search_by_k");
    group.sample_size(20);

    let dim = 1536;
    let n = 10000;
    let index = build_hnsw_index(n, dim);
    let query = make_vector(dim, 999_999_999);

    for k in [1, 5, 10, 20, 50, 100] {
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(k), &k, |bench, _| {
            bench.iter(|| index.search(black_box(&query), black_box(k), None, None))
        });
    }
    group.finish();
}

fn bench_hnsw_search_by_ef(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/search_by_ef");
    group.sample_size(20);

    let dim = 768;
    let n = 10000;
    let index = build_hnsw_index(n, dim);
    let query = make_vector(dim, 999_999_999);
    let k = 10;

    for ef in [10, 20, 50, 100, 200, 500] {
        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(ef), &ef, |bench, _| {
            bench.iter(|| index.search(black_box(&query), black_box(k), Some(ef), None))
        });
    }
    group.finish();
}

fn bench_hnsw_search_by_dimension(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/search_by_dimension");
    group.sample_size(20);

    let n = 5000;
    let k = 10;

    for dim in [128, 256, 384, 512, 768, 1024, 1536] {
        let index = build_hnsw_index(n, dim);
        let query = make_vector(dim, 999_999_999);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(dim), &dim, |bench, _| {
            bench.iter(|| index.search(black_box(&query), black_box(k), None, None))
        });
    }
    group.finish();
}

fn bench_flat_search_by_corpus_size(c: &mut Criterion) {
    let mut group = c.benchmark_group("flat/search_by_corpus_size");
    group.sample_size(20);

    let dim = 768;
    let k = 10;
    let query = make_vector(dim, 999_999_999);

    for n in [100, 500, 1000, 5000, 10000] {
        let index = build_flat_index(n, dim);

        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| index.search(black_box(&query), black_box(k), None, None))
        });
    }
    group.finish();
}

fn bench_hnsw_vs_flat(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw_vs_flat/n=5000_dim=768");
    group.sample_size(30);

    let dim = 768;
    let n = 5000;
    let k = 10;
    let query = make_vector(dim, 999_999_999);

    let hnsw = build_hnsw_index(n, dim);
    let flat = build_flat_index(n, dim);

    group.throughput(Throughput::Elements(1));

    group.bench_function("hnsw", |bench| {
        bench.iter(|| hnsw.search(black_box(&query), black_box(k), None, None))
    });

    group.bench_function("flat", |bench| {
        bench.iter(|| flat.search(black_box(&query), black_box(k), None, None))
    });

    group.finish();
}

fn bench_hnsw_add_single(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/add_single");
    group.sample_size(20);

    let dim = 1536;

    for base_size in [0, 1000, 5000, 10000] {
        let config = IndexConfig::hnsw(dim, DistanceMetric::Cosine);
        let index = VectorIndex::new(config);
        for i in 0..base_size {
            let v = make_vector(dim, i as u64);
            index.add(format!("base_{}", i), v, None).unwrap();
        }

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("base_size", base_size),
            &base_size,
            |bench, _| {
                let mut counter = base_size;
                bench.iter(|| {
                    let v = make_vector(dim, counter as u64 + 1_000_000);
                    index.add(format!("new_{}", counter), v, None).unwrap();
                    counter += 1;
                    black_box(counter)
                })
            },
        );
    }
    group.finish();
}

fn bench_hnsw_delete_and_rebuild(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/delete");
    group.sample_size(20);

    let dim = 768;
    let n = 1000;

    group.throughput(Throughput::Elements(1));
    group.bench_function("single_delete", |bench| {
        let index = build_hnsw_index(n, dim);
        let mut counter = 0usize;
        bench.iter(|| {
            let id = format!("doc_{:08}", counter % n);
            black_box(index.delete(&id).unwrap());
            counter += 1;
        });
    });

    group.finish();
}

fn bench_batch_add(c: &mut Criterion) {
    let mut group = c.benchmark_group("hnsw/batch_add");
    group.sample_size(10);

    let dim = 1536;
    for batch_size in [100, 500, 1000, 5000] {
        let vectors = make_vectors(batch_size, dim);
        let ids: Vec<String> = (0..batch_size).map(|i| format!("doc_{}", i)).collect();

        group.throughput(Throughput::Elements(batch_size as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(batch_size),
            &batch_size,
            |bench, _| {
                bench.iter(|| {
                    let config = IndexConfig::hnsw(dim, DistanceMetric::Cosine);
                    let index = VectorIndex::new(config);
                    black_box(index.add_batch(ids.clone(), vectors.clone(), None).unwrap())
                })
            },
        );
    }
    group.finish();
}

fn bench_concurrent_search(c: &mut Criterion) {
    use std::sync::Arc;

    let mut group = c.benchmark_group("hnsw/concurrent_search");
    group.sample_size(10);

    let dim = 768;
    let n = 10000;
    let k = 10;
    let index = Arc::new(build_hnsw_index(n, dim));

    for num_threads in [1, 2, 4, 8] {
        group.throughput(Throughput::Elements(num_threads as u64));
        group.bench_with_input(
            BenchmarkId::new("threads", num_threads),
            &num_threads,
            |bench, &threads| {
                bench.iter(|| {
                    let handles: Vec<_> = (0..threads)
                        .map(|t| {
                            let idx = Arc::clone(&index);
                            let q = make_vector(dim, t as u64 * 1234567);
                            std::thread::spawn(move || {
                                black_box(idx.search(&q, k, None, None).unwrap())
                            })
                        })
                        .collect();
                    for h in handles {
                        h.join().unwrap();
                    }
                })
            },
        );
    }
    group.finish();
}

criterion_group!(
    vector_index_benches,
    bench_hnsw_build_by_size,
    bench_hnsw_build_by_dimension,
    bench_hnsw_search_by_corpus_size,
    bench_hnsw_search_by_k,
    bench_hnsw_search_by_ef,
    bench_hnsw_search_by_dimension,
    bench_flat_search_by_corpus_size,
    bench_hnsw_vs_flat,
    bench_hnsw_add_single,
    bench_hnsw_delete_and_rebuild,
    bench_batch_add,
    bench_concurrent_search,
);
criterion_main!(vector_index_benches);
