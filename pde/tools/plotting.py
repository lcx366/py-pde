'''
Tools for plotting and controlling plot output using context managers

.. autosummary::
   :nosignatures:

   add_scaled_colorbar
   finalize_plot
   disable_interactive
   plot_on_axes
   plot_on_figure
   PlotReference
   BasicPlottingContext
   JupyterPlottingContext
   get_plotting_context
   napari_viewer

.. codeauthor:: David Zwicker <david.zwicker@ds.mpg.de>
'''


import contextlib
import functools
import logging
import warnings
from typing import Type, Dict, Tuple, Any, TYPE_CHECKING  # @UnusedImport

from ..tools.docstrings import replace_in_docstring

if TYPE_CHECKING:
    from ..grids.base import GridBase  # @UnusedImport

 

def add_scaled_colorbar(axes_image,
                        aspect: float = 20,
                        pad_fraction: float = 0.5,
                        **kwargs):
    """ add a vertical color bar to an image plot
    
    The height of the colorbar is now adjusted to the plot, so that the width
    determined by `aspect` is now given relative to the height. Moreover, the
    gap between the colorbar and the plot is now given in units of the fraction
    of the width by `pad_fraction`. 

    Inspired by https://stackoverflow.com/a/33505522/932593
    
    Args:
        axes_image: object returned from :meth:`matplotlib.pyplot.imshow`
        ax (:class:`matplotlib.axes.Axes`): the current figure axes
        aspect (float): the target aspect ratio of the colorbar
        pad_fraction (float): Width of the gap between colorbar and image
        **kwargs: Additional parameters are passed to colorbar call

    Returns:
        the result of the colorbar call
    """
    from mpl_toolkits import axes_grid1
    divider = axes_grid1.make_axes_locatable(axes_image.axes)
    width = axes_grid1.axes_size.AxesY(axes_image.axes, aspect=1./aspect)
    pad = axes_grid1.axes_size.Fraction(pad_fraction, width)
    cax = divider.append_axes("right", size=width, pad=pad)
    return axes_image.axes.figure.colorbar(axes_image, cax=cax, **kwargs)            
       


class nested_plotting_check():
    """ context manager that checks whether it is the root plotting call
    
    Example:
        The context manager can be used in plotting calls to check for nested
        plotting calls::
        
            with nested_plotting_check() as is_outermost_plot_call:
                make_plot(...)  # could potentially call other plotting methods
                if is_outermost_plot_call:
                    plt.show()
    
    """
    
    _is_plotting = False  # class variable keeping track of nesting
    
    
    def __init__(self):
        self.is_nested = None  # determines whether the this context is nested
    
    
    def __enter__(self):
        self.is_nested = self.__class__._is_plotting
        self.__class__._is_plotting = True
        return not self.is_nested
    
    
    def __exit__(self, *exc):
        if not self.is_nested:
            self.__class__._is_plotting = False



def finalize_plot(fig_or_ax=None,
                  title: str = None,
                  filename: str = None,
                  show: bool = False,
                  close_figure: bool = False) -> Tuple[Any, Any]:
    r""" finalizes a figure by adjusting relevant parameters
    
    Args:
        fig_or_ax:
            The figure or axes that are affected. If `None`, the current figure
            is used.
        title (str):
            Determines the title of the figure
        filename (str):
            If given, the resulting image is written to this file.
        show (bool):
            Flag determining whether :func:`matplotlib.pyplot.show` is called
        close_figure (bool):
            Whether the figure should be closed in the end
            
    Returns:
        tuple: The figure and the axes that were used to finalize the plot
    """
    import matplotlib.pyplot as plt
    
    # Deprecated this method on 2020-06-13
    warnings.warn("finalize_plot() method is deprecated. Use the decorators "
                  "plot_on_axes or plot_on_figure to control plots instead.",
                  DeprecationWarning)
    
    # determine which figure to modify    
    if fig_or_ax is None:
        fig = plt.gcf()  # current figure
        ax = fig.gca()
    elif hasattr(fig_or_ax, 'savefig'):
        fig = fig_or_ax  # figure is given
        ax = fig.gca()
    else:
        ax = fig_or_ax  # assume that axes are given
        fig = ax.get_figure()
    
    if title is not None:
        ax.set_title(title)
    
    if filename:
        fig.savefig(filename)
    if show:
        plt.show()
    if close_figure:
        plt.close(fig)
        
    return fig, ax
    
    

@contextlib.contextmanager
def disable_interactive():
    """ context manager disabling the interactive mode of matplotlib
    
    This context manager restores the previous state after it is done. Details
    of the interactive mode are described in :func:`matplotlib.interactive`.
    """
    import matplotlib.pyplot as plt

    if plt.isinteractive():
        # interactive mode is enabled => disable it temporarily
        plt.interactive(False) 
        yield
        plt.interactive(True)
        
    else:
        # interactive mode is already disabled => do nothing
        yield



class PlotReference():
    """ contains all information to update a plot element """
    
    __slots__ = ['ax', 'element', 'parameters']
    
    def __init__(self, ax, element: Any, parameters: Dict[str, Any] = None):
        """
        Args:
            ax (:class:`matplotlib.axes.Axes`): The axes of the element
            element (:class:`matplotlib.artist.Artist`): The actual element 
            parameters (dict): Parameters to recreate the plot element
        """
        self.ax = ax
        self.element = element
        self.parameters = {} if parameters is None else parameters



def plot_on_axes(wrapped=None, update_method=None):
    """ decorator for a plot method or function that uses a single axes
    
    This decorator adds typical options for creating plots that fill a single
    axes. These options are available via keyword arguments. These options can
    be described in the docstring, if the placeholder `{PLOT_ARGS}` is mentioned
    in the docstring of the wrapped function or method. Note that the decorator
    can be used on both functions and methods.

    Example:
        The following example illustrates how this decorator can be used to
        implement plotting for a given class. In particular, supplying the
        `update_method` will allow efficient dynamical plotting::
    
            class State:
                def __init__(self):
                    self.data = np.arange(8)
    
                def _update_plot(self, reference):
                    reference.element.set_ydata(self.data)
    
                @plot_on_axes(update_method='_update_plot')
                def plot(self, ax):
                    line, = ax.plot(np.arange(8), self.data)
                    return PlotReference(ax, line)
                    
                    
            @plot_on_axes
            def make_plot(ax):
                ax.plot(...)
                    
        When `update_method` is not supplied, the method can still be used for
        plotting, but dynamic updating, e.g., by
        :class:`pde.trackers.PlotTracker`, is not possible.

    Args:
        wrapped (callable):
            Function to be wrapped
        update_method (callable or str):
            Method to call to update the plot. The argument of the new
            method will be the result of the initial call of the wrapped
            method.
    """
    if wrapped is None:
        # handle the case where decorator was called without brackets
        return functools.partial(plot_on_axes, update_method=update_method)    
    
    def wrapper(*args,
                title: str = None,
                filename: str = None,
                action: str = 'auto',
                ax_style: Dict[str, Any] = None,
                ax=None,
                **kwargs):
        """
        title (str):
            Title of the plot. If omitted, the title might be chosen
            automatically.
        filename (str, optional):
            If given, the plot is written to the specified file.
        action (str):
            Decides what to do with the figure. If the argument is set to `show`
            :func:`matplotlib.pyplot.show` will be called to show the plot, if
            the value is `create`, the figure will be created, but not shown,
            and the value `close` closes the figure, after saving it to a file 
            when `filename` is given. The default value `auto` implies that the
            plot is shown if it is not a nested plot call.
        ax_style (dict):
            Dictionary with properties that will be changed on the axis
            after the plot has been drawn by calling
            :meth:`matplotlib.pyplot.setp`.
        ax (:class:`matplotlib.axes.Axes`):
            Figure axes to be used for plotting. If `None`, a new figure
            is created. This has no effect if a `reference` is supplied.
        """
        # Note on docstring: This docstring replaces the token {PLOT_ARGS} in 
        # the wrapped function
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        
        # some logic to check for nested plotting calls:
        with nested_plotting_check() as is_outermost_plot_call:
        
            # disable interactive plotting temporarily
            with disable_interactive():
                
                if ax is None:
                    # create new figure
                    backend = mpl.get_backend()
                    if 'backend_inline' in backend or 'nbAgg' == backend:
                        plt.close('all')  # close left over figures
                    fig, ax = plt.subplots()
                else:
                    fig = ax.get_figure()
            
                # call the actual plotting function
                reference = wrapped(*args, ax=ax, **kwargs)
                
                # finishing touches...            
                if title is not None:
                    ax.set_title(title)
                if ax_style:
                    plt.setp(ax, **ax_style)
                if filename:
                    fig.savefig(filename)
                    
            # decide what to do with the final plot
            if action == 'auto':
                if is_outermost_plot_call:
                    action = 'show'
                else:
                    action = 'create'
                    
            if action == 'show':
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    plt.show()
                    
            elif action == 'close':
                plt.close(fig)
                
            elif action != 'create':
                raise ValueError(f'Unknown action `{action}`')
            
        return reference
        
    # adjusting the signature of the wrapped function to include wrapper args
    import inspect
    sig_wrapped = inspect.signature(wrapped)
    parameters = tuple(arg
                       for name, arg in sig_wrapped.parameters.items()
                       if name != 'kwargs' and name != 'ax')
    
    sig_wrapper = inspect.signature(wrapper)
    parameters += tuple(sig_wrapper.parameters.values())
    wrapper.__signature__ = sig_wrapped.replace(parameters=parameters)
    
    # adjusting additional properties of the function to match the wrapped one
    wrapper.__name__ = wrapped.__name__        
    wrapper.__module__ = wrapped.__module__
    wrapper.__dict__.update(wrapped.__dict__)
    
    if wrapped.__doc__:
        replace_in_docstring(wrapper, '{PLOT_ARGS}', wrapper.__doc__,
                             docstring=wrapped.__doc__)

    wrapper.mpl_class = 'axes'
    wrapper.update_method = update_method
        
    return wrapper
    


def plot_on_figure(wrapped=None, update_method=None):
    """ decorator for a plot method or function that fills an entire figure
    
    This decorator adds typical options for creating plots that fill an
    entire figure. These options are available via keyword arguments. These
    options can be described in the docstring, if the placeholder `{PLOT_ARGS}`
    is mentioned in the docstring of the wrapped function or method. Note that
    the decorator can be used on both functions and methods.
    
    Example:
        The following example illustrates how this decorator can be used to
        implement plotting for a given class. In particular, supplying the
        `update_method` will allow efficient dynamical plotting::
    
            class State:
                def __init__(self):
                    self.data = np.random.random((2, 8))
    
                def _update_plot(self, reference):
                    ref1, ref2 = reference
                    ref1.element.set_ydata(self.data[0])
                    ref2.element.set_ydata(self.data[1])
    
                @plot_on_figure(update_method='_update_plot')
                def plot(self, fig):
                    ax1, ax2 = fig.subplots(1, 2)
                    l1, = ax1.plot(np.arange(8), self.data[0])
                    l2, = ax2.plot(np.arange(8), self.data[1])
                    return [PlotReference(ax1, l1), PlotReference(ax2, l2)]
                   
                    
            @plot_on_figure
            def make_plot(fig):
                ...
                    
                    
        When `update_method` is not supplied, the method can still be used for
        plotting, but dynamic updating, e.g., by
        :class:`pde.trackers.PlotTracker`, is not possible. 
        
        
    Args:
        wrapped (callable):
            Function to be wrapped
        update_method (callable or str):
            Method to call to update the plot. The argument of the new
            method will be the result of the initial call of the wrapped
            method.
    """
    if wrapped is None:
        # handle the case where decorator was called without brackets
        return functools.partial(plot_on_figure, update_method=update_method)    
    
    
    def wrapper(*args,
                title: str = None,
                constrained_layout: bool = True,
                filename: str = None,
                action: str = 'auto',
                fig_style: Dict[str, Any] = None,
                fig=None,
                **kwargs):
        """
        title (str):
            Title of the plot. If omitted, the title might be chosen
            automatically. This is shown above all panels.
        constrained_layout (bool):
            Whether to use `constrained_layout` in 
            :func:`matplotlib.pyplot.figure` call to create a figure. 
            This affects the layout of all plot elements.
        filename (str, optional):
            If given, the figure is written to the specified file.
        action (str):
            Decides what to do with the figure. If the argument is set to `show`
            :func:`matplotlib.pyplot.show` will be called to show the plot, if
            the value is `create`, the figure will be created, but not shown,
            and the value `close` closes the figure, after saving it to a file 
            when `filename` is given. The default value `auto` implies that the
            plot is shown if it is not a nested plot call.
        fig_style (dict):
            Dictionary with properties that will be changed on the
            figure after the plot has been drawn by calling
            :meth:`matplotlib.pyplot.setp`.
        fig (:class:`matplotlib.figures.Figure`):
            Figure that is used for plotting. If omitted, a new figure is
            created.
        """
        # Note on docstring: This docstring replaces the token {PLOT_ARGS} in 
        # the wrapped function
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        
        # some logic to check for nested plotting calls:
        with nested_plotting_check() as is_outermost_plot_call:
            
            # disable interactive plotting temporarily
            with disable_interactive():
                
                if fig is None:
                    # create new figure
                    backend = mpl.get_backend()
                    if 'backend_inline' in backend or 'nbAgg' == backend:
                        plt.close('all')  # close left over figures
                    fig = plt.figure(constrained_layout=constrained_layout)
            
                # call the actual plotting function
                reference = wrapped(*args, fig=fig, **kwargs)
                
                # finishing touches...            
                if title is not None:
                    fig.suptitle(title)
                if fig_style:
                    plt.setp(fig, **fig_style)
                if filename:
                    fig.savefig(filename)
                    
            # decide what to do with the final plot
            if action == 'auto':
                if is_outermost_plot_call:
                    action = 'show'
                else:
                    action = 'create'
                    
            if action == 'show':
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    plt.show()
                    
            elif action == 'close':
                plt.close(fig)
                
            elif action != 'create':
                raise ValueError(f'Unknown action `{action}`')  
                      
        return reference    
        
    # adjusting the signature of the wrapped function to include wrapper args
    import inspect
    sig_wrapped = inspect.signature(wrapped)
    parameters = tuple(arg
                       for name, arg in sig_wrapped.parameters.items()
                       if name != 'kwargs' and name != 'fig')
    
    sig_wrapper = inspect.signature(wrapper)
    parameters += tuple(sig_wrapper.parameters.values())
    wrapper.__signature__ = sig_wrapped.replace(parameters=parameters)
    
    # adjusting additional properties of the function to match the wrapped one
    wrapper.__name__ = wrapped.__name__        
    wrapper.__module__ = wrapped.__module__
    wrapper.__dict__.update(wrapped.__dict__)
    
    if wrapped.__doc__:
        replace_in_docstring(wrapper, '{PLOT_ARGS}', wrapper.__doc__,
                             docstring=wrapped.__doc__)

    wrapper.mpl_class = 'figure'
    wrapper.update_method = update_method
    
    return wrapper



class PlottingContextBase(object):
    """ base class of the plotting contexts
    
    Example:
        The context wraps calls to the :mod:`matplotlib.pyplot` interface::
    
            context = PlottingContext()
            with context:
                plt.plot(...)
                plt.xlabel(...)
    """
    
    supports_update: bool = True
    """ flag indicating whether the context supports that plots can be updated
    with out redrawing the entire plot """
    
    
    def __init__(self,
                 title: str = None,
                 show: bool = True):
        """ 
        Args:
            title (str): The shown in the plot
            show (bool): Flag determining whether plots are actually shown
        """
        self.title = title
        self.show = show
        
        self.initial_plot = True
        self.fig = None
        self._logger = logging.getLogger(__name__)
        self._logger.info(f'Initialize {self.__class__.__name__}')
    

    def __enter__(self):
        # start the plotting process
        if self.fig is not None:
            import matplotlib.pyplot as plt
            plt.figure(self.fig.number)
    

    def __exit__(self, *exc): 
        if self.initial_plot or not self.supports_update:
            # recreate the entire figure
            import matplotlib.pyplot as plt
            self.fig = plt.gcf()
            if len(self.fig.axes) == 0:
                # The figure seems to be empty, which must be a mistake
                raise RuntimeError('Plot figure does not contain axes')
            
            elif len(self.fig.axes) == 1:
                # The figure contains only a single axis, indicating that it is
                # composed of a single panel
                self._title = plt.title(self.title)
                
            else:
                # The figure contains multiple axes. This is an indication that
                # the figure consists of multiple panels, although insets and
                # colorbars also count as additional axes
                self._title = plt.suptitle(self.title)
                
            self.initial_plot = False
            
        else:
            # update the old figure
            self._title.set_text(self.title)


    def close(self):
        """ close the plot """
        # close matplotlib figure
        if self.fig is not None:
            import matplotlib.pyplot as plt
            plt.close(self.fig)



class BasicPlottingContext(PlottingContextBase):
    """ basic plotting using just matplotlib """
    
    def __init__(self,
                 fig_or_ax=None,
                 title: str = None,
                 show: bool = True):
        """
        Args:
            fig_or_ax:
                If axes are given, they are used. If a figure is given, it is 
                set as active.
            title (str):
                The shown in the plot
            show (bool):
                Flag determining whether plots are actually shown
        """
        import matplotlib.axes as mpl_axes
        import matplotlib.figure as mpl_figure
        
        super().__init__(title=title, show=show)
        
        # determine which figure to modify
        if isinstance(fig_or_ax, mpl_axes.Axes):
            self.fig = fig_or_ax.get_figure()  # assume that axes are given
        elif isinstance(fig_or_ax, mpl_figure.Figure):
            self.fig = fig_or_ax
    

    def __exit__(self, *exc): 
        super().__exit__(*exc)
        if self.show:
            self.fig.canvas.draw()  # required for display in nbagg backend
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # add a small pause to allow the GUI to run it's event loop
                import matplotlib.pyplot as plt
                plt.pause(1e-3)



class JupyterPlottingContext(PlottingContextBase):
    """ plotting in a jupyter widget using the `inline` backend """
    
    supports_update = False
    """ flag indicating whether the context supports that plots can be updated
    with out redrawing the entire plot. The jupyter backend (`inline`) requires
    replotting of the entire figure, so an update is not supported."""
    
    def __enter__(self):
        from IPython.display import display
        from ipywidgets import Output
        
        if self.initial_plot:
            # close all previous plots
            import matplotlib.pyplot as plt
            plt.close('all')
            
            # create output widget for capturing all plotting
            self._ipython_out = Output()
            
            if self.show:
                # only show the widget if necessary
                display(self._ipython_out)
            
        # capture plots in the output widget
        self._ipython_out.__enter__()
    
    
    def __exit__(self, *exc):
        import matplotlib.pyplot as plt
        # finalize plot
        super().__exit__(*exc)
        
        if self.show:
            # show the plot, but ...
            plt.show()  # show the figure to make sure it can be captured
        # ... also clear it the next time something is done        
        self._ipython_out.clear_output(wait=True)
            
        # stop capturing plots in the output widget
        self._ipython_out.__exit__(*exc)

        # close the figure, so figure windows do not accumulate
        plt.close(self.fig)
 

    def close(self):
        """ close the plot """
        super().close()
        # close ipython output
        try:
            self._ipython_out.close()
        except Exception:
            pass


        
def get_plotting_context(context=None,
                         title: str = None,
                         show: bool = True) -> PlottingContextBase:
    """ returns a suitable plotting context
    
    Args:
        context:
            An instance of :class:`PlottingContextBase` or an instance of
            :class:`matplotlib.axes.Axes` or :class:`matplotlib.figure.Figure`
            to determine where the plotting will happen. If omitted, the context
            is determined automatically.
        title (str):
            The title shown in the plot
        show (bool):
            Determines whether the plot is shown while the simulation is
            running. If `False`, the files are created in the background.
            
    Returns:
        :class:`PlottingContextBase`: The plotting context
    """
    import matplotlib as mpl
    import matplotlib.axes as mpl_axes
    import matplotlib.figure as mpl_figure
    
    if context is None:
        # figure out whether plots are shown in jupyter notebook
        
        if 'backend_inline' in mpl.get_backend():
            # special context to support the `inline` backend
            try:
                from IPython.display import display  # @UnusedImport
                from ipywidgets import Output  # @UnusedImport
            except ImportError:
                context_class: Type[PlottingContextBase] = BasicPlottingContext
            else:
                context_class = JupyterPlottingContext
                
        else:
            # standard context for all other backends
            context_class = BasicPlottingContext
        
        return context_class(title=title, show=show)    
    
    elif isinstance(context, PlottingContextBase):
        # re-use an existing context
        context.title = title
        context.show = show
        return context
    
    elif isinstance(context, (mpl_axes.Axes, mpl_figure.Figure)):
        # create a basic context based on the given axes or figure
        return BasicPlottingContext(fig_or_ax=context, title=title, show=show)
    
    else:
        raise RuntimeError(f'Unknown plotting context `{context}`')
        
        

@contextlib.contextmanager
def napari_viewer(grid: 'GridBase', **kwargs):
    """ creates an napari viewer for interactive plotting
    
    Args:
        grid (:class:`pde.grids.base.GridBase`): The grid defining the space
        **kwargs: Extra arguments are passed to :class:`napari.Viewer`
    """
    import napari
    
    if grid.num_axes == 1:
        raise RuntimeError('Interactive plotting only works for data with '
                           'at least 2 dimensions')
    
    viewer_args = kwargs
    viewer_args.setdefault('axis_labels', grid.axes)
    viewer_args.setdefault('ndisplay', 3 if grid.num_axes >= 3 else 2)
    
    with napari.gui_qt():  # create Qt GUI context
        yield napari.Viewer(**viewer_args)        
        