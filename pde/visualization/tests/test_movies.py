'''
.. codeauthor:: David Zwicker <david.zwicker@ds.mpg.de>
'''

import os
import tempfile

from .. import movies
from ...grids import UnitGrid
from ...fields import ScalarField
from ...storage import MemoryStorage
from ...pdes import DiffusionPDE
from ...tools.misc import skipUnlessModule



@skipUnlessModule("matplotlib")
def test_simple():
    """ test Simple simulation """
    # create some data
    state = ScalarField.random_uniform(UnitGrid([16, 16]))
    pde = DiffusionPDE()
    storage = MemoryStorage()
    tracker = storage.tracker(interval=5)
    pde.solve(state, t_range=10, dt=1e-2, tracker=tracker)

    # check creating an video
    with tempfile.NamedTemporaryFile(suffix='.mov') as fp:
        movies.movie_scalar(storage, filename=fp.name, progress=False)
        assert os.stat(fp.name).st_size > 0
