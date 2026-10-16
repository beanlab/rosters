# Python Function Index

`function_index.py` finds every function, async function, nested function, and method in a local Python directory. It writes a JSON file designed to be consumed one function at a time by another program.

## Install and run

```bash
python -m pip install -r requirements.txt
python function_index.py /path/to/repository --output functions.json
```

For a GitHub repository, clone it first and pass the cloned directory. Omit `--output` to print JSON to standard output.

## Analyze repository history

Analyze a local clone repeatedly without changing its current branch or working files:

```bash
python function_index.py /path/to/repository \
  --ref main \
  --interval monthly \
  --count 5 \
  --output-dir results
```

`--interval` accepts:

- `weekly`: current time, then every week backward.
- `monthly`: current time, then every month backward.
- `bimonthly`: current time, then every two months backward.

`--count` controls the number of snapshots, including the current point. Each result filename contains its timestamp and resolved commit. Historical analysis requires Git. If the requested ref is not local, fetch it first. If a shallow clone does not contain enough history, the command reports that it must be unshallowed.

## Output contract (schema 1.1)

The top-level JSON object contains:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | string | Contract version, currently `1.1`. |
| `root` | string | Absolute path of the analyzed directory. |
| `git` | object | Historical analysis metadata; omitted for ordinary directory analysis. |
| `entry_points` | string[] | IDs of functions called by module-level code. |
| `functions` | object[] | Function records, ordered by file and line. |
| `errors` | object[] | Files that could not be read or parsed. |

The historical `git` object contains `ref`, the full resolved `commit` SHA, and the requested `cutoff` timestamp.

Each function record contains:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Unique ID in the form `file.py::qualified.name@line`. |
| `file` | string | POSIX-style path relative to `root`. |
| `name` | string | Function's short name. |
| `qualified_name` | string | Name including enclosing classes/functions. |
| `line`, `end_line` | integer | One-based source span. |
| `signature` | string | Readable function signature. |
| `source` | string | Complete function source text. |
| `calls` | string[] | IDs of directly called functions resolved in the same file. |
| `depth_from_entry` | integer or null | Fewest calls from a module-level entry point; entry points are `0`. `null` means no entry path was found. |
| `depth_to_leaf` | integer | Longest call-graph distance to a function with no resolved outgoing calls. Leaf functions are `0`. Recursive cycles are collapsed before this value is calculated. |

## Deliberate limitations

This simplest version performs static analysis only. It resolves direct calls by name within one file and `self.method()`/`cls.method()` calls. It does not resolve imports, aliases, decorators, dynamic dispatch, or arbitrary attribute calls. Calls it cannot resolve are omitted. Hidden directories, virtual environments, caches, and version-control directories are skipped.
