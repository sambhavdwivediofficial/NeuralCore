// rust_engine/benches/reranker_bench.rs

use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};
use neuralcore_engine::reranker::{
    compute_mrr, compute_ndcg, compute_precision_at_k, compute_recall_at_k, NormalizationMethod,
    RerankerConfig, RerankerType, ScoreFusion,
};
use neuralcore_engine::types::RankedResult;
use neuralcore_engine::utils::{min_max_normalize, reciprocal_rank_fusion, softmax};
use std::collections::HashSet;

fn make_ranked_list(n: usize, seed: u64) -> Vec<(String, f32)> {
    let mut state = seed;
    (0..n)
        .map(|i| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            let score = (state as f32) / (u64::MAX as f32);
            (format!("doc_{:06}", i), score)
        })
        .collect()
}

fn make_overlapping_lists(
    total_docs: usize,
    list_size: usize,
    num_lists: usize,
    overlap_fraction: f64,
) -> Vec<Vec<(String, f32)>> {
    let overlap_n = (list_size as f64 * overlap_fraction) as usize;
    let mut lists = Vec::with_capacity(num_lists);
    let mut rng_state: u64 = 0xdeadbeefcafebabe;

    let common_docs: Vec<String> = (0..overlap_n).map(|i| format!("common_{:04}", i)).collect();

    for l in 0..num_lists {
        let mut list: Vec<(String, f32)> = Vec::with_capacity(list_size);

        for doc in &common_docs {
            rng_state ^= rng_state << 13;
            rng_state ^= rng_state >> 7;
            rng_state ^= rng_state << 17;
            let score = (rng_state as f32) / (u64::MAX as f32);
            list.push((doc.clone(), score));
        }

        let unique_needed = list_size - overlap_n;
        for i in 0..unique_needed {
            rng_state ^= rng_state << 13;
            let score = (rng_state as f32) / (u64::MAX as f32);
            list.push((format!("list{}_doc_{:04}", l, i), score));
        }

        list.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        lists.push(list);
    }
    lists
}

fn make_ranked_results(n: usize) -> Vec<RankedResult> {
    (0..n)
        .map(|i| RankedResult {
            id: format!("doc_{:06}", i),
            rank: i + 1,
            score: 1.0 - (i as f32 / n as f32),
            original_score: None,
            original_rank: None,
        })
        .collect()
}

fn make_relevant_set(n_relevant: usize, total: usize) -> HashSet<String> {
    (0..n_relevant.min(total))
        .map(|i| format!("doc_{:06}", i))
        .collect()
}

fn bench_rrf_fusion_by_list_size(c: &mut Criterion) {
    let mut group = c.benchmark_group("rrf_fusion/by_list_size");

    let config = RerankerConfig {
        reranker_type: RerankerType::ReciprocalRankFusion,
        rrf_k: 60.0,
        top_n: 10,
        ..Default::default()
    };
    let fusion = ScoreFusion::new(config);

    for n in [10, 50, 100, 500, 1000] {
        let list1 = make_ranked_list(n, 42);
        let list2 = make_ranked_list(n, 99);
        let lists = vec![list1, list2];

        group.throughput(Throughput::Elements(n as u64 * 2));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| fusion.fuse(black_box(&lists)))
        });
    }
    group.finish();
}

fn bench_rrf_fusion_by_num_lists(c: &mut Criterion) {
    let mut group = c.benchmark_group("rrf_fusion/by_num_lists");

    let list_size = 100;
    for num_lists in [2, 3, 5, 10] {
        let config = RerankerConfig {
            reranker_type: RerankerType::ReciprocalRankFusion,
            rrf_k: 60.0,
            top_n: 10,
            ..Default::default()
        };
        let fusion = ScoreFusion::new(config);
        let lists: Vec<Vec<(String, f32)>> = (0..num_lists)
            .map(|i| make_ranked_list(list_size, i as u64 * 12345))
            .collect();

        group.throughput(Throughput::Elements((list_size * num_lists) as u64));
        group.bench_with_input(
            BenchmarkId::from_parameter(num_lists),
            &num_lists,
            |bench, _| bench.iter(|| fusion.fuse(black_box(&lists))),
        );
    }
    group.finish();
}

fn bench_fusion_strategy_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("fusion_strategy_comparison/n=100_lists=2");
    group.sample_size(50);

    let list_size = 100;
    let lists = make_overlapping_lists(200, list_size, 2, 0.5);

    let strategies = [
        RerankerType::ReciprocalRankFusion,
        RerankerType::WeightedFusion,
        RerankerType::Borda,
        RerankerType::SoftmaxFusion,
        RerankerType::ScoreNormalization,
    ];

    let strategy_names = ["rrf", "weighted", "borda", "softmax", "score_norm"];

    for (strategy, name) in strategies.into_iter().zip(strategy_names.iter()) {
        let config = RerankerConfig {
            reranker_type: strategy,
            top_n: 10,
            ..Default::default()
        };
        let fusion = ScoreFusion::new(config);

        group.bench_function(*name, |bench| bench.iter(|| fusion.fuse(black_box(&lists))));
    }
    group.finish();
}

fn bench_rrf_with_overlap_variation(c: &mut Criterion) {
    let mut group = c.benchmark_group("rrf_fusion/by_overlap");
    group.sample_size(30);

    let config = RerankerConfig {
        reranker_type: RerankerType::ReciprocalRankFusion,
        rrf_k: 60.0,
        top_n: 10,
        ..Default::default()
    };
    let fusion = ScoreFusion::new(config);

    for overlap in [0, 25, 50, 75, 100] {
        let lists = make_overlapping_lists(200, 100, 2, overlap as f64 / 100.0);

        group.bench_with_input(
            BenchmarkId::new("overlap_pct", overlap),
            &overlap,
            |bench, _| bench.iter(|| fusion.fuse(black_box(&lists))),
        );
    }
    group.finish();
}

fn bench_rrf_top_n_variation(c: &mut Criterion) {
    let mut group = c.benchmark_group("rrf_fusion/by_top_n");

    let list_size = 1000;
    let lists = vec![
        make_ranked_list(list_size, 42),
        make_ranked_list(list_size, 99),
    ];

    for top_n in [5, 10, 25, 50, 100, 500, 1000] {
        let config = RerankerConfig {
            reranker_type: RerankerType::ReciprocalRankFusion,
            rrf_k: 60.0,
            top_n,
            ..Default::default()
        };
        let fusion = ScoreFusion::new(config);

        group.throughput(Throughput::Elements(top_n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(top_n), &top_n, |bench, _| {
            bench.iter(|| fusion.fuse(black_box(&lists)))
        });
    }
    group.finish();
}

fn bench_rrf_k_variation(c: &mut Criterion) {
    let mut group = c.benchmark_group("rrf_fusion/by_rrf_k");

    let lists = vec![make_ranked_list(100, 42), make_ranked_list(100, 99)];

    for k_val in [10.0f32, 30.0, 60.0, 100.0, 200.0] {
        let config = RerankerConfig {
            reranker_type: RerankerType::ReciprocalRankFusion,
            rrf_k: k_val,
            top_n: 10,
            ..Default::default()
        };
        let fusion = ScoreFusion::new(config);

        group.bench_with_input(BenchmarkId::new("k", k_val as usize), &k_val, |bench, _| {
            bench.iter(|| fusion.fuse(black_box(&lists)))
        });
    }
    group.finish();
}

fn bench_ndcg_by_result_count(c: &mut Criterion) {
    let mut group = c.benchmark_group("metrics/ndcg_by_result_count");

    for n in [10, 50, 100, 500, 1000] {
        let results = make_ranked_results(n);
        let relevant = make_relevant_set(n / 5, n);

        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| compute_ndcg(black_box(&results), black_box(&relevant), black_box(n)))
        });
    }
    group.finish();
}

fn bench_mrr_by_result_count(c: &mut Criterion) {
    let mut group = c.benchmark_group("metrics/mrr_by_result_count");

    for n in [10, 50, 100, 500, 1000] {
        let results = make_ranked_results(n);
        let relevant = make_relevant_set(1, n);

        group.throughput(Throughput::Elements(n as u64));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| compute_mrr(black_box(&results), black_box(&relevant)))
        });
    }
    group.finish();
}

fn bench_all_metrics_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("metrics/comparison_n=100");
    group.sample_size(50);

    let n = 100;
    let results = make_ranked_results(n);
    let relevant = make_relevant_set(20, n);
    let k = 10;

    group.bench_function("ndcg@k", |bench| {
        bench.iter(|| compute_ndcg(black_box(&results), black_box(&relevant), black_box(k)))
    });

    group.bench_function("mrr", |bench| {
        bench.iter(|| compute_mrr(black_box(&results), black_box(&relevant)))
    });

    group.bench_function("precision@k", |bench| {
        bench.iter(|| {
            compute_precision_at_k(black_box(&results), black_box(&relevant), black_box(k))
        })
    });

    group.bench_function("recall@k", |bench| {
        bench.iter(|| compute_recall_at_k(black_box(&results), black_box(&relevant), black_box(k)))
    });

    group.finish();
}

fn bench_normalization_methods(c: &mut Criterion) {
    let mut group = c.benchmark_group("normalization/by_method");

    for n in [10, 100, 1000] {
        let scores: Vec<f32> = (0..n).map(|i| i as f32 * 0.001).collect();

        group.bench_with_input(BenchmarkId::new("min_max", n), &n, |bench, _| {
            bench.iter(|| min_max_normalize(black_box(&scores)))
        });

        group.bench_with_input(BenchmarkId::new("softmax", n), &n, |bench, _| {
            bench.iter(|| softmax(black_box(&scores)))
        });
    }
    group.finish();
}

fn bench_rrf_utility(c: &mut Criterion) {
    let mut group = c.benchmark_group("rrf_utility/by_list_size");

    for n in [50, 100, 500, 1000] {
        let list1: Vec<(String, usize)> = (0..n).map(|i| (format!("doc_{}", i), i + 1)).collect();
        let list2: Vec<(String, usize)> = (0..n)
            .map(|i| (format!("doc_{}", n - i - 1), i + 1))
            .collect();
        let lists = vec![list1, list2];

        group.throughput(Throughput::Elements(n as u64 * 2));
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |bench, _| {
            bench.iter(|| reciprocal_rank_fusion(black_box(&lists), black_box(60.0)))
        });
    }
    group.finish();
}

criterion_group!(
    reranker_benches,
    bench_rrf_fusion_by_list_size,
    bench_rrf_fusion_by_num_lists,
    bench_fusion_strategy_comparison,
    bench_rrf_with_overlap_variation,
    bench_rrf_top_n_variation,
    bench_rrf_k_variation,
    bench_ndcg_by_result_count,
    bench_mrr_by_result_count,
    bench_all_metrics_comparison,
    bench_normalization_methods,
    bench_rrf_utility,
);
criterion_main!(reranker_benches);
