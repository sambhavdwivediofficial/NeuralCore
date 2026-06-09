// rust_engine/src/tokenizer.rs

use crate::error::{EngineError, EngineResult};
use crate::types::{BatchTokenizerOutput, TokenId, TokenizerOutput};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use unicode_normalization::UnicodeNormalization;
use unicode_segmentation::UnicodeSegmentation;

const DEFAULT_MAX_LENGTH: usize = 512;
const DEFAULT_UNK_TOKEN: &str = "[UNK]";
const DEFAULT_PAD_TOKEN: &str = "[PAD]";
const DEFAULT_CLS_TOKEN: &str = "[CLS]";
const DEFAULT_SEP_TOKEN: &str = "[SEP]";
const DEFAULT_MASK_TOKEN: &str = "[MASK]";
const BPE_CONTINUATION: &str = "##";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TokenizerType {
    WordPiece,
    BPE,
    SentencePiece,
    Whitespace,
    Character,
    Unigram,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TruncationStrategy {
    LongestFirst,
    OnlyFirst,
    OnlySecond,
    DoNotTruncate,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PaddingStrategy {
    Longest,
    MaxLength,
    DoNotPad,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpecialTokens {
    pub unk_token: String,
    pub pad_token: String,
    pub cls_token: String,
    pub sep_token: String,
    pub mask_token: String,
    pub bos_token: Option<String>,
    pub eos_token: Option<String>,
    pub additional_special_tokens: Vec<String>,
}

impl Default for SpecialTokens {
    fn default() -> Self {
        Self {
            unk_token: DEFAULT_UNK_TOKEN.to_string(),
            pad_token: DEFAULT_PAD_TOKEN.to_string(),
            cls_token: DEFAULT_CLS_TOKEN.to_string(),
            sep_token: DEFAULT_SEP_TOKEN.to_string(),
            mask_token: DEFAULT_MASK_TOKEN.to_string(),
            bos_token: None,
            eos_token: None,
            additional_special_tokens: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenizerConfig {
    pub tokenizer_type: TokenizerType,
    pub max_length: usize,
    pub truncation_strategy: TruncationStrategy,
    pub padding_strategy: PaddingStrategy,
    pub pad_to_multiple_of: Option<usize>,
    pub add_special_tokens: bool,
    pub do_lower_case: bool,
    pub strip_accents: bool,
    pub clean_text: bool,
    pub tokenize_chinese_chars: bool,
    pub strip_whitespace: bool,
    pub unicode_normalization_form: UnicodeNormForm,
    pub return_token_type_ids: bool,
    pub return_attention_mask: bool,
    pub return_special_tokens_mask: bool,
    pub return_offsets: bool,
    pub return_tokens: bool,
    pub special_tokens: SpecialTokens,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum UnicodeNormForm {
    NFC,
    NFD,
    NFKC,
    NFKD,
    None,
}

impl Default for TokenizerConfig {
    fn default() -> Self {
        Self {
            tokenizer_type: TokenizerType::WordPiece,
            max_length: DEFAULT_MAX_LENGTH,
            truncation_strategy: TruncationStrategy::LongestFirst,
            padding_strategy: PaddingStrategy::DoNotPad,
            pad_to_multiple_of: None,
            add_special_tokens: true,
            do_lower_case: true,
            strip_accents: true,
            clean_text: true,
            tokenize_chinese_chars: true,
            strip_whitespace: true,
            unicode_normalization_form: UnicodeNormForm::NFC,
            return_token_type_ids: false,
            return_attention_mask: true,
            return_special_tokens_mask: false,
            return_offsets: false,
            return_tokens: false,
            special_tokens: SpecialTokens::default(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Vocabulary {
    token_to_id: HashMap<String, TokenId>,
    id_to_token: HashMap<TokenId, String>,
    vocab_size: usize,
}

impl Vocabulary {
    pub fn new(vocab: HashMap<String, TokenId>) -> Self {
        let id_to_token: HashMap<TokenId, String> =
            vocab.iter().map(|(k, &v)| (v, k.clone())).collect();
        let vocab_size = vocab.len();
        Self {
            token_to_id: vocab,
            id_to_token,
            vocab_size,
        }
    }

    pub fn from_list(tokens: Vec<String>) -> Self {
        let token_to_id: HashMap<String, TokenId> = tokens
            .into_iter()
            .enumerate()
            .map(|(i, t)| (t, i as TokenId))
            .collect();
        let id_to_token: HashMap<TokenId, String> =
            token_to_id.iter().map(|(k, &v)| (v, k.clone())).collect();
        let vocab_size = token_to_id.len();
        Self {
            token_to_id,
            id_to_token,
            vocab_size,
        }
    }

    pub fn get_id(&self, token: &str) -> Option<TokenId> {
        self.token_to_id.get(token).copied()
    }

    pub fn get_token(&self, id: TokenId) -> Option<&str> {
        self.id_to_token.get(&id).map(|s| s.as_str())
    }

    pub fn contains(&self, token: &str) -> bool {
        self.token_to_id.contains_key(token)
    }

    pub fn size(&self) -> usize {
        self.vocab_size
    }
}

pub struct WordPieceTokenizer {
    vocab: Arc<Vocabulary>,
    config: TokenizerConfig,
    unk_id: TokenId,
    pad_id: TokenId,
    cls_id: TokenId,
    sep_id: TokenId,
}

impl WordPieceTokenizer {
    pub fn new(vocab: Vocabulary, config: TokenizerConfig) -> EngineResult<Self> {
        let unk_id = vocab
            .get_id(&config.special_tokens.unk_token)
            .ok_or_else(|| EngineError::TokenizationError(format!(
                "UNK token '{}' not found in vocabulary",
                config.special_tokens.unk_token
            )))?;

        let pad_id = vocab
            .get_id(&config.special_tokens.pad_token)
            .ok_or_else(|| EngineError::TokenizationError(format!(
                "PAD token '{}' not found in vocabulary",
                config.special_tokens.pad_token
            )))?;

        let cls_id = vocab
            .get_id(&config.special_tokens.cls_token)
            .ok_or_else(|| EngineError::TokenizationError(format!(
                "CLS token '{}' not found in vocabulary",
                config.special_tokens.cls_token
            )))?;

        let sep_id = vocab
            .get_id(&config.special_tokens.sep_token)
            .ok_or_else(|| EngineError::TokenizationError(format!(
                "SEP token '{}' not found in vocabulary",
                config.special_tokens.sep_token
            )))?;

        Ok(Self {
            vocab: Arc::new(vocab),
            config,
            unk_id,
            pad_id,
            cls_id,
            sep_id,
        })
    }

    pub fn encode(&self, text: &str) -> EngineResult<TokenizerOutput> {
        let processed = self.preprocess(text);
        let words = self.basic_tokenize(&processed);
        let mut all_token_ids: Vec<TokenId> = Vec::new();
        let mut all_tokens: Vec<String> = Vec::new();
        let mut all_offsets: Vec<(usize, usize)> = Vec::new();
        let mut special_tokens_mask: Vec<u8> = Vec::new();

        if self.config.add_special_tokens {
            all_token_ids.push(self.cls_id);
            if self.config.return_tokens {
                all_tokens.push(self.config.special_tokens.cls_token.clone());
            }
            if self.config.return_offsets {
                all_offsets.push((0, 0));
            }
            special_tokens_mask.push(1);
        }

        for word in &words {
            let wp_tokens = self.wordpiece_tokenize(word);
            for token in wp_tokens {
                let id = self.vocab.get_id(&token).unwrap_or(self.unk_id);
                all_token_ids.push(id);
                if self.config.return_tokens {
                    all_tokens.push(token);
                }
                special_tokens_mask.push(0);
            }
        }

        if self.config.add_special_tokens {
            all_token_ids.push(self.sep_id);
            if self.config.return_tokens {
                all_tokens.push(self.config.special_tokens.sep_token.clone());
            }
            if self.config.return_offsets {
                all_offsets.push((0, 0));
            }
            special_tokens_mask.push(1);
        }

        let was_truncated = all_token_ids.len() > self.config.max_length;
        if all_token_ids.len() > self.config.max_length {
            match self.config.truncation_strategy {
                TruncationStrategy::DoNotTruncate => {}
                _ => {
                    let keep = self.config.max_length;
                    if self.config.add_special_tokens && keep >= 2 {
                        let sep = all_token_ids[all_token_ids.len() - 1];
                        all_token_ids.truncate(keep - 1);
                        all_token_ids.push(sep);
                        special_tokens_mask.truncate(keep - 1);
                        special_tokens_mask.push(1);
                        if self.config.return_tokens && !all_tokens.is_empty() {
                            let sep_tok = all_tokens[all_tokens.len() - 1].clone();
                            all_tokens.truncate(keep - 1);
                            all_tokens.push(sep_tok);
                        }
                    } else {
                        all_token_ids.truncate(keep);
                        special_tokens_mask.truncate(keep);
                        if self.config.return_tokens {
                            all_tokens.truncate(keep);
                        }
                    }
                }
            }
        }

        let num_tokens = all_token_ids.len();
        let target_length = self.compute_padded_length(num_tokens);

        let mut attention_mask: Vec<u8> = vec![1; num_tokens];

        if target_length > num_tokens {
            let pad_count = target_length - num_tokens;
            all_token_ids.extend(vec![self.pad_id; pad_count]);
            attention_mask.extend(vec![0u8; pad_count]);
            if self.config.return_tokens {
                all_tokens.extend(
                    vec![self.config.special_tokens.pad_token.clone(); pad_count],
                );
            }
            special_tokens_mask.extend(vec![1u8; pad_count]);
        }

        Ok(TokenizerOutput {
            input_ids: all_token_ids,
            attention_mask,
            token_type_ids: if self.config.return_token_type_ids {
                Some(vec![0u8; num_tokens.max(1)])
            } else {
                None
            },
            special_tokens_mask: if self.config.return_special_tokens_mask {
                Some(special_tokens_mask)
            } else {
                None
            },
            offsets: if self.config.return_offsets && !all_offsets.is_empty() {
                Some(all_offsets)
            } else {
                None
            },
            tokens: if self.config.return_tokens {
                Some(all_tokens)
            } else {
                None
            },
            num_tokens,
            was_truncated,
        })
    }

    pub fn encode_batch(&self, texts: &[String]) -> EngineResult<BatchTokenizerOutput> {
        let outputs: EngineResult<Vec<TokenizerOutput>> =
            texts.par_iter().map(|t| self.encode(t)).collect();
        let outputs = outputs?;

        let max_len = match self.config.padding_strategy {
            PaddingStrategy::MaxLength => self.config.max_length,
            PaddingStrategy::Longest => outputs.iter().map(|o| o.num_tokens).max().unwrap_or(0),
            PaddingStrategy::DoNotPad => 0,
        };

        let mut all_input_ids = Vec::with_capacity(outputs.len());
        let mut all_attention_masks = Vec::with_capacity(outputs.len());
        let mut all_num_tokens = Vec::with_capacity(outputs.len());
        let mut all_was_truncated = Vec::with_capacity(outputs.len());
        let mut has_token_type_ids = false;
        let mut all_token_type_ids: Vec<Vec<u8>> = Vec::new();

        for output in outputs {
            let n = output.input_ids.len();
            all_num_tokens.push(n);
            all_was_truncated.push(output.was_truncated);

            let mut ids = output.input_ids;
            let mut mask = output.attention_mask;

            if max_len > n {
                let pad_count = max_len - n;
                ids.extend(vec![self.pad_id; pad_count]);
                mask.extend(vec![0u8; pad_count]);
            }

            all_input_ids.push(ids);
            all_attention_masks.push(mask);

            if let Some(tti) = output.token_type_ids {
                has_token_type_ids = true;
                let mut padded = tti;
                if max_len > n {
                    padded.extend(vec![0u8; max_len - n]);
                }
                all_token_type_ids.push(padded);
            }
        }

        Ok(BatchTokenizerOutput {
            input_ids: all_input_ids,
            attention_mask: all_attention_masks,
            token_type_ids: if has_token_type_ids {
                Some(all_token_type_ids)
            } else {
                None
            },
            num_tokens: all_num_tokens,
            was_truncated: all_was_truncated,
        })
    }

    pub fn decode(&self, ids: &[TokenId], skip_special_tokens: bool) -> String {
        let tokens: Vec<&str> = ids
            .iter()
            .filter_map(|&id| {
                let token = self.vocab.get_token(id)?;
                if skip_special_tokens && self.is_special_token(token) {
                    return None;
                }
                Some(token)
            })
            .collect();
        self.join_tokens(&tokens)
    }

    pub fn count_tokens(&self, text: &str) -> usize {
        let processed = self.preprocess(text);
        let words = self.basic_tokenize(&processed);
        let base_count: usize = words.iter().map(|w| self.wordpiece_tokenize(w).len()).sum();
        if self.config.add_special_tokens {
            base_count + 2
        } else {
            base_count
        }
    }

    pub fn truncate_to_token_limit(&self, text: &str, max_tokens: usize) -> String {
        let effective_max = if self.config.add_special_tokens && max_tokens >= 2 {
            max_tokens - 2
        } else {
            max_tokens
        };

        let words = self.basic_tokenize(&self.preprocess(text));
        let mut total_tokens = 0;
        let mut kept_words: Vec<&str> = Vec::new();

        for word in &words {
            let word_tokens = self.wordpiece_tokenize(word).len();
            if total_tokens + word_tokens > effective_max {
                break;
            }
            total_tokens += word_tokens;
            kept_words.push(word);
        }

        kept_words.join(" ")
    }

    pub fn vocab_size(&self) -> usize {
        self.vocab.size()
    }

    fn preprocess(&self, text: &str) -> String {
        let mut s = text.to_string();

        if self.config.clean_text {
            s = s
                .chars()
                .filter(|c| !c.is_control() || *c == '\n' || *c == '\t')
                .collect();
        }

        s = match self.config.unicode_normalization_form {
            UnicodeNormForm::NFC => s.nfc().collect(),
            UnicodeNormForm::NFD => s.nfd().collect(),
            UnicodeNormForm::NFKC => s.nfkc().collect(),
            UnicodeNormForm::NFKD => s.nfkd().collect(),
            UnicodeNormForm::None => s,
        };

        if self.config.do_lower_case {
            s = s.to_lowercase();
        }

        if self.config.strip_whitespace {
            s = s.split_whitespace().collect::<Vec<&str>>().join(" ");
        }

        s
    }

    fn basic_tokenize<'a>(&self, text: &'a str) -> Vec<String> {
        let mut tokens = Vec::new();

        for word in text.unicode_words() {
            if self.config.tokenize_chinese_chars {
                let mut current = String::new();
                for ch in word.chars() {
                    if is_chinese_char(ch) {
                        if !current.is_empty() {
                            tokens.push(current.trim().to_string());
                            current = String::new();
                        }
                        tokens.push(ch.to_string());
                    } else {
                        current.push(ch);
                    }
                }
                if !current.is_empty() {
                    tokens.push(current.trim().to_string());
                }
            } else {
                tokens.push(word.to_string());
            }
        }

        tokens.into_iter().filter(|t| !t.is_empty()).collect()
    }

    fn wordpiece_tokenize(&self, word: &str) -> Vec<String> {
        if word.len() > 200 {
            return vec![self.config.special_tokens.unk_token.clone()];
        }

        let chars: Vec<char> = word.chars().collect();
        let mut output_tokens: Vec<String> = Vec::new();
        let mut start = 0;

        while start < chars.len() {
            let mut end = chars.len();
            let mut found = false;
            let is_first = start == 0;

            while start < end {
                let substr: String = chars[start..end].iter().collect();
                let candidate = if is_first {
                    substr.clone()
                } else {
                    format!("{}{}", BPE_CONTINUATION, substr)
                };

                if self.vocab.contains(&candidate) {
                    output_tokens.push(candidate);
                    found = true;
                    break;
                }

                end -= 1;
            }

            if !found {
                output_tokens.push(self.config.special_tokens.unk_token.clone());
                break;
            }

            start = end;
        }

        output_tokens
    }

    fn join_tokens(&self, tokens: &[&str]) -> String {
        let mut result = String::new();
        for token in tokens {
            if token.starts_with(BPE_CONTINUATION) {
                result.push_str(&token[BPE_CONTINUATION.len()..]);
            } else {
                if !result.is_empty() {
                    result.push(' ');
                }
                result.push_str(token);
            }
        }
        result
    }

    fn is_special_token(&self, token: &str) -> bool {
        token == self.config.special_tokens.unk_token
            || token == self.config.special_tokens.pad_token
            || token == self.config.special_tokens.cls_token
            || token == self.config.special_tokens.sep_token
            || token == self.config.special_tokens.mask_token
            || self.config.special_tokens.additional_special_tokens.contains(&token.to_string())
    }

    fn compute_padded_length(&self, current: usize) -> usize {
        match self.config.padding_strategy {
            PaddingStrategy::MaxLength => {
                let target = self.config.max_length;
                if let Some(multiple) = self.config.pad_to_multiple_of {
                    let remainder = target % multiple;
                    if remainder == 0 {
                        target
                    } else {
                        target + multiple - remainder
                    }
                } else {
                    target
                }
            }
            PaddingStrategy::Longest | PaddingStrategy::DoNotPad => current,
        }
    }
}

pub struct WhitespaceTokenizer {
    config: TokenizerConfig,
}

impl WhitespaceTokenizer {
    pub fn new(config: TokenizerConfig) -> Self {
        Self { config }
    }

    pub fn encode(&self, text: &str) -> EngineResult<TokenizerOutput> {
        let tokens: Vec<String> = if self.config.do_lower_case {
            text.split_whitespace()
                .map(|t| t.to_lowercase())
                .collect()
        } else {
            text.split_whitespace().map(|t| t.to_string()).collect()
        };

        let mut ids: Vec<TokenId> = tokens.iter().enumerate().map(|(i, _)| i as TokenId).collect();
        let was_truncated = ids.len() > self.config.max_length;
        ids.truncate(self.config.max_length);
        let num_tokens = ids.len();
        let attention_mask = vec![1u8; num_tokens];

        Ok(TokenizerOutput {
            input_ids: ids,
            attention_mask,
            token_type_ids: None,
            special_tokens_mask: None,
            offsets: None,
            tokens: if self.config.return_tokens {
                Some(tokens[..num_tokens].to_vec())
            } else {
                None
            },
            num_tokens,
            was_truncated,
        })
    }

    pub fn count_tokens(&self, text: &str) -> usize {
        text.split_whitespace().count().min(self.config.max_length)
    }
}

pub fn count_tokens_approximate(text: &str) -> usize {
    let char_count = text.chars().count();
    let word_count = text.split_whitespace().count();
    let chinese_count = text.chars().filter(|&c| is_chinese_char(c)).count();
    word_count + chinese_count + (char_count / 4).saturating_sub(word_count)
}

pub fn fits_in_context(text: &str, max_tokens: usize, tokenizer_overhead: usize) -> bool {
    count_tokens_approximate(text) + tokenizer_overhead <= max_tokens
}

pub fn batch_count_tokens_approximate(texts: &[String]) -> Vec<usize> {
    texts
        .par_iter()
        .map(|t| count_tokens_approximate(t))
        .collect()
}

fn is_chinese_char(c: char) -> bool {
    let cp = c as u32;
    (0x4E00..=0x9FFF).contains(&cp)
        || (0x3400..=0x4DBF).contains(&cp)
        || (0x20000..=0x2A6DF).contains(&cp)
        || (0x2A700..=0x2B73F).contains(&cp)
        || (0x2B740..=0x2B81F).contains(&cp)
        || (0x2B820..=0x2CEAF).contains(&cp)
        || (0xF900..=0xFAFF).contains(&cp)
        || (0x2F800..=0x2FA1F).contains(&cp)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn build_test_vocab() -> Vocabulary {
        let mut vocab: HashMap<String, TokenId> = HashMap::new();
        vocab.insert("[PAD]".to_string(), 0);
        vocab.insert("[UNK]".to_string(), 1);
        vocab.insert("[CLS]".to_string(), 2);
        vocab.insert("[SEP]".to_string(), 3);
        vocab.insert("[MASK]".to_string(), 4);
        for (i, word) in ["hello", "world", "test", "token", "##ing", "##ed", "neural", "core"]
            .iter()
            .enumerate()
        {
            vocab.insert(word.to_string(), (i + 5) as TokenId);
        }
        Vocabulary::new(vocab)
    }

    fn build_test_tokenizer() -> WordPieceTokenizer {
        WordPieceTokenizer::new(build_test_vocab(), TokenizerConfig::default()).unwrap()
    }

    #[test]
    fn test_encode_produces_cls_and_sep() {
        let tokenizer = build_test_tokenizer();
        let output = tokenizer.encode("hello world").unwrap();
        assert_eq!(output.input_ids[0], 2);
        assert_eq!(*output.input_ids.last().unwrap(), 3);
    }

    #[test]
    fn test_encode_empty_string() {
        let tokenizer = build_test_tokenizer();
        let output = tokenizer.encode("").unwrap();
        assert_eq!(output.num_tokens, 2);
        assert_eq!(output.input_ids[0], 2);
        assert_eq!(output.input_ids[1], 3);
    }

    #[test]
    fn test_truncation_respects_max_length() {
        let config = TokenizerConfig {
            max_length: 5,
            ..Default::default()
        };
        let tokenizer = WordPieceTokenizer::new(build_test_vocab(), config).unwrap();
        let text = "hello world test token neural core";
        let output = tokenizer.encode(text).unwrap();
        assert!(output.input_ids.len() <= 5);
        assert!(output.was_truncated);
    }

    #[test]
    fn test_attention_mask_all_ones_no_padding() {
        let tokenizer = build_test_tokenizer();
        let output = tokenizer.encode("hello").unwrap();
        assert!(output.attention_mask.iter().all(|&m| m == 1));
    }

    #[test]
    fn test_whitespace_tokenizer_count() {
        let count = WhitespaceTokenizer::new(TokenizerConfig::default())
            .count_tokens("hello world foo bar");
        assert_eq!(count, 4);
    }

    #[test]
    fn test_approximate_count_reasonable() {
        let text = "This is a simple test sentence for token counting.";
        let count = count_tokens_approximate(text);
        assert!(count >= 5 && count <= 20);
    }

    #[test]
    fn test_decode_round_trip() {
        let tokenizer = build_test_tokenizer();
        let output = tokenizer.encode("hello world").unwrap();
        let decoded = tokenizer.decode(&output.input_ids, true);
        assert!(decoded.contains("hello"));
    }

    #[test]
    fn test_batch_encode_consistent_lengths_with_padding() {
        let config = TokenizerConfig {
            padding_strategy: PaddingStrategy::MaxLength,
            max_length: 16,
            ..Default::default()
        };
        let tokenizer = WordPieceTokenizer::new(build_test_vocab(), config).unwrap();
        let texts = vec!["hello".to_string(), "hello world test".to_string()];
        let batch = tokenizer.encode_batch(&texts).unwrap();
        assert_eq!(batch.input_ids[0].len(), batch.input_ids[1].len());
    }
}