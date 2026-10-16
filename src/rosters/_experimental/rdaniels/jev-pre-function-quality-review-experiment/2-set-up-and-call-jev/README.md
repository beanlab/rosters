# Jev function review MVP

This CLI reads the parsed function index, asks Jev every question in `code-checks.yaml` for
each function, and writes a readable YAML report. Each question is a Noul, so every recorded
answer is the probability that the answer is **yes**.

## Setup

Use Python 3.10 or newer and install the project dependencies:

```bash
python -m pip install -e .
export TYPESAFE_API_KEY="your-key"
```

## Estimate before calling Jev

The default input is the preceding pipeline stage's
`results/1-parse-repo/parsed.json`. This command only calculates and displays the estimate:

```bash
python review_functions.py --estimate-only
```

The estimate uses a deliberately simple heuristic: UTF-8 bytes divided by four, plus 200
tokens of request overhead. The default assumed price is `$0.042` per million input tokens.
Both values can be changed with CLI options.

## Run the review

```bash
python review_functions.py
```

The program always displays the estimate before any Jev call and asks for confirmation. For
an already-approved non-interactive run, pass `--yes`. It refuses non-interactive execution
without that explicit flag.

The default output is `results/2-set-up-and-call-jev/function-review.yaml`. It records:

- the exact grouped checks and each check's positive/negative polarity;
- every function's Noul probability for every question;
- the requested and resolved model versions;
- per-function and total token usage;
- estimated and actual cost; and
- start time, completion time, and elapsed duration.

Run `python review_functions.py --help` to override input, output, checks, model, or pricing.

## Edit checks

Edit `code-checks.yaml`. A `positive` question means **yes is favorable**; a `negative`
question means **yes is unfavorable**. Question IDs must be unique because downstream code
uses them as stable response keys.
