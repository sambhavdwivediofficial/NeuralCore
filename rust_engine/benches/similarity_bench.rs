// rust_engine/benches/similarity_bench.rs

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use neuralcore_engine::similarity::{
    batch_cosine_similarity, batch_dot_product, batch_euclidean_similarity, cosine_similarity,
    cosine_similarity_prenormalized, dot_product, euclidean_distance, euclidean_similarity,
    manhattan_distance, pairwise_similarity_matrix, top_k_by_similarity,
};
use neuralcore_engine::types::DistanceMetric;
use neuralcore_engine::utils::normalize_vector_new;

fn make_random_vector(dim: usize, seed: u64) -> Vec<f32> {
    let mut state = seed;
    (0..dim)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            ((state as f32) / (u64::MAX as f32)) * 2.0 - 1.0
        })
        .collect()
}

fn make_random_vectors(n: usize, dim: usize, seed_offset: u64) -> Vec<Vec<f32>> {
    (0..n)
        .map(|i| make_random_vector(dim, seed_offset + i as u64 * 6364136223846793005))
        .collect()
}

fn make_normalized_vector(dim: usize, seed: u64) -> Vec<f32> {
    normalize_vector_new(&make_random_vector(dim, seed))
}

fn make_normalized_vectors(n: usize, dim: usize, seed_offset: u64) -> Vec<Vec<f32>> {
    make_random_vectors(n, dim, seed_offset)
        .into_iter()
        .map(|v| normalize_vector_new(&v))
        .collect()
}

fn bench_cosine_similarity_by_dimension(c: &mut Criterion) {
    let mut group = c.benchmark_group("cosine_similarity/by_dimension");

    for dim in [128, 256, 384, 512, 768, 1024, 1536, 3072] {
        let a = make_random_vector(dim, 42);
        let b = make_random_vector(dim, 99);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(dim), &dim, |bench, _| {
            bench.iter(|| cosine_similarity(black_box(&a), black_box(&b)))
        });
    }
    group.finish();
}

fn bench_cosine_similarity_prenormalized_by_dimension(c: &mut Criterion) {
    let mut group = c.benchmark_group("cosine_similarity_prenormalized/by_dimension");

    for dim in [128, 256, 384, 512, 768, 1024, 1536, 3072] {
        let a = make_normalized_vector(dim, 42);
        let b = make_normalized_vector(dim, 99);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(dim), &dim, |bench, _| {
            bench.iter(|| cosine_similarity_prenormalized(black_box(&a), black_box(&b)))
        });
    }
    group.finish();
}

fn bench_dot_product_by_dimension(c: &mut Criterion) {
    let mut group = c.benchmark_group("dot_product/by_dimension");

    for dim in [128, 384, 768, 1536, 3072] {
        let a = make_random_vector(dim, 42);
        let b = make_random_vector(dim, 99);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(dim), &dim, |bench, _| {
            bench.iter(|| dot_product(black_box(&a), black_box(&b)))
        });
    }
    group.finish();
}

fn bench_euclidean_distance_by_dimension(c: &mut Criterion) {
    let mut group = c.benchmark_group("euclidean_distance/by_dimension");

    for dim in [128, 384, 768, 1536] {
        let a = make_random_vector(dim, 42);
        let b = make_random_vector(dim, 99);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(BenchmarkId::from_parameter(dim), &dim, |bench, _| {
            bench.iter(|| euclidean_distance(black_box(&a), black_box(&b)))
        });
    }
    group.finish();
}

fn bench_batch_cosine_by_corpus_size(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_cosine_similarity/by_corpus_size");
    group.sample_size(20);

    let dim = 1536;
    let query = make_normalized_vector(dim, 1);

    for n in [100, 500, 1000, 5000, 10000, 50000] {
        let corpus = make_normalized_vectors(n, dim, 100);

        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| {
                batch_cosine_similarity(black_box(&query), black_box(&corpus), black_box(true))
            })
        });
    }
    group.finish();
}

fn bench_batch_cosine_by_dimension(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_cosine_similarity/by_dimension");
    group.sample_size(20);

    let n = 1000;
    for dim in [128, 384, 768, 1536, 3072] {
        let query = make_normalized_vector(dim, 1);
        let corpus = make_normalized_vectors(n, dim, 100);

        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(dim), &dim, |bench, _| {
            bench.iter(|| {
                batch_cosine_similarity(black_box(&query), black_box(&corpus), black_box(true))
            })
        });
    }
    group.finish();
}

fn bench_batch_dot_product_by_corpus_size(c: &mut Criterion) {
    let mut group = c.benchmark_group("batch_dot_product/by_corpus_size");
    group.sample_size(20);

    let dim = 1536;
    let query = make_random_vector(dim, 1);

    for n in [100, 1000, 10000, 50000] {
        let corpus = make_random_vectors(n, dim, 100);

        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| batch_dot_product(black_box(&query), black_box(&corpus)))
        });
    }
    group.finish();
}

fn bench_top_k_similarity(c: &mut Criterion) {
    let mut group = c.benchmark_group("top_k_similarity");
    group.sample_size(20);

    let dim = 1536;
    let query = make_normalized_vector(dim, 1);

    let sizes = [
        (1000, 10),
        (5000, 10),
        (10000, 10),
        (10000, 50),
        (10000, 100),
    ];
    for (n, k) in sizes {
        let corpus = make_normalized_vectors(n, dim, 100);
        let ids: Vec<String> = (0..n).map(|i| format!("doc_{}", i)).collect();

        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(
            BenchmarkId::new(format!("n={}", n), format!("k={}", k)),
            &(n, k),
            |bench, _| {
                bench.iter(|| {
                    top_k_by_similarity(
                        black_box(&query),
                        black_box(&corpus),
                        black_box(&ids),
                        black_box(k),
                        black_box(DistanceMetric::Cosine),
                        black_box(true),
                    )
                })
            },
        );
    }
    group.finish();
}

fn bench_pairwise_similarity_matrix(c: &mut Criterion) {
    let mut group = c.benchmark_group("pairwise_similarity_matrix");
    group.sample_size(10);

    for n in [50, 100, 200, 500] {
        let dim = 768;
        let va = make_normalized_vectors(n, dim, 1);
        let vb = make_normalized_vectors(n, dim, 2);

        group.throughput(Throughput::Elements((n * n) as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| {
                pairwise_similarity_matrix(
                    black_box(&va),
                    black_box(&vb),
                    black_box(DistanceMetric::Cosine),
                    black_box(true),
                )
            })
        });
    }
    group.finish();
}

fn bench_metric_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("metric_comparison/dim=768_n=1000");
    group.sample_size(20);

    let dim = 768;
    let n = 1000;
    let query = make_random_vector(dim, 1);
    let corpus = make_random_vectors(n, dim, 100);
    let query_norm = normalize_vector_new(&query);
    let corpus_norm: Vec<Vec<f32>> = corpus.iter().map(|v| normalize_vector_new(v)).collect();

    group.throughput(Throughput::Elements(n as u64));

    group.bench_function("cosine_prenormalized", |bench| {
        bench.iter(|| {
            batch_cosine_similarity(
                black_box(&query_norm),
                black_box(&corpus_norm),
                black_box(true),
            )
        })
    });

    group.bench_function("cosine_raw", |bench| {
        bench.iter(|| {
            batch_cosine_similarity(black_box(&query), black_box(&corpus), black_box(false))
        })
    });

    group.bench_function("dot_product", |bench| {
        bench.iter(|| batch_dot_product(black_box(&query), black_box(&corpus)))
    });

    group.bench_function("euclidean", |bench| {
        bench.iter(|| batch_euclidean_similarity(black_box(&query), black_box(&corpus)))
    });

    group.finish();
}

criterion_group!(
    similarity_benches,
    bench_cosine_similarity_by_dimension,
    bench_cosine_similarity_prenormalized_by_dimension,
    bench_dot_product_by_dimension,
    bench_euclidean_distance_by_dimension,
    bench_batch_cosine_by_corpus_size,
    bench_batch_cosine_by_dimension,
    bench_batch_dot_product_by_corpus_size,
    bench_top_k_similarity,
    bench_pairwise_similarity_matrix,
    bench_metric_comparison,
);
criterion_main!(similarity_benches);
