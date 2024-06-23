""" This code has been implemented according to the algorithm mentioned in the IEEE paper on "Candid Covariance-free Incremental Principal Component Analysis" by
Juyang Weng et. al. 
https://pdfs.semanticscholar.org/4e22/d6b9650a4ff9ccc8c9b860442d162d559025.pdf 
"""
#Covariance free Incremental Principal Component Analysis algorithm 

"""Candid covariance-free incremental principal component analysis (CCIPCA)
    Linear dimensionality reduction using an online incremental PCA algorithm.
    CCIPCA computes the principal components incrementally without
    estimating the covariance matrix. This algorithm was designed for high
    dimensional data and converges quickly. 
    This implementation only works for dense arrays. However it should scale
    well to large data.
    
    Time Complexity: per iteration 3 dot products and 2 additions over 'n' where 'n' is the number of features (n_features)."""
"""
    Working of algorithm: Calling fit(X) multiple times will update the components_ etc.
    
        An example of the implementation of this algorithm will be as follows: 
    >>> import numpy as np
    >>> from sklearn.decomposition import CCIPCA
    >>> X = np.array([[-1, -1], [-2, -1], [-3, -2], [1, 1], [2, 1], [3, 2]])
    >>> ccipca = CCIPCA(n_components=2)
    >>> ccipca.fit(X)
    CCIPCA(amnesic=2.0, copy=True, n_components=2)
    >>> print(ccipca.explained_variance_ratio_)
    [ 0.97074203  0.02925797]
    
    """
        
import numpy as np
from scipy import linalg as la
from sklearn.base import BaseEstimator, TransformerMixin
 
class CCIPCA(BaseEstimator, TransformerMixin):
    """ Function: CCIPCA 
        Parameters:
        n_components : int
        Number of components to keep.
    amnesia : float
        A parameter that weights the present more strongly than the
        past. amnesia=1 makes the present count the same as anything else.
    copy : bool"""
    def __init__(self, n_components=2, amnesic=2.0, copy=True):
        self.n_components = n_components
        if self.n_components < 2:
            raise ValueError ("must specifiy n_components for CCIPCA")
            
        self.copy = copy
        self.amnesic = amnesic
        self.iteration = 0
                
    """Function: fit 
        Fits the model with X.
    Parameters:
     X: array-like, shape (n_samples, n_features)
     Training data, where n_samples in the number of samples
    and n_features is the number of features.
    Returns:
    self : object
    Returns the instance itself.
 
     Calling this function multiple times will update the components
     """        

    def fit(self, X, y=None, **params):     
        X = np.array(X)
        n_samples, n_features = X.shape 
        
        # init
        if self.iteration == 0:  
            self.mean_ = np.zeros([n_features], np.float64)
            self.components_ = np.zeros([self.n_components,n_features], np.float64)
        else:
            if n_features != self.components_.shape[1]:
                raise ValueError('The dimensionality of the new data and the existing components_ does not match')   
        
        # incrementally fit the model
        for i in range(0,X.shape[0]):
            self.partial_fit(X[i,:])
        
        # update explained_variance_ratio_
        self.explained_variance_ratio_ = np.sqrt(np.sum(self.components_**2,axis=1)) #`explained_variance_ratio_` : array, [n_components]. Percentage of variance explained by each of the selected components.
        
        # sort by explained_variance_ratio_
        idx = np.argsort(-self.explained_variance_ratio_)
        self.explained_variance_ratio_ = self.explained_variance_ratio_[idx]
        self.components_ = self.components_[idx,:]
        
        # re-normalize
        self.explained_variance_ratio_ = (self.explained_variance_ratio_ / self.explained_variance_ratio_.sum())
            
        for r in range(0,self.components_.shape[0]):
            self.components_[r,:] /= np.sqrt(np.dot(self.components_[r,:],self.components_[r,:]))
        
        return self
        
        """ Function: partial_fit 
        It updates the mean and components to account for a new vector.
    Parameters: 
    u : array [1, n_features] a single new data sample
        """
      
    def partial_fit(self, u):
        
        n = float(self.iteration)
        V = self.components_ #`components_` : array, [n_components, n_features]; Components.
        
        # amnesic learning params
        if n <= int(self.amnesic):
            w1 = float(n+2-1)/float(n+2)    
            w2 = float(1)/float(n+2)    
        else:
            w1 = float(n+2-self.amnesic)/float(n+2)    
            w2 = float(1+self.amnesic)/float(n+2)

        # update mean
        self.mean_ = w1*self.mean_ + w2*u

        # mean center u        
        u = u - self.mean_

        # update components
        for j in range(0,self.n_components):
            
            if j > n:
                # the component has already been init to a zerovec
                pass
            
            elif j == n:
                # set the component to u 
                V[j,:] = u
            else:       
                # update the components
                V[j,:] = w1*V[j,:] + w2*np.dot(u,V[j,:])*u / la.norm(V[j,:])
                
                normedV = V[j,:] / la.norm(V[j,:])
            
                u = u - np.dot(np.dot(u.T,normedV),normedV)

        self.iteration += 1
        self.components_ = V
            
        return
    
        """Function: transform
        To apply the dimensionality reduction on X.
    Parameters:
    X : array-like, shape (n_samples, n_features)
    New data, where n_samples in the number of samples
    and n_features is the number of features.
    Returns:
    X_new : array-like, shape (n_samples, n_components)
    """
    def transform(self, X):
        X = np.array(X)
        X_transformed = X - self.mean_
        X_transformed = np.dot(X_transformed, self.components_.T)
        return X_transformed

        """Function: inverse_transform
        To transform data back to its original space, i.e., return an input X_original whose transform would be X
    Parameters:
        X : array-like, shape (n_samples, n_components)
            New data, where n_samples in the number of samples
            and n_components is the number of components.
    Returns:
        X_original array-like, shape (n_samples, n_features)
    """ 
    def inverse_transform(self, X):
        return np.dot(X, self.components_) + self.mean_
