# sphinx-spice

**An spice_file and spice_simulation extension for Sphinx**.

This package contains a [Sphinx](http://www.sphinx-doc.org/en/master/) extension
for producing `spice_file` and `spice_simulation` directives.


## Get started

To get started with `sphinx-spice`, first install it through `pip`:

```
pip install git+https://github.com/jangenoe/sphinx-spice.git
```

then, add `sphinx_spice` to your sphinx `extensions` in the `conf.py`

```python
...
extensions = ["sphinx_spice"]
...
```


we provided a gated directive syntax for `spice_file` and `spice_simulation` directives, which provides
an alternative syntax for building `spice_file` and `spice_simulation` that may also include
executable code.

**Example:**

You may now use `spice_file-start` and `spice_file-end` to define the spice_file which may
include any type of text, directives and roles between the start and end markers.

````md
```{spice_file-start} Basic class E circuit
:label: ex1
```

```{code-cell}
# Some setup code that needs executing
```

and maybe you wish to add a figure

```{figure} img/example.png
```

```{spice_file-end}
```
````

The same holds for the simulation

````md
```{spice_simulation-start} Simulation of 1 period
:label: ex2
```

```{code-cell}
# Some setup code that needs executing
```

and maybe you wish to add a figure

```{figure} img/example.png
```

```{spice_simulation-end}
```
````
