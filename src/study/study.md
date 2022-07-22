
# Title
Study
        
# Style
img {
padding: 10px;
margin: 5px;
background-color: {color_accent_light}; 
}

.img_div {
padding: 10px;
margin: 5px;
background-color: {color_accent_light}; 
}
        

.scroll {
font-size: medium; 
line-height: 1.6;
}

# HTML
## study` mo 
### Friday, July 22 2022  
https://www.youtube.com/watch?v=C2w45qRc3aU  

---  

## study`Surface Piercing Propeller 
### Thursday, July 21 2022  
#### Surface piercing props by Paul Kamen  
- https://people.well.com/user/pk/SPAprofboat.html  
- typically waterline passes through hub - is this required?  
- larger prop, more efficiency, momentum theory, low geer ratio  
- cavitation happens pretty easily because 1atm is only 14.7psi  
  - if suction on low pressure side on prop dips below ambient pressure,  
vacuum cavity forms  
  - water vapor cavity  
- sucking in air prevents cavitation damage/water ram effect  
- there is 1 ATM pushing backwards (could be more of Problem for small prop)  
- shaft produces drag  
- adjust prop submergence is like controlling prop pitch  
- can allow for shallow draft  
- prop must not be too close to transom  
- openFOAM CFD  
- Lower vibration  
- reverse can be worse  
- could make a variable pitch prop with a huge hub!  

---  

## study`David Mueller Neural Network Loss Landscape 
### Thursday, July 21 2022  
 https://damueller.com/#/blog-post/NNLLs  
- Why NN's find generalizable solutions?  
  - gradient descent can traverse a complex or simple loss landscape with  
fewer local minima  
  - can't look at all possible weight settings must use GD  
  - skip, residual connections, higher overparameterization, result in  
smoother loss landscapes  
![local minima](https://monksevillair.com/src/study/2022-07-21-study`David-Mueller-Neural-Network-Loss-Landscape/im1.png)  
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

---  

## study` Excellent Piano Practice Technique 
### Thursday, July 21 2022  
 https://www.youtube.com/watch?v=MUvPx-ZaYmA  
- todo, attempt & notate  
- analyze over mindless practicing  
- play in every key  

---  

## Fwd: `study` West System Cold Molded Bo 
### Wednesday, July 20 2022  
### Vicem Yachts - Cold Molding Method  
- https://www.youtube.com/watch?v=6TuXUyweVyE  
- layer veneers at 90degrees  
- Vicem Yachts  
- cnc foam  
- keel made from mahogany  
- keel, cnc battens, stringers super simple mold  
![mold]("./im1.png")  
- transom, stiffeners, chine clamp, spray rail  
- 45deg angle, galvanized nails  
![veneers]("./im2.png")  
- epoxy, stainless staples  
- 10oz eglass on inside and out  
- deck made from thin plywood  
- mirror finish  
  - undercoat, epoxy fairing, longboard and machine sanding, multiple coats  
of epoxy primer and polyurethane paint  
- longboard sanding  
![longboard sanding]("./im3.png")  
  
#### Review  
- still very intricate, could be more computerized  
  
### Boats from trees  
https://www.youtube.com/watch?v=6ZIzJEaIX7U  
- insane sawmill  
 ![insane sawmill]("./im4.png")  
- interesting rigid spiral conveyor  
 ![spiral conveyor]("./im5.png")  
- planers are great  
- laminate several layers of veneer, bend around steel mold  
 ![bending veneers]("./im6.png")  
 ![interesting round shapes]("./im7.png")  
- modern take on traditional boat building  
  - these guys do keyed planks for first layer instead of criss-crosses  
veneers  
- stainless staples, fiberglass, absorbative material, vacuum bag  
 ![stainless staples, fiberglass, absorbative material, vacuum  
bag]("./im8.png")  
- some kinda bondo/clay type juice, plank sanding  
- mark waterline with laser, flipit  
- staple gun is a useful tool  
  
#### Review  
- wood structures are easy to manually mold into the shape you like, but in  
the age of computers strikes me as not the most efficient way to get the  
task done  
  - respect to the artisanalness  
  - useful techniques for something highly aesthetic!  

---  

## David Mueller Neural Network Loss Landscape 
### Tuesday, July 19 2022  
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

---  

## esting 
### Monday, July 18 2022  
testing123  

---  

