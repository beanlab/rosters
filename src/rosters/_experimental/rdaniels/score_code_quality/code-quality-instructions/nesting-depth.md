# Nesting Depth

Nesting depth is the greatest number of control-flow or lexical blocks that
enclose a statement. Depending on the analyzer, functions, classes, conditionals,
loops, exception handlers, and context managers may count as nesting levels.
Deep nesting increases the amount of context a reader must retain and makes
individual paths harder to identify.

Judge the deepest meaningful path in each function, not indentation caused only
by formatting. Prefer guard clauses, early exits, and small named helpers when
they clarify the flow. Some nesting is natural, so treat depth as a warning to
inspect the code rather than proof of poor quality. State the counting rules
when reporting a number.

## Good example

```python
def send_receipt(order: Order) -> bool:
    if not order.is_paid:
        return False
    if order.customer.email is None:
        return False

    email_receipt(order.customer.email, order)
    return True
```

No operation is buried beneath multiple decisions, and failed preconditions are
visible immediately.

## Bad example

```python
def send_receipt(order: Order) -> bool:
    if order.is_paid:
        if order.customer.email is not None:
            if order.items:
                for item in order.items:
                    if item.is_refundable:
                        email_receipt(order.customer.email, order)
                        return True
    return False
```

The important action is five blocks deep, and its actual preconditions are hard
to distinguish from incidental iteration.
