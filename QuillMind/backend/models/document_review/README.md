# Document review ONNX models

Store each deployable model in a versioned directory:

```text
document_review/
└── v1.0.0/
    ├── model.onnx
    ├── labels.json
    ├── tokenizer.json
    ├── tokenizer_config.json
    └── special_tokens_map.json
```

The ONNX model should expose tokenizer-compatible inputs such as `input_ids`,
`attention_mask`, and optionally `token_type_ids`. Its first output must be token
classification logits shaped `[batch, sequence, labels]`.

`labels.json` may be a list:

```json
["O", "B-表述歧义:high", "I-表述歧义:high"]
```

or an ID-keyed object. Labels support BIO prefixes and optional
`low`/`medium`/`high` levels separated by `:` or `|`. A structured label value
may also provide `tag`, `type`, and `level`.

Set `DOCUMENT_REVIEW_MODEL_VERSION` to switch the default version. Individual
calls may pass `model_version` for blue-green routing. If a requested model is
not installed, `DocumentReviewer` uses the LLM baseline.
