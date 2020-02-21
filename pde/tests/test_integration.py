'''
Integration tests that use multiple modules together

.. codeauthor:: David Zwicker <david.zwicker@ds.mpg.de>
'''


import tempfile

import numpy as np

from ..grids import UnitGrid, CartesianGrid
from ..fields import ScalarField
from ..pdes import DiffusionPDE
from ..storage import FileStorage
from ..tools.misc import skipUnlessModule



@skipUnlessModule('h5py')
def test_writing_to_storage():
    """ test whether data is written to storage """
    state = ScalarField.random_uniform(UnitGrid([3]))
    pde = DiffusionPDE()
    with tempfile.NamedTemporaryFile(suffix='.hdf5', delete=True) as file:
        data = FileStorage(filename=file.name)
        pde.solve(state, t_range=1.1, dt=0.1, tracker=[data.tracker(0.5)])
        
        assert len(data) == 3



def test_inhomogeneous_bcs():
    """ test simulation with inhomogeneous boundary conditions """
    grid = CartesianGrid([[0, 2*np.pi], [0, 1]], [32, 2],
                         periodic=[True, False])
    state = ScalarField(grid)
    pde = DiffusionPDE(bc=['natural', {'type': 'value', 'value': 'sin(x)'}])
    sol = pde.solve(state, t_range=1e1, dt=1e-2, tracker=None)
    data = sol.get_line_data('project_x')
    np.testing.assert_almost_equal(data['data_y'],
                                   0.9 * np.sin(data['data_x']), decimal=2)
