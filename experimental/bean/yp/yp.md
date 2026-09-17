---
type: skill
description: How to write and execute source in the Yp programming language. Yp is a transform of Python that allows for body-first function definitions. Yp files end in `.yp`.
---

# Yp - a body-first transform of Python

**Motivation** - Yp allows the author to write code where *usage* occurs **before** *definition*. 

## Syntax

The syntax of Yp is identical to Python except in the definition of functions, where the arguments to the function now follow the function body:

```yp
def greet:
    print(name)
needs (name: str)
```

The expression following the `needs` keyword is transposed directly following the function name, creating valid Python:

```python
def greet(name: str):
    print(name)
```

The `needs` keyword must match the indentation of the `def` keyword.

That is the only difference between Yp and Python. 

## Execution

You can invoke Yp source with:

```shell
yp file.yp
```

You can compile Yp to Python with:

```shell
yp --compile file.yp -o file.py
```
