
![alt text](https://github.com/cacodcar/gana/blob/main/docs/source/gana-logo.png?raw=true)

[![Documentation Status](https://readthedocs.org/projects/gana/badge/)](https://gana.readthedocs.io/en/latest/)

Gana is an algebraic modeling language (AML) for multiscale modeling and optimization

Modeling in Gana is done using four sets: 

1. I - index 
2. V - variable
3. P - parameter 
4. T - parametric variable
 
The model can be exported as a .mps or .lp file and passed to a solver 

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
    2. CRb - Bound (upper or lower)


Gana was developed to enable certain functionalities in [energia (py)](https://pypi.org/project/energiapy/).

Both were developed through my PhD and as such have a lot of room for improvement.

So please reach out to me on cacodcar@gmail.com with suggestions and such. 



