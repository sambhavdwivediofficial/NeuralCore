// rust_engine/src/compression.rs

use crate::error::{EngineError, EngineResult};
use crate::types::CompressionStats;
use serde::{Deserialize, Serialize};
use std::time::Instant;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Hash)]
pub enum CompressionAlgorithm {
    Lz4,
    Zstd,
    Snappy,
    None,
}

impl std::fmt::Display for CompressionAlgorithm {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CompressionAlgorithm::Lz4 => write!(f, "lz4"),
            CompressionAlgorithm::Zstd => write!(f, "zstd"),
            CompressionAlgorithm::Snappy => write!(f, "snappy"),
            CompressionAlgorithm::None => write!(f, "none"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressionConfig {
    pub algorithm: CompressionAlgorithm,
    pub zstd_level: i32,
    pub min_size_to_compress: usize,
    pub max_decompressed_size: usize,
}

impl Default for CompressionConfig {
    fn default() -> Self {
        Self {
            algorithm: CompressionAlgorithm::Lz4,
            zstd_level: 3,
            min_size_to_compress: 256,
            max_decompressed_size: 256 * 1024 * 1024,
        }
    }
}

pub fn compress(
    data: &[u8],
    config: &CompressionConfig,
) -> EngineResult<(Vec<u8>, CompressionStats)> {
    if data.is_empty() {
        return Ok((
            Vec::new(),
            CompressionStats {
                original_size_bytes: 0,
                compressed_size_bytes: 0,
                compression_ratio: 1.0,
                algorithm: config.algorithm.to_string(),
                duration_micros: 0,
            },
        ));
    }

    if data.len() < config.min_size_to_compress {
        let mut output = vec![0u8];
        output.extend_from_slice(data);

        let compressed_size = output.len() - 1;

        return Ok((
            output,
            CompressionStats {
                original_size_bytes: data.len(),
                compressed_size_bytes: compressed_size,
                compression_ratio: 1.0,
                algorithm: "none".to_string(),
                duration_micros: 0,
            },
        ));
    }

    let start = Instant::now();
    let original_size = data.len();

    let compressed = match config.algorithm {
        CompressionAlgorithm::Lz4 => compress_lz4(data)?,
        CompressionAlgorithm::Zstd => compress_zstd(data, config.zstd_level)?,
        CompressionAlgorithm::Snappy => compress_snappy(data)?,
        CompressionAlgorithm::None => {
            let mut output = vec![0u8];
            output.extend_from_slice(data);
            output
        }
    };

    let duration = start.elapsed().as_micros() as u64;
    let compressed_size = compressed.len();
    let ratio = original_size as f64 / compressed_size as f64;

    Ok((
        compressed,
        CompressionStats {
            original_size_bytes: original_size,
            compressed_size_bytes: compressed_size,
            compression_ratio: ratio,
            algorithm: config.algorithm.to_string(),
            duration_micros: duration,
        },
    ))
}

pub fn decompress(data: &[u8], config: &CompressionConfig) -> EngineResult<Vec<u8>> {
    if data.is_empty() {
        return Ok(Vec::new());
    }

    if data[0] == 0 {
        return Ok(data[1..].to_vec());
    }

    match config.algorithm {
        CompressionAlgorithm::Lz4 => decompress_lz4(&data[1..], config.max_decompressed_size),
        CompressionAlgorithm::Zstd => decompress_zstd(&data[1..]),
        CompressionAlgorithm::Snappy => decompress_snappy(&data[1..]),
        CompressionAlgorithm::None => Ok(data[1..].to_vec()),
    }
}

fn compress_lz4(data: &[u8]) -> EngineResult<Vec<u8>> {
    #[cfg(feature = "compression")]
    {
        let compressed = lz4_flex::compress_prepend_size(data);
        let mut output = vec![1u8];
        output.extend_from_slice(&compressed);
        Ok(output)
    }
    #[cfg(not(feature = "compression"))]
    {
        let mut output = vec![0u8];
        output.extend_from_slice(data);
        Ok(output)
    }
}

fn decompress_lz4(data: &[u8], _max_size: usize) -> EngineResult<Vec<u8>> {
    #[cfg(feature = "compression")]
    {
        lz4_flex::decompress_size_prepended(data)
            .map_err(|e| EngineError::CompressionError(format!("LZ4 decompress error: {}", e)))
    }
    #[cfg(not(feature = "compression"))]
    {
        Ok(data.to_vec())
    }
}

fn compress_zstd(data: &[u8], level: i32) -> EngineResult<Vec<u8>> {
    #[cfg(feature = "compression")]
    {
        let compressed = zstd::encode_all(data, level)
            .map_err(|e| EngineError::CompressionError(format!("Zstd compress error: {}", e)))?;
        let mut output = vec![2u8];
        output.extend_from_slice(&compressed);
        Ok(output)
    }
    #[cfg(not(feature = "compression"))]
    {
        let mut output = vec![0u8];
        output.extend_from_slice(data);
        Ok(output)
    }
}

fn decompress_zstd(data: &[u8]) -> EngineResult<Vec<u8>> {
    #[cfg(feature = "compression")]
    {
        zstd::decode_all(data)
            .map_err(|e| EngineError::CompressionError(format!("Zstd decompress error: {}", e)))
    }
    #[cfg(not(feature = "compression"))]
    {
        Ok(data.to_vec())
    }
}

fn compress_snappy(data: &[u8]) -> EngineResult<Vec<u8>> {
    #[cfg(feature = "compression")]
    {
        let mut encoder = snap::write::FrameEncoder::new(Vec::new());
        use std::io::Write;
        encoder
            .write_all(data)
            .map_err(|e| EngineError::CompressionError(format!("Snappy compress error: {}", e)))?;
        let compressed = encoder
            .into_inner()
            .map_err(|e| EngineError::CompressionError(format!("Snappy flush error: {}", e)))?;
        let mut output = vec![3u8];
        output.extend_from_slice(&compressed);
        Ok(output)
    }
    #[cfg(not(feature = "compression"))]
    {
        let mut output = vec![0u8];
        output.extend_from_slice(data);
        Ok(output)
    }
}

fn decompress_snappy(data: &[u8]) -> EngineResult<Vec<u8>> {
    #[cfg(feature = "compression")]
    {
        let mut decoder = snap::read::FrameDecoder::new(data);
        let mut output = Vec::new();
        use std::io::Read;
        decoder.read_to_end(&mut output).map_err(|e| {
            EngineError::CompressionError(format!("Snappy decompress error: {}", e))
        })?;
        Ok(output)
    }
    #[cfg(not(feature = "compression"))]
    {
        Ok(data.to_vec())
    }
}

pub fn compress_vectors(
    vectors: &[Vec<f32>],
    config: &CompressionConfig,
) -> EngineResult<(Vec<u8>, CompressionStats)> {
    if vectors.is_empty() {
        return Ok((
            Vec::new(),
            CompressionStats {
                original_size_bytes: 0,
                compressed_size_bytes: 0,
                compression_ratio: 1.0,
                algorithm: config.algorithm.to_string(),
                duration_micros: 0,
            },
        ));
    }

    let n = vectors.len();
    let dim = vectors[0].len();
    let mut raw = Vec::with_capacity(8 + n * dim * 4);
    raw.extend_from_slice(&(n as u64).to_le_bytes());
    raw.extend_from_slice(&(dim as u64).to_le_bytes());
    for v in vectors {
        for &f in v {
            raw.extend_from_slice(&f.to_le_bytes());
        }
    }

    compress(&raw, config)
}

pub fn decompress_vectors(data: &[u8], config: &CompressionConfig) -> EngineResult<Vec<Vec<f32>>> {
    if data.is_empty() {
        return Ok(Vec::new());
    }

    let raw = decompress(data, config)?;

    if raw.len() < 16 {
        return Err(EngineError::CompressionError(
            "Decompressed vector data too small to contain header".to_string(),
        ));
    }

    let n = u64::from_le_bytes(raw[0..8].try_into().unwrap()) as usize;
    let dim = u64::from_le_bytes(raw[8..16].try_into().unwrap()) as usize;

    let expected_bytes = 16 + n * dim * 4;
    if raw.len() != expected_bytes {
        return Err(EngineError::CompressionError(format!(
            "Decompressed data length mismatch: expected {}, got {}",
            expected_bytes,
            raw.len()
        )));
    }

    let mut vectors = Vec::with_capacity(n);
    let mut offset = 16;
    for _ in 0..n {
        let mut v = Vec::with_capacity(dim);
        for _ in 0..dim {
            let bytes: [u8; 4] = raw[offset..offset + 4].try_into().unwrap();
            v.push(f32::from_le_bytes(bytes));
            offset += 4;
        }
        vectors.push(v);
    }

    Ok(vectors)
}

pub fn quantize_scalar_i8(
    vectors: &[Vec<f32>],
    quantile: f32,
) -> EngineResult<(Vec<Vec<i8>>, f32, f32)> {
    if vectors.is_empty() {
        return Ok((Vec::new(), 0.0, 0.0));
    }

    if !(0.0..=1.0).contains(&quantile) {
        return Err(EngineError::InvalidParameter {
            name: "quantile",
            value: quantile.to_string(),
            reason: "must be in range [0.0, 1.0]",
        });
    }

    let all_values: Vec<f32> = vectors.iter().flat_map(|v| v.iter().copied()).collect();
    let mut sorted = all_values.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let lower_idx = (((1.0 - quantile) * (sorted.len() as f32 - 1.0)).floor()) as usize;
    let upper_idx =
        (((quantile * (sorted.len() as f32 - 1.0)).ceil()) as usize).min(sorted.len() - 1);
    let min_val = sorted[lower_idx.min(sorted.len() - 1)];
    let max_val = sorted[upper_idx.min(sorted.len() - 1)];

    let range = max_val - min_val;
    if range < f32::EPSILON {
        let quantized: Vec<Vec<i8>> = vectors.iter().map(|v| vec![0i8; v.len()]).collect();
        return Ok((quantized, min_val, max_val));
    }

    let quantized: Vec<Vec<i8>> = vectors
        .iter()
        .map(|v| {
            v.iter()
                .map(|&x| {
                    let clamped = x.max(min_val).min(max_val);
                    let normalized = (clamped - min_val) / range;
                    let scaled = normalized * 254.0 - 127.0;
                    scaled.round().clamp(-127.0, 127.0) as i8
                })
                .collect()
        })
        .collect();

    Ok((quantized, min_val, max_val))
}

pub fn dequantize_scalar_i8(quantized: &[Vec<i8>], min_val: f32, max_val: f32) -> Vec<Vec<f32>> {
    let range = max_val - min_val;
    quantized
        .iter()
        .map(|v| {
            v.iter()
                .map(|&q| {
                    let normalized = (q as f32 + 127.0) / 254.0;
                    normalized * range + min_val
                })
                .collect()
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use approx::assert_relative_eq;

    fn default_config() -> CompressionConfig {
        CompressionConfig::default()
    }

    #[test]
    fn test_compress_decompress_roundtrip() {
        let config = default_config();
        let data =
            b"hello world this is test data for compression roundtrip testing neuralcore engine";
        let (compressed, stats) = compress(data, &config).unwrap();
        let decompressed = decompress(&compressed, &config).unwrap();
        assert_eq!(&decompressed, data);
        assert!(stats.original_size_bytes > 0);
    }

    #[test]
    fn test_compress_empty_data() {
        let config = default_config();
        let (compressed, stats) = compress(&[], &config).unwrap();
        assert!(compressed.is_empty());
        assert_eq!(stats.original_size_bytes, 0);
    }

    #[test]
    fn test_decompress_empty_data() {
        let config = default_config();
        let result = decompress(&[], &config).unwrap();
        assert!(result.is_empty());
    }

    #[test]
    fn test_small_data_skips_compression() {
        let config = CompressionConfig {
            min_size_to_compress: 1000,
            ..Default::default()
        };
        let data = b"short";
        let (compressed, _) = compress(data, &config).unwrap();
        assert_eq!(compressed[0], 0);
        let decompressed = decompress(&compressed, &config).unwrap();
        assert_eq!(&decompressed, data);
    }

    #[test]
    fn test_vector_compress_decompress_roundtrip() {
        let config = default_config();
        let vectors = vec![
            vec![0.1f32, 0.2, 0.3, 0.4],
            vec![0.5f32, 0.6, 0.7, 0.8],
            vec![0.9f32, 1.0, 0.0, -0.1],
        ];
        let (compressed, _) = compress_vectors(&vectors, &config).unwrap();
        let decompressed = decompress_vectors(&compressed, &config).unwrap();
        assert_eq!(decompressed.len(), vectors.len());
        for (orig, decomp) in vectors.iter().zip(decompressed.iter()) {
            for (&o, &d) in orig.iter().zip(decomp.iter()) {
                assert_relative_eq!(o, d, epsilon = 1e-6);
            }
        }
    }

    #[test]
    fn test_quantize_dequantize_i8_approximate() {
        let vectors = vec![
            vec![0.0f32, 0.5, 1.0, -0.5, -1.0],
            vec![0.25f32, 0.75, -0.25, -0.75, 0.0],
        ];
        let (quantized, min_val, max_val) = quantize_scalar_i8(&vectors, 0.99).unwrap();
        let restored = dequantize_scalar_i8(&quantized, min_val, max_val);
        for (orig, rest) in vectors.iter().zip(restored.iter()) {
            for (&o, &r) in orig.iter().zip(rest.iter()) {
                assert!(
                    (o - r).abs() < 0.05,
                    "Quantization error too large: {} vs {}",
                    o,
                    r
                );
            }
        }
    }

    #[test]
    fn test_quantize_empty_returns_empty() {
        let (q, _min, _max) = quantize_scalar_i8(&[], 0.99).unwrap();
        assert!(q.is_empty());
    }

    #[test]
    fn test_compression_stats_populated() {
        let config = default_config();
        let data: Vec<u8> = (0..1024).map(|i| (i % 256) as u8).collect();
        let (_, stats) = compress(&data, &config).unwrap();
        assert_eq!(stats.original_size_bytes, 1024);
        assert!(stats.compression_ratio > 0.0);
    }
}
