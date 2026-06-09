// rust_engine/src/main.rs

#[cfg(feature = "cli")]
mod cli {
    use neuralcore_engine::compression::{
        compress, decompress, CompressionAlgorithm, CompressionConfig,
    };
    use neuralcore_engine::reranker::{RerankerConfig, RerankerType, ScoreFusion};
    use neuralcore_engine::similarity::batch_cosine_similarity;
    use neuralcore_engine::tokenizer::count_tokens_approximate;
    use neuralcore_engine::types::DistanceMetric;
    use neuralcore_engine::vector_index::{IndexConfig, VectorIndex};
    use clap::{Parser, Subcommand};
    use std::path::PathBuf;
    use std::time::Instant;

    #[derive(Parser, Debug)]
    #[command(
        name = "neuralcore_engine",
        version = env!("CARGO_PKG_VERSION"),
        author = "Sambhav Dwivedi",
        about = "NeuralCore Rust Engine — high-performance AI inference utilities",
        long_about = "
NeuralCore Rust Engine provides high-performance implementations of:
  - Vector similarity computation (cosine, dot product, euclidean, manhattan)
  - HNSW vector indexing and search
  - Score fusion and reranking (RRF, weighted, borda, softmax)
  - Retrieval evaluation metrics (NDCG, MRR, Precision@K, Recall@K)
  - Text tokenization and token counting
  - Data compression (LZ4, Zstd, Snappy)
  - Vector quantization (scalar int8)
  - LRU/LFU caching with TTL support

All operations are designed for use with full error handling,
parallel execution via Rayon, and Python FFI via PyO3.
"
    )]
    pub struct Cli {
        #[command(subcommand)]
        pub command: Commands,

        #[arg(long, global = true, help = "Output format: text, json")]
        pub output: Option<String>,

        #[arg(long, global = true, help = "Enable verbose output")]
        pub verbose: bool,
    }

    #[derive(Subcommand, Debug)]
    pub enum Commands {
        Bench(BenchArgs),
        Similarity(SimilarityArgs),
        Index(IndexArgs),
        Tokenize(TokenizeArgs),
        Compress(CompressArgs),
        Rerank(RerankArgs),
        Info,
    }

    #[derive(clap::Args, Debug)]
    #[command(about = "Run performance benchmarks")]
    pub struct BenchArgs {
        #[arg(long, default_value = "all", help = "Benchmark to run: all, similarity, index, tokenizer, reranker, compression")]
        pub target: String,

        #[arg(long, default_value_t = 1000, help = "Number of vectors for index benchmarks")]
        pub num_vectors: usize,

        #[arg(long, default_value_t = 1536, help = "Vector dimension")]
        pub dimension: usize,

        #[arg(long, default_value_t = 10, help = "Number of benchmark iterations")]
        pub iterations: usize,

        #[arg(long, default_value_t = 10, help = "Top-K for search benchmarks")]
        pub top_k: usize,

        #[arg(long, help = "Write benchmark results to JSON file")]
        pub output_file: Option<PathBuf>,
    }

    #[derive(clap::Args, Debug)]
    #[command(about = "Compute vector similarity")]
    pub struct SimilarityArgs {
        #[arg(long, help = "Vector A as comma-separated floats: 0.1,0.2,0.3")]
        pub vec_a: String,

        #[arg(long, help = "Vector B as comma-separated floats: 0.4,0.5,0.6")]
        pub vec_b: String,

        #[arg(long, default_value = "cosine", help = "Metric: cosine, dot_product, euclidean, manhattan")]
        pub metric: String,

        #[arg(long, help = "Vectors are pre-normalized (skips normalization for cosine)")]
        pub prenormalized: bool,
    }

    #[derive(clap::Args, Debug)]
    #[command(about = "Vector index operations")]
    pub struct IndexArgs {
        #[command(subcommand)]
        pub operation: IndexOperation,
    }

    #[derive(Subcommand, Debug)]
    pub enum IndexOperation {
        #[command(about = "Run a smoke-test on the HNSW index")]
        Smoketest {
            #[arg(long, default_value_t = 500)]
            num_vectors: usize,
            #[arg(long, default_value_t = 128)]
            dimension: usize,
            #[arg(long, default_value_t = 5)]
            top_k: usize,
        },
    }

    #[derive(clap::Args, Debug)]
    #[command(about = "Tokenize text and count tokens")]
    pub struct TokenizeArgs {
        #[arg(help = "Text to tokenize")]
        pub text: String,

        #[arg(long, help = "Also truncate text to fit within max_tokens")]
        pub max_tokens: Option<usize>,
    }

    #[derive(clap::Args, Debug)]
    #[command(about = "Compress or decompress data")]
    pub struct CompressArgs {
        #[command(subcommand)]
        pub operation: CompressOperation,
    }

    #[derive(Subcommand, Debug)]
    pub enum CompressOperation {
        #[command(about = "Compress a file")]
        Compress {
            #[arg(help = "Input file path")]
            input: PathBuf,
            #[arg(help = "Output file path")]
            output: PathBuf,
            #[arg(long, default_value = "lz4", help = "Algorithm: lz4, zstd, snappy")]
            algorithm: String,
            #[arg(long, default_value_t = 3)]
            zstd_level: i32,
        },
        #[command(about = "Decompress a file")]
        Decompress {
            #[arg(help = "Input file path")]
            input: PathBuf,
            #[arg(help = "Output file path")]
            output: PathBuf,
            #[arg(long, default_value = "lz4")]
            algorithm: String,
        },
        #[command(about = "Benchmark compression on random data")]
        Benchmark {
            #[arg(long, default_value_t = 1_000_000)]
            size_bytes: usize,
            #[arg(long, default_value_t = 5)]
            iterations: usize,
        },
    }

    #[derive(clap::Args, Debug)]
    #[command(about = "Rerank search results using score fusion")]
    pub struct RerankArgs {
        #[arg(long, default_value = "rrf", help = "Strategy: rrf, weighted, borda, softmax, score_norm")]
        pub strategy: String,

        #[arg(long, default_value_t = 60.0)]
        pub rrf_k: f32,

        #[arg(long, default_value_t = 10)]
        pub top_n: usize,
    }

    pub fn run(cli: Cli) {
        let use_json = cli.output.as_deref() == Some("json");
        match cli.command {
            Commands::Info => cmd_info(use_json),
            Commands::Similarity(args) => cmd_similarity(args, use_json),
            Commands::Index(args) => cmd_index(args, cli.verbose, use_json),
            Commands::Tokenize(args) => cmd_tokenize(args, use_json),
            Commands::Compress(args) => cmd_compress(args, use_json),
            Commands::Rerank(args) => cmd_rerank(args, use_json),
            Commands::Bench(args) => cmd_bench(args, use_json),
        }
    }

    fn cmd_info(use_json: bool) {
        let info = serde_json::json!({
            "name": neuralcore_engine::NAME,
            "version": neuralcore_engine::VERSION,
            "build_profile": if cfg!(debug_assertions) { "debug" } else { "release" },
            "features": {
                "simd": cfg!(feature = "simd"),
                "compression": cfg!(feature = "compression"),
                "python_bindings": cfg!(feature = "python-bindings"),
                "onnx": cfg!(feature = "onnx"),
                "cli": cfg!(feature = "cli"),
            },
            "cpu_cores": num_cpus::get(),
            "cpu_cores_physical": num_cpus::get_physical(),
            "rust_version": env!("CARGO_PKG_RUST_VERSION"),
        });

        if use_json {
            println!("{}", serde_json::to_string_pretty(&info).unwrap());
        } else {
            println!("NeuralCore Rust Engine");
            println!("  Version      : {}", neuralcore_engine::VERSION);
            println!("  Build        : {}", if cfg!(debug_assertions) { "debug" } else { "release" });
            println!("  CPU Cores    : {} logical / {} physical", num_cpus::get(), num_cpus::get_physical());
            println!("  SIMD         : {}", cfg!(feature = "simd"));
            println!("  Compression  : {}", cfg!(feature = "compression"));
            println!("  Python FFI   : {}", cfg!(feature = "python-bindings"));
            println!("  ONNX Runtime : {}", cfg!(feature = "onnx"));
        }
    }

    fn cmd_similarity(args: SimilarityArgs, use_json: bool) {
        let parse_vec = |s: &str| -> Vec<f32> {
            s.split(',')
                .filter_map(|x| x.trim().parse::<f32>().ok())
                .collect()
        };

        let a = parse_vec(&args.vec_a);
        let b = parse_vec(&args.vec_b);

        if a.is_empty() || b.is_empty() {
            eprintln!("Error: could not parse vectors. Format: 0.1,0.2,0.3");
            std::process::exit(1);
        }

        let metric: DistanceMetric = match args.metric.parse() {
            Ok(m) => m,
            Err(e) => {
                eprintln!("Error: {}", e);
                std::process::exit(1);
            }
        };

        let start = Instant::now();
        let score = neuralcore_engine::similarity::compute_similarity(&a, &b, metric, args.prenormalized);
        let elapsed = start.elapsed();

        match score {
            Ok(s) => {
                if use_json {
                    println!(
                        "{}",
                        serde_json::json!({
                            "score": s,
                            "metric": args.metric,
                            "dim_a": a.len(),
                            "dim_b": b.len(),
                            "elapsed_us": elapsed.as_micros(),
                        })
                    );
                } else {
                    println!("Similarity ({}) : {:.8}", args.metric, s);
                    println!("Elapsed        : {:?}", elapsed);
                }
            }
            Err(e) => {
                eprintln!("Error: {}", e);
                std::process::exit(1);
            }
        }
    }

    fn cmd_index(args: IndexArgs, _verbose: bool, use_json: bool) {
        match args.operation {
            IndexOperation::Smoketest {
                num_vectors,
                dimension,
                top_k,
            } => {
                println!("Running HNSW index smoketest: {} vectors, dim={}, k={}", num_vectors, dimension, top_k);

                let config = IndexConfig::hnsw(dimension, DistanceMetric::Cosine);
                let index = VectorIndex::new(config);

                let add_start = Instant::now();
                for i in 0..num_vectors {
                    let v: Vec<f32> = (0..dimension)
                        .map(|j| ((i * dimension + j) as f32).sin())
                        .collect();
                    if let Err(e) = index.add(format!("vec_{}", i), v, None) {
                        eprintln!("Add error at {}: {}", i, e);
                        std::process::exit(1);
                    }
                }
                let add_elapsed = add_start.elapsed();

                let query: Vec<f32> = (0..dimension).map(|j| (j as f32).sin()).collect();
                let search_start = Instant::now();
                let results = index.search(&query, top_k, None, None);
                let search_elapsed = search_start.elapsed();

                match results {
                    Ok(r) => {
                        if use_json {
                            println!(
                                "{}",
                                serde_json::json!({
                                    "status": "ok",
                                    "num_vectors": num_vectors,
                                    "dimension": dimension,
                                    "top_k": top_k,
                                    "indexed": index.len(),
                                    "results_count": r.len(),
                                    "add_elapsed_ms": add_elapsed.as_millis(),
                                    "search_elapsed_us": search_elapsed.as_micros(),
                                    "top_result": r.first().map(|x| serde_json::json!({"id": x.id, "score": x.score})),
                                })
                            );
                        } else {
                            println!("  Indexed   : {}", index.len());
                            println!("  Add time  : {:?} ({:.2}k vec/s)", add_elapsed,
                                num_vectors as f64 / add_elapsed.as_secs_f64() / 1000.0);
                            println!("  Search    : {:?}", search_elapsed);
                            println!("  Results   : {}", r.len());
                            if let Some(top) = r.first() {
                                println!("  Top result: {} (score={:.6})", top.id, top.score);
                            }
                            println!("  PASS");
                        }
                    }
                    Err(e) => {
                        eprintln!("Search error: {}", e);
                        std::process::exit(1);
                    }
                }
            }
        }
    }

    fn cmd_tokenize(args: TokenizeArgs, use_json: bool) {
        let approx = count_tokens_approximate(&args.text);

        if use_json {
            let mut result = serde_json::json!({
                "text_length_chars": args.text.len(),
                "approximate_tokens": approx,
            });
            if let Some(max) = args.max_tokens {
                let fits = neuralcore_engine::tokenizer::fits_in_context(&args.text, max, 2);
                result["fits_in_context"] = serde_json::Value::Bool(fits);
                result["max_tokens"] = serde_json::Value::Number(max.into());
            }
            println!("{}", serde_json::to_string_pretty(&result).unwrap());
        } else {
            println!("Text length      : {} chars", args.text.len());
            println!("Approx tokens    : {}", approx);
            if let Some(max) = args.max_tokens {
                let fits = neuralcore_engine::tokenizer::fits_in_context(&args.text, max, 2);
                println!("Max tokens       : {}", max);
                println!("Fits in context  : {}", fits);
            }
        }
    }

    fn cmd_compress(args: CompressArgs, use_json: bool) {
        match args.operation {
            CompressOperation::Compress { input, output, algorithm, zstd_level } => {
                let data = std::fs::read(&input).unwrap_or_else(|e| {
                    eprintln!("Error reading {}: {}", input.display(), e);
                    std::process::exit(1);
                });

                let alg = parse_algorithm(&algorithm);
                let config = CompressionConfig {
                    algorithm: alg,
                    zstd_level,
                    min_size_to_compress: 0,
                    ..Default::default()
                };

                let _start = Instant::now();
                match compress(&data, &config) {
                    Ok((compressed, stats)) => {
                        std::fs::write(&output, &compressed).unwrap_or_else(|e| {
                            eprintln!("Error writing {}: {}", output.display(), e);
                            std::process::exit(1);
                        });
                        if use_json {
                            println!("{}", serde_json::to_string_pretty(&serde_json::json!({
                                "original_bytes": stats.original_size_bytes,
                                "compressed_bytes": stats.compressed_size_bytes,
                                "ratio": stats.compression_ratio,
                                "algorithm": stats.algorithm,
                                "elapsed_us": stats.duration_micros,
                            })).unwrap());
                        } else {
                            println!("Original     : {} bytes", stats.original_size_bytes);
                            println!("Compressed   : {} bytes", stats.compressed_size_bytes);
                            println!("Ratio        : {:.3}x", stats.compression_ratio);
                            println!("Algorithm    : {}", stats.algorithm);
                            println!("Time         : {}μs", stats.duration_micros);
                        }
                    }
                    Err(e) => {
                        eprintln!("Compress error: {}", e);
                        std::process::exit(1);
                    }
                }
            }
            CompressOperation::Decompress { input, output, algorithm } => {
                let data = std::fs::read(&input).unwrap_or_else(|e| {
                    eprintln!("Error reading {}: {}", input.display(), e);
                    std::process::exit(1);
                });
                let config = CompressionConfig {
                    algorithm: parse_algorithm(&algorithm),
                    ..Default::default()
                };
                match decompress(&data, &config) {
                    Ok(decompressed) => {
                        std::fs::write(&output, &decompressed).unwrap_or_else(|e| {
                            eprintln!("Error writing {}: {}", output.display(), e);
                            std::process::exit(1);
                        });
                        println!("Decompressed {} bytes -> {} bytes", data.len(), decompressed.len());
                    }
                    Err(e) => {
                        eprintln!("Decompress error: {}", e);
                        std::process::exit(1);
                    }
                }
            }
            CompressOperation::Benchmark { size_bytes, iterations } => {
                println!("Compression benchmark: {} bytes x {} iterations", size_bytes, iterations);
                let data: Vec<u8> = (0..size_bytes).map(|i| (i % 256) as u8).collect();
                let algorithms = [
                    CompressionAlgorithm::Lz4,
                    CompressionAlgorithm::Zstd,
                    CompressionAlgorithm::Snappy,
                ];
                let mut results = Vec::new();
                for alg in &algorithms {
                    let config = CompressionConfig {
                        algorithm: *alg,
                        min_size_to_compress: 0,
                        ..Default::default()
                    };
                    let mut total_compress_us = 0u64;
                    let mut total_decompress_us = 0u64;
                    let mut ratio = 0.0f64;
                    for _ in 0..iterations {
                        let start = Instant::now();
                        let (compressed, stats) = compress(&data, &config).unwrap();
                        total_compress_us += start.elapsed().as_micros() as u64;
                        ratio = stats.compression_ratio;
                        let start = Instant::now();
                        let _ = decompress(&compressed, &config).unwrap();
                        total_decompress_us += start.elapsed().as_micros() as u64;
                    }
                    let avg_c = total_compress_us / iterations as u64;
                    let avg_d = total_decompress_us / iterations as u64;
                    results.push(serde_json::json!({
                        "algorithm": alg.to_string(),
                        "ratio": ratio,
                        "avg_compress_us": avg_c,
                        "avg_decompress_us": avg_d,
                        "compress_mb_per_s": (size_bytes as f64 / 1_000_000.0) / (avg_c as f64 / 1_000_000.0),
                        "decompress_mb_per_s": (size_bytes as f64 / 1_000_000.0) / (avg_d as f64 / 1_000_000.0),
                    }));
                    if !use_json {
                        println!("  {:8} | ratio={:.3}x | compress={:6}μs | decompress={:6}μs | {:.0} MB/s compress",
                            alg.to_string(), ratio, avg_c, avg_d,
                            (size_bytes as f64 / 1_000_000.0) / (avg_c as f64 / 1_000_000.0));
                    }
                }
                if use_json {
                    println!("{}", serde_json::to_string_pretty(&results).unwrap());
                }
            }
        }
    }

    fn cmd_rerank(args: RerankArgs, use_json: bool) {
        let lists = vec![
            vec![
                ("doc_a".to_string(), 0.92f32),
                ("doc_b".to_string(), 0.85),
                ("doc_c".to_string(), 0.71),
                ("doc_d".to_string(), 0.60),
                ("doc_e".to_string(), 0.45),
            ],
            vec![
                ("doc_b".to_string(), 0.91f32),
                ("doc_d".to_string(), 0.83),
                ("doc_a".to_string(), 0.75),
                ("doc_f".to_string(), 0.55),
                ("doc_c".to_string(), 0.40),
            ],
        ];

        let reranker_type = match args.strategy.as_str() {
            "rrf" | "reciprocal_rank_fusion" => RerankerType::ReciprocalRankFusion,
            "weighted" => RerankerType::WeightedFusion,
            "borda" => RerankerType::Borda,
            "softmax" => RerankerType::SoftmaxFusion,
            "score_norm" => RerankerType::ScoreNormalization,
            other => {
                eprintln!("Unknown strategy: {}", other);
                std::process::exit(1);
            }
        };

        let config = RerankerConfig {
            reranker_type,
            rrf_k: args.rrf_k,
            top_n: args.top_n,
            ..Default::default()
        };

        let fusion = ScoreFusion::new(config);
        match fusion.fuse(&lists) {
            Ok(results) => {
                if use_json {
                    let json_results: Vec<serde_json::Value> = results
                        .iter()
                        .map(|r| serde_json::json!({"rank": r.rank, "id": r.id, "score": r.score}))
                        .collect();
                    println!("{}", serde_json::to_string_pretty(&json_results).unwrap());
                } else {
                    println!("Fusion results (strategy={}, rrf_k={}):", args.strategy, args.rrf_k);
                    for r in &results {
                        println!("  #{} {:8} score={:.6}", r.rank, r.id, r.score);
                    }
                }
            }
            Err(e) => {
                eprintln!("Rerank error: {}", e);
                std::process::exit(1);
            }
        }
    }

    fn cmd_bench(args: BenchArgs, use_json: bool) {
        let mut all_results: Vec<serde_json::Value> = Vec::new();
        let run_all = args.target == "all";

        if run_all || args.target == "similarity" {
            let result = bench_similarity(args.dimension, args.iterations, &args.target);
            if !use_json {
                println!("[similarity] dim={} iters={} | avg={:.2}μs | throughput={:.0}k ops/s",
                    args.dimension, args.iterations,
                    result["avg_us"].as_f64().unwrap_or(0.0),
                    result["throughput_kops"].as_f64().unwrap_or(0.0));
            }
            all_results.push(result);
        }

        if run_all || args.target == "batch_similarity" {
            let result = bench_batch_similarity(args.dimension, args.num_vectors, args.iterations);
            if !use_json {
                println!("[batch_sim] dim={} n={} iters={} | avg={:.2}ms | throughput={:.0}k vec/s",
                    args.dimension, args.num_vectors, args.iterations,
                    result["avg_ms"].as_f64().unwrap_or(0.0),
                    result["throughput_kvec_per_s"].as_f64().unwrap_or(0.0));
            }
            all_results.push(result);
        }

        if run_all || args.target == "index" {
            let result = bench_index(args.dimension, args.num_vectors, args.top_k, args.iterations);
            if !use_json {
                println!("[index] dim={} n={} k={} | add={:.2}ms | search={:.2}μs | add_throughput={:.1}k vec/s",
                    args.dimension, args.num_vectors, args.top_k,
                    result["add_total_ms"].as_f64().unwrap_or(0.0),
                    result["search_avg_us"].as_f64().unwrap_or(0.0),
                    result["add_throughput_kvec_per_s"].as_f64().unwrap_or(0.0));
            }
            all_results.push(result);
        }

        if run_all || args.target == "tokenizer" {
            let result = bench_tokenizer(args.iterations);
            if !use_json {
                println!("[tokenizer] iters={} | avg={:.2}μs | throughput={:.0}k docs/s",
                    args.iterations,
                    result["avg_us"].as_f64().unwrap_or(0.0),
                    result["throughput_kdocs"].as_f64().unwrap_or(0.0));
            }
            all_results.push(result);
        }

        if run_all || args.target == "compression" {
            let result = bench_compression(args.iterations);
            if !use_json {
                println!("[compression] iters={} | lz4_compress={:.0}μs | lz4_ratio={:.3}x",
                    args.iterations,
                    result["lz4_avg_compress_us"].as_f64().unwrap_or(0.0),
                    result["lz4_ratio"].as_f64().unwrap_or(0.0));
            }
            all_results.push(result);
        }

        if use_json {
            println!("{}", serde_json::to_string_pretty(&all_results).unwrap());
        }
    }

    fn bench_similarity(dim: usize, iterations: usize, _target: &str) -> serde_json::Value {
        let a: Vec<f32> = (0..dim).map(|i| (i as f32).sin()).collect();
        let b: Vec<f32> = (0..dim).map(|i| (i as f32).cos()).collect();
        let a_norm = neuralcore_engine::utils::normalize_vector_new(&a);
        let b_norm = neuralcore_engine::utils::normalize_vector_new(&b);

        let start = Instant::now();
        for _ in 0..iterations {
            let _ = cosine_similarity_prenormalized(&a_norm, &b_norm);
        }
        let elapsed = start.elapsed();
        let avg_us = elapsed.as_micros() as f64 / iterations as f64;

        serde_json::json!({
            "benchmark": "similarity",
            "dimension": dim,
            "iterations": iterations,
            "avg_us": avg_us,
            "total_us": elapsed.as_micros(),
            "throughput_kops": 1_000.0 / avg_us,
        })
    }

    fn cosine_similarity_prenormalized(a: &[f32], b: &[f32]) -> f32 {
        a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
    }

    fn bench_batch_similarity(dim: usize, n: usize, iterations: usize) -> serde_json::Value {
        let query: Vec<f32> = (0..dim).map(|i| (i as f32).sin()).collect();
        let vectors: Vec<Vec<f32>> = (0..n)
            .map(|i| (0..dim).map(|j| ((i * dim + j) as f32).cos()).collect())
            .collect();

        let start = Instant::now();
        for _ in 0..iterations {
            let _ = batch_cosine_similarity(&query, &vectors, false);
        }
        let elapsed = start.elapsed();
        let avg_ms = elapsed.as_millis() as f64 / iterations as f64;

        serde_json::json!({
            "benchmark": "batch_similarity",
            "dimension": dim,
            "num_vectors": n,
            "iterations": iterations,
            "avg_ms": avg_ms,
            "throughput_kvec_per_s": (n as f64 / 1000.0) / (avg_ms / 1000.0),
        })
    }

    fn bench_index(dim: usize, n: usize, k: usize, _iterations: usize) -> serde_json::Value {
        let config = IndexConfig::hnsw(dim, DistanceMetric::Cosine);
        let index = VectorIndex::new(config);

        let add_start = Instant::now();
        for i in 0..n {
            let v: Vec<f32> = (0..dim).map(|j| ((i * dim + j) as f32).sin()).collect();
            let _ = index.add(format!("v{}", i), v, None);
        }
        let add_elapsed = add_start.elapsed();

        let query: Vec<f32> = (0..dim).map(|j| (j as f32).sin()).collect();
        let search_start = Instant::now();
        for _ in 0..100 {
            let _ = index.search(&query, k, None, None);
        }
        let search_elapsed = search_start.elapsed();

        serde_json::json!({
            "benchmark": "index",
            "dimension": dim,
            "num_vectors": n,
            "top_k": k,
            "add_total_ms": add_elapsed.as_millis(),
            "add_throughput_kvec_per_s": (n as f64 / 1000.0) / add_elapsed.as_secs_f64(),
            "search_avg_us": search_elapsed.as_micros() as f64 / 100.0,
            "search_throughput_qps": 100_000_000.0 / search_elapsed.as_micros() as f64,
        })
    }

    fn bench_tokenizer(iterations: usize) -> serde_json::Value {
        let texts = vec![
            "The quick brown fox jumps over the lazy dog and demonstrates tokenization speed.",
            "NeuralCore is a production-grade AI infrastructure platform for enterprise use.",
            "Retrieval-augmented generation combines vector search with large language model inference.",
        ];

        let start = Instant::now();
        for _ in 0..iterations {
            for text in &texts {
                let _ = count_tokens_approximate(text);
            }
        }
        let elapsed = start.elapsed();
        let total_docs = iterations * texts.len();
        let avg_us = elapsed.as_micros() as f64 / total_docs as f64;

        serde_json::json!({
            "benchmark": "tokenizer",
            "iterations": iterations,
            "total_docs": total_docs,
            "avg_us": avg_us,
            "throughput_kdocs": 1_000.0 / avg_us,
        })
    }

    fn bench_compression(iterations: usize) -> serde_json::Value {
        let data: Vec<u8> = (0..65536).map(|i| (i % 256) as u8).collect();
        let config = CompressionConfig {
            algorithm: CompressionAlgorithm::Lz4,
            min_size_to_compress: 0,
            ..Default::default()
        };

        let start = Instant::now();
        let mut ratio = 1.0f64;
        for _ in 0..iterations {
            let (c, stats) = compress(&data, &config).unwrap();
            ratio = stats.compression_ratio;
            let _ = decompress(&c, &config).unwrap();
        }
        let elapsed = start.elapsed();

        serde_json::json!({
            "benchmark": "compression",
            "data_size_bytes": data.len(),
            "iterations": iterations,
            "lz4_avg_compress_us": elapsed.as_micros() as f64 / (iterations * 2) as f64,
            "lz4_ratio": ratio,
        })
    }

    fn parse_algorithm(s: &str) -> CompressionAlgorithm {
        match s {
            "lz4" => CompressionAlgorithm::Lz4,
            "zstd" => CompressionAlgorithm::Zstd,
            "snappy" => CompressionAlgorithm::Snappy,
            _ => CompressionAlgorithm::Lz4,
        }
    }
}

fn main() {
    #[cfg(feature = "cli")]
    {
        use clap::Parser;
        let cli = cli::Cli::parse();
        cli::run(cli);
    }

    #[cfg(not(feature = "cli"))]
    {
        eprintln!(
            "neuralcore_engine v{} — compiled without CLI feature.",
            neuralcore_engine::VERSION
        );
        eprintln!("Rebuild with: cargo build --features cli");
        std::process::exit(1);
    }
}