# Code quality atlas

Generate one self-contained, interactive HTML report from one or more `scores.yaml` files. The resulting file has no external assets or server dependency, so it can be opened locally or shared as-is.

When the report contains multiple timestamped pipeline snapshots, its **Score over time** page plots the overall basic and weighted scores from oldest to newest. The exact values are also listed in a table, and selecting a snapshot opens its detailed quality map.

## Setup

```bash
python -m pip install -r requirements.txt
```

## Generate a report

```bash
python generate_report.py /path/to/scores.yaml -o quality-report.html
```

Pass multiple files to compare projects. Prefix any path with `NAME=` to control its display name:

```bash
python generate_report.py \
  "Parser=/results/parser/scores.yaml" \
  "Indexer=/results/indexer/scores.yaml" \
  --title "Repository quality review" \
  -o quality-report.html
```

Open `quality-report.html` in any modern browser. Select a project by its overall score, switch between basic and weighted aggregation, choose any scoring category, and toggle the map between directories, files, and functions. Selecting a map tile or ranked hotspot reveals its category scores. The inspector drills down to individual criterion results and provides clickable breadcrumbs back through the containing file and directory.

The top-level pipeline runner writes a combined report containing every requested iteration to `<output-dir>/quality-report.html`. It also keeps the individual snapshot reports in their timestamped directories.

When a score file references parser metadata through `source.function_metadata_file`, each function's source is embedded in the report and displayed with its original line numbers. Because the source is copied into the generated HTML, recipients do not need access to the reviewed repository or metadata file.

## Design notes

- Categories and criteria are discovered from the input instead of being hard-coded.
- Validation and normalization live in `quality_report/model.py`; HTML serialization lives in `quality_report/generator.py`; interaction and presentation live in `quality_report/report.html`.
- The treemap area reflects the number of evaluated criteria, while color reflects the selected score. Ranking and median comparisons use that same selected metric.

## Test

```bash
python -m unittest discover -s tests -v
```
