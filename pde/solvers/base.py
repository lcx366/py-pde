"""
Package that contains base classes for solvers

.. codeauthor:: David Zwicker <david.zwicker@ds.mpg.de> 
"""

import logging
from typing import Dict, Any, List  # @UnusedImport
from abc import ABCMeta, abstractmethod

import numba as nb

from ..pdes.base import PDEBase
from ..fields.base import FieldBase
from ..tools.misc import classproperty



class SolverBase(metaclass=ABCMeta):
    """ base class for simulations """

    
    _subclasses: Dict[str, Any] = {}  # all classes inheriting from this
    
        
    def __init__(self, pde: PDEBase):
        """ initialize the solver
        
        Args:
            pde (:class:`~pde.pdes.base.PDEBase`):
                The partial differential equation that should be solved
        """
        self.pde = pde
        self.info: Dict[str, Any] = {'pde_class': self.pde.__class__.__name__}
        self._logger = logging.getLogger(self.__class__.__module__)
        

    def __init_subclass__(cls, **kwargs):  # @NoSelf
        """ register all subclassess to reconstruct them later """
        super().__init_subclass__(**kwargs)
        cls._subclasses[cls.__name__] = cls
        if hasattr(cls, 'name') and cls.name:
            if cls.name in cls._subclasses:
                logging.warn(f'Solver with name {cls.name} is already '
                             'registered')
            cls._subclasses[cls.name] = cls


    @classmethod
    def from_name(cls, name: str, pde: PDEBase, **kwargs) -> "SolverBase":
        r""" create solver class based on its name 
        
        Args:
            name (str):
                The name of the solver to construct
            pde (:class:`~pde.pdes.base.PDEBase`):
                The partial differential equation that should be solved
            \**kwargs:
                Additional arguments for the constructor of the solver
            
        Returns:
            An instance of a subclass of :class:`SolverBase`
        """
        try:
            solver_class = cls._subclasses[name]
        except KeyError:
            raise ValueError(f'Unknown solver method `{name}`')

        return solver_class(pde, **kwargs)  # type: ignore
    
    
    @classproperty
    def registered_solvers(cls) -> List[str]:  # @NoSelf
        """ list of str: the names of the registered solvers """
        return list(sorted(cls._subclasses.keys()))
    

    def _make_pde_rhs(self, state: FieldBase,
                      backend: str = 'auto',
                      allow_stochastic: bool = False):
        """ obtain a function for evaluating the right hand side
        
        Args:
            state (:class:`~pde.fields.FieldBase`):
                An example for the state from which the grid and other
                information can be extracted
                The instance describing the pde that needs to be solved
            backend (str):
                Determines how the function is created. Accepted  values are
                'numpy` and 'numba'. Alternatively, 'auto' lets the code decide
                for the most optimal backend.
            allow_stochastic (bool):
                Flag indicating whether stochastic simulations should be
                supported.
                
        Raises:
            RuntimeError: when a stochastic partial differential equation is
            encountered but `allow_stochastic == False`.
        
        Returns:
            A function that is called with data given by a
            :class:`numpy.ndarray` and a time. The function returns the 
            deterministic evolution rate and (if applicable) a realization of
            the associated noise.
        """
        if self.pde.is_sde and not allow_stochastic:
            raise RuntimeError(f'The chosen stepper does not support '
                               'stochastic equations')
        
        if self.pde.is_sde:
            rhs = self.pde.make_sde_rhs(state, backend=backend)
        else:
            rhs = self.pde.make_pde_rhs(state, backend=backend)
            
        if hasattr(rhs, '_backend'):
            self.info['backend'] = rhs._backend  # type: ignore
        elif isinstance(rhs, nb.dispatcher.Dispatcher):
            self.info['backend'] = 'numba'
        else:           
            self.info['backend'] = 'undetermined'
        
        return rhs
            

    @abstractmethod
    def make_stepper(self, state, dt: float = None):
        pass
   

