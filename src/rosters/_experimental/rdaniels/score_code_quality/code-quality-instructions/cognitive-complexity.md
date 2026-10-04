# Cognitive Complexity

Cognitive complexity estimates how difficult a unit of code is for a person to
follow. It increases when control flow branches (`if`, loops, exception
handlers, and similar constructs), when branches are nested, and when normal
linear reading is interrupted. Unlike cyclomatic complexity, it gives extra
weight to nesting because nested decisions require the reader to remember more
context.

Judge cognitive complexity at the function or method level. Prefer focused,
linear control flow, guard clauses, and clearly named helper functions. Do not
penalize a necessary branch merely for existing; penalize control flow that is
harder to understand than the problem requires. If reporting a numeric value,
name the analyzer and version because implementations and thresholds differ.

## Good example

```python
def shipping_cost(order: Order) -> int:
    if order.is_digital:
        return 0
    if order.qualifies_for_free_shipping:
        return 0
    return order.package_count * 500
```

The guard clauses keep each decision independent and leave the main result on a
straight path.

## Bad example

```python
def shipping_cost(order: Order) -> int:
    if not order.is_digital:
        if not order.qualifies_for_free_shipping:
            if order.package_count > 0:
                return order.package_count * 500
            else:
                return 0
        else:
            return 0
    else:
        return 0
```

The same simple policy is expressed through nested decisions and unnecessary
`else` branches, forcing the reader to retain several conditions at once.
