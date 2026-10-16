# Jev Function Quality Scorer

This command turns Jev's `function-review.yaml` into human-readable, machine-parsable YAML containing basic and call-depth-weighted scores at function, file, module, and overall levels. Every level also includes scores for each review category.

## Run

```bash
python score_reviews.py path/to/function-review.yaml --output scores.yaml
```

The default passing threshold is `0.85`. Override it with:

```bash
python score_reviews.py path/to/function-review.yaml --threshold 0.9 --output scores.yaml
```

The review's `source.input_file` identifies the parsed function metadata JSON used for call depth. Use `--metadata path/to/parsed.json` to override it.

## Scoring

- A positive criterion passes when `probability_yes >= threshold`.
- A negative criterion passes when `probability_no >= threshold`.
- A basic score is `passed criteria / evaluated criteria`.
- A function's weight is `depth_to_leaf + 1`, so leaf functions weigh 1 and progressively higher callers weigh more.
- A weighted aggregate is the weighted average of its function scores.
- A module is a reviewed file's parent directory; `.` represents files in the repository root.

The generated YAML records these rules, source paths, counts, weights, category scores, and each criterion's pass/fail decision.
