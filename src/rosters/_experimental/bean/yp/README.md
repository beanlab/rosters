# YP

YP transforms body-first function definitions into ordinary Python.

```yp
def greet:
    print(f"Hello, {name}!")
needs (name)

greet("world")
```

Install the project and execute or compile a source file:

```sh
yp example.yp
yp --compile example.yp
yp --compile example.yp -o example.py
```

The Python API exposes `yp.preprocess(source, filename="<yp>")` and
`yp.run(path)`. Source files are read and written as UTF-8. `run` accepts either
a string path or a `pathlib.Path`.
