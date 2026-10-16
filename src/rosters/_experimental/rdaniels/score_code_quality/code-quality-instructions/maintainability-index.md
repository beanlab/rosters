# Maintainability Index

The Maintainability Index (MI) combines several measurements into one score,
usually Halstead volume, cyclomatic complexity, and lines of code. Some variants
also include comment density or normalize the result to a 0–100 scale. A higher
score conventionally indicates code that may be easier to maintain.

MI is a broad screening and trend metric, not a direct design judgment. Record
the analyzer, formula, version, scope, and exclusions, and compare only results
produced under the same conditions. Use a low or falling score to select code
for inspection; do not infer the cause or recommend a change from MI alone.
Generated code, comments, language differences, and splitting code into smaller
files can change the score without improving the design.

## Good example

```python
def final_price(price: Decimal, discount: Decimal) -> Decimal:
    discounted_price = price * (Decimal("1") - discount)
    return max(discounted_price, Decimal("0"))
```

This small function has low control-flow complexity and modest operator and
operand counts, so it would generally contribute to a stronger MI result. Its
clear responsibility also supports the metric's suggestion.

## Bad example

```python
def final_price(order: Order, customer: Customer, now: datetime) -> Decimal:
    total = sum(item.price * item.quantity for item in order.items)
    if customer.is_member:
        if now.weekday() < 5:
            total *= Decimal("0.90")
        elif total > Decimal("100"):
            total *= Decimal("0.85")
    else:
        if len(order.items) > 10:
            total -= Decimal("5")
    if order.coupon and not order.coupon.is_expired(now):
        if order.coupon.kind == "percent":
            total *= Decimal("1") - order.coupon.value
        else:
            total -= order.coupon.value
    return max(total, Decimal("0"))
```

The larger size, greater control-flow complexity, and larger vocabulary would
generally lower MI. Direct inspection also reveals several pricing policies
combined in one function, which explains why the metric merits attention.
