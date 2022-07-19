https://damueller.com/#/blog-post/NNLLs
- Why NN's find generalizable solutions?
  - gradient descent can traverse a complex or simple loss landscape with
fewer local minima
  - can't look at all possible weight settings must use GD
  - skip, residual connections, higher overparameterization, result in
smoother loss landscapes
![local minima]("./im1.png")
  - NN pref data that is generalizable over random
- GD Alg ( SGD stochastic gradient descent (into madness))
  - start @ rand point, move down gradient ideally reducing error
  - saddle points are a problem: https://arxiv.org/pdf/1406.2572.pdf
  - gradient descent doesn't often encounter local minima with modern NN
    - can usually find a global minimizer
  - GD can be used as universal func approximator
    - can memorize entire dataset
- "There is no guarantee that this solution would actually generalize to
data outside of the training data!"
  - you

## Wide Basins and Implicit Regularization
- wide basins are easier to generalize than narrow basin
  - generalizable NN pref flatter basins
  - less noise in a flatter basin
- what is a basin? (basin of attraction)
  - set of initial points that converge to some attracting set
  - several points that converge together as the system evolves through time

__left off at Why might SGD prefer basins that are flatter?_

## Intrinsic Dimensionality
## Mode Connectivity and Basins
## The 2 Phases of Training & Dynamics of SGD

## To Explore
- Stochastic Differential Equation (SDE)
