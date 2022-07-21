 https://damueller.com/#/blog-post/NNLLs
- Why NN's find generalizable solutions?
  - gradient descent can traverse a complex or simple loss landscape with
fewer local minima
  - can't look at all possible weight settings must use GD
  - skip, residual connections, higher overparameterization, result in
smoother loss landscapes
![local minima](./im1.png)
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

### Wide Basins and Implicit Regularization
- wide basins are easier to generalize than narrow basin
  - generalizable NN pref flatter basins
  - less noise in a flatter basin
- what is a basin? (basin of attraction)
  - set of initial points that converge to some attracting set
  - several points that converge together as the system evolves through time
- wider the basin, more like we are to find it during noisey optimization

#### Temperature of SGD
- determines amount of noise present
- flat minima prefered to sharp minima
  - this is why networks do not overfit

### Intrinsic Dimensionality
- often the more parameters, the better we generalize
- you can fix your optimization to a random subspace, move only within that
subspace and still find a good solution
- goldilocks zone, region of particularly high positive curvature within
loss landscape
  - large ratio of positive eigenvalues in their hessians
- __The lottery ticket hypothesis suggests that in any dense, randomly
initialized feed-forward network there exists a subnetwork (the winning
lottery ticket) which can be trained, with all other weights set to 0, and
still achieve comparable accuracy to the original full network__
  - damn

### Mode Connectivity and Basins
- Wormholes
- two independently trained NN can be traverse without incurring a higher
loss than the originals
  - tunnels between local minima

LEFT OFF AT: built upon these findings to propose a large-scale model
### Phases of Training & Dynamics of SGD

### To Explore
- [Stochastic Differential Equation (SDE)](
https://en.wikipedia.org/wiki/Stochastic_differential_equation)
- flat minima, sharp minima
- noise optimization
- [Hessian Matrix](https://en.wikipedia.org/wiki/Hessian_matrix)
- Eigenvalues
### Tags
