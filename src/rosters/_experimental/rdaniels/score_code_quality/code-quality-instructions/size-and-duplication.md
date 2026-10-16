# Size and Duplication

Size describes how much code a unit contains, commonly measured with source or
logical lines of code, function and class length, parameter count, module count,
or public API surface. Duplication describes substantially repeated code or
knowledge that must be changed consistently in more than one place.

Judge whether size or repetition increases comprehension, defect, or change
cost; neither is automatically a flaw. A long cohesive algorithm may be easier
to maintain than several fragmented helpers, and two superficially similar
blocks may represent different domain rules. Extract shared code when it
expresses one stable concept, not merely to reduce a line count. Numeric results
should identify the analyzer, scope, and whether generated or vendored files
were excluded.

## Good example

```python
def discounted_total(subtotal: Decimal, discount: Decimal) -> Decimal:
    return subtotal * (Decimal("1") - discount)


retail_total = discounted_total(retail_subtotal, retail_discount)
wholesale_total = discounted_total(wholesale_subtotal, wholesale_discount)
```

The repeated calculation has one name and one implementation, so a rule change
has one place to be made.

## Bad example

```python
retail_total = retail_subtotal - (retail_subtotal * retail_discount)
if retail_total < Decimal("0"):
    retail_total = Decimal("0")

wholesale_total = wholesale_subtotal - (
    wholesale_subtotal * wholesale_discount
)
if wholesale_total < Decimal("0"):
    wholesale_total = Decimal("0")
```

The same multi-step rule is duplicated. A later fix or policy change can easily
be applied to one customer type but missed for the other.
