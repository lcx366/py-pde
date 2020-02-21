'''
.. codeauthor:: David Zwicker <david.zwicker@ds.mpg.de>
'''

import glob
import os
import subprocess as sp
from pathlib import Path
from typing import List  # @UnusedImport

import pytest
import numba as nb

from ..tools.misc import module_available



PACKAGE_PATH = Path(__file__).resolve().parents[2]
EXAMPLES = glob.glob(str(PACKAGE_PATH / 'examples' / '*.py'))
NOTEBOOKS = glob.glob(str(PACKAGE_PATH / 'examples' / 'jupyter' / '*.ipynb'))

if module_available("matplotlib"):
    SKIP_EXAMPLES: List[str] = []
else:
    SKIP_EXAMPLES = ['make_movie.py', 'trackers.py']



@pytest.mark.skipif(nb.config.DISABLE_JIT,
                    reason='pytest seems to check code coverage')
@pytest.mark.parametrize('path', EXAMPLES)
def test_example(path):
    """ runs an example script given by path """
    if os.path.basename(path).startswith('_'):
        pytest.skip('skip examples starting with an underscore')
    if any(name in path for name in SKIP_EXAMPLES):
        pytest.skip('require matplotlib')
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PACKAGE_PATH) + ":" + env.get("PYTHONPATH", "")
    proc = sp.Popen(['python3', path], env=env, stdout=sp.PIPE,
                    stderr=sp.PIPE)
    try:
        outs, errs = proc.communicate(timeout=30)
    except sp.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()            
        
    msg = 'Script `%s` failed with following output:' % path
    if outs:
        msg = '%s\nSTDOUT:\n%s' % (msg, outs)
    if errs:
        msg = '%s\nSTDERR:\n%s' % (msg, errs)
    assert proc.returncode == 0, msg



@pytest.mark.skipif(nb.config.DISABLE_JIT,
                    reason='pytest seems to check code coverage')
@pytest.mark.parametrize('path', NOTEBOOKS)
def test_jupyter_notebooks(path):
    """ run the jupyter notebooks """
    if os.path.basename(path).startswith('_'):
        pytest.skip('skip examples starting with an underscore')
    sp.check_call(['python3', '-m', 'jupyter', 'nbconvert', 
                   '--to', 'notebook', '--inplace',
                   '--execute', path])
