
<p align="center">
  <img src="https://github.com/cacodcar/gana/raw/main/docs/_static/ganalogo.jpg" width="75%">
</p>


[![Documentation Status](https://readthedocs.org/projects/gana/badge/)](https://gana.readthedocs.io/en/latest/)
[![PyPI](https://img.shields.io/pypi/v/gana.svg)](https://pypi.org/project/gana)
[![Downloads](https://static.pepy.tech/personalized-badge/gana?period=total&units=international_system&left_color=grey&right_color=orange&left_text=Downloads)](https://pepy.tech/project/gana)
[![Python package](https://github.com/cacodcar/gana/actions/workflows/python-package.yml/badge.svg)](https://github.com/cacodcar/gana/actions/workflows/python-package.yml)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gana.svg)](https://pypi.org/project/gana/)

Gana is an Algebraic Modeling Language (AML) for Multiscale Modeling and Optimization. 
Generated programs (```Prg```) can be subclasses of Multiparametric Mixed Integer Linear Programming (mpMILP). 

# Installation

The current development checkout requires the Rust extension, `gana._native`.
The Python modeling API is unchanged. Use Python 3.12 or 3.13 for the candidate
validation matrix; other versions and wheel platforms are not yet verified.

Install an available release and its dependencies in a fresh environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install gana
```

On Windows, use `.venv\Scripts\python` instead. Published releases may predate
the backend retirement described here. A compatible wheel includes the native
extension and needs no Rust compiler at runtime. A source installation, including
this checkout, needs Rust/Cargo 1.88 or newer and a platform linker; validation
uses Rust 1.88.0:

```sh
.venv/bin/python -m pip install .
```

Leave `GANA_BACKEND` unset. The old `rust-parameters` value is accepted as an
alias; `python` and unknown values are rejected. A missing extension produces
installation guidance instead of selecting a Python backend. See the
[installation guide](https://gana.readthedocs.io/en/latest/tutorials/installation.html)
and [native implementation notes](https://gana.readthedocs.io/en/latest/NATIVE_BACKEND.html).

# Features 

Gana supports:

- mutable elements, allowing constraints/functions to be updated dynamically
- multiparametric as well as mixed integer programming
- formulation in both matrix form and set-based mathematical program 

Moreover, Gana uses a simple format to write constraints/functions. 

# Elements

Programs in Gana are written using element sets, namely:

1. ```I``` - index 
2. ```V``` - variable
3. ```P``` - parameter 
4. ```T``` - parametric variable
 

# Solvers

The list of natively supported solvers are:

1. [PPOPT](https://github.com/TAMUparametric/PPOPT) for multiparametric programming (mp)
2. [Gurobi](https://www.gurobi.com/) for Mixed Integer Programming (MIP)
Programs  can, however, be exported as a [.mps](https://www.ibm.com/docs/en/icos/22.1.2?topic=formats-working-mps-files) or [.lp](https://www.ibm.com/docs/en/icos/22.1.2?topic=formats-working-lp-files) file and passed to most solvers.


# Illustration

Gana is best run in [Jupyter](https://jupyter.org/) as notebook (.ipynb) files, 
where programs can be visualized as canonical mathematical programs using set-notation.

Additionally, matrices can be exported. 

# Purpose

Gana was developed to enable certain functionalities in [energia (py)](https://energiapy.readthedocs.io/en/latest/). Both were developed as PhD projects and have ample room for improvement. So please reach out to me on cacodcar@gmail.com with suggestions and such. 

<!-- 
or 

Matrices can be generated to represent: 

LHS Parameter coefficient of variables in constraints: 
    1. A - all
    2. G - inequality 
    3. H - equality
    4. NN - nonnegativity

RHS parameters in constraints:
    1. B 

RHS Parameter coefficient of parametric variables in constraints:
    1. F 

Bounds of the parametric variables:
    1. CRa - RHS coefficients
    2. CRb - Bound (upper or lower) -->





