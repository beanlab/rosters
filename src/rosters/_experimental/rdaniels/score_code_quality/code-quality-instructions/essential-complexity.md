# Essential Complexity

Essential complexity measures how much unstructured control flow remains after
all well-structured sequences, selections, and loops in a control-flow graph
are collapsed. In McCabe's formulation, a value of 1 describes fully structured
control flow; higher values indicate irreducible flow, such as branches that
jump into or out of regions with multiple entry or exit points.

This metric requires a control-flow analyzer and is mainly useful for languages
that permit constructs such as `goto`. Do not substitute cyclomatic complexity,
cognitive complexity, or visual inspection for an essential-complexity value.
For structured languages such as Python, the metric is commonly 1 and often
provides little discrimination. When it is available, use it to locate
unstructured flow, then judge whether refactoring to structured constructs
would make behavior safer and clearer.

## Good example

```text
read request
if request is valid:
    process request
else:
    report validation error
record completion
```

Each region has a clear entry and exit and can be reduced to a standard
sequence or selection.

## Bad example

```text
start:
read request
if request is missing: goto finish
if request is cached: goto process
validate request
process:
process request
if retry is required: goto start
finish:
record completion
```

Jumps enter and leave control-flow regions at several points, so the graph
cannot be reduced cleanly to structured decisions and loops.
