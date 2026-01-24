# VIBE-CODED
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, Iterator
    from rich.progress import TaskID

import logging
import os
import sys
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from pfund_kit.style import RichColor, TextStyle


def _should_disable_progress() -> bool:
    """Check if progress bars should be disabled via environment variable."""
    return os.getenv('PFUND_DISABLE_PROGRESS_BAR', '').lower() in ('1', 'true', 'yes')


class ProgressBar:
    """A simple wrapper around rich.progress.Progress for easy usage.

    Note:
        Progress bars can be disabled globally by setting the environment variable
        PFUND_DISABLE_PROGRESS_BAR=1 (or 'true' or 'yes'). This is useful when
        debugging with pdb or running in non-interactive environments.
    """
    
    def __init__(
        self,
        iterable: Iterable | None = None,
        total: int | None = None,
        description: str = "Processing",
        *,
        spinner_style: str = TextStyle.BOLD + RichColor.MAGENTA,
        text_style: str = TextStyle.BOLD + RichColor.CYAN,
        bar_style: str = RichColor.BRIGHT_GREEN,
        bar_finished_style: str | None = None,
        progress_style: str = TextStyle.BOLD + RichColor.YELLOW,
        transient: bool = False,
        show_time: bool | str = False,
        redirect_stdout: bool = False,
        redirect_stderr: bool = True,
    ):
        """
        Create a progress bar.
        
        Args:
            iterable: Optional iterable to track progress over.
            total: Total number of steps. Inferred from iterable if not provided.
            description: Text to display next to the progress bar.
            spinner_style: Style for the spinner.
            text_style: Style for the description text.
            bar_style: Style for the progress bar (both in progress and finished).
            bar_finished_style: Style for the progress bar when finished. If None, uses bar_style.
            progress_style: Style for the percentage text.
            transient: If True, the progress bar disappears after completion.
            show_time: Time display mode. False (default) = no time, 
                      'elapsed' = show elapsed time, 'remaining' = show time remaining,
                      True = show both elapsed and remaining.
            redirect_stdout: If True, redirect stdout so prints won't break the progress bar.
            redirect_stderr: If True, redirect stderr so logs won't break the progress bar.
        """
        from pfund_kit.utils import get_notebook_type

        self._iterable = iterable
        self._total = total if total is not None else (len(iterable) if hasattr(iterable, '__len__') else None)
        self._description = description
        self._transient = transient
        self._in_notebook = get_notebook_type() is not None
        self._redirect_stdout = redirect_stdout
        self._redirect_stderr = redirect_stderr
        self._patched_handlers: list[tuple[logging.StreamHandler, object]] = []
        if self._in_notebook:
            redirect_stdout = False
            redirect_stderr = False

        # If bar_finished_style is not specified, use the same as bar_style
        if bar_finished_style is None:
            bar_finished_style = bar_style

        # Build columns list
        columns = [
            SpinnerColumn(style=spinner_style),
            TextColumn(f"[{text_style}]{{task.description}}"),
            BarColumn(complete_style=bar_style, finished_style=bar_finished_style),
            TaskProgressColumn(text_format=f"[{progress_style}]{{task.percentage:>3.0f}}%"),
            MofNCompleteColumn(),
        ]

        # Add time columns based on show_time parameter
        if show_time == 'elapsed':
            columns.append(TimeElapsedColumn())
        elif show_time == 'remaining':
            columns.append(TimeRemainingColumn())
        elif show_time is True:
            columns.append(TimeElapsedColumn())
            columns.append(TimeRemainingColumn())

        self._progress = Progress(
            *columns,
            transient=transient,
            disable=_should_disable_progress(),
            redirect_stdout=redirect_stdout,
            redirect_stderr=redirect_stderr,
        )
        self._task_id: TaskID | None = None
    
    def __enter__(self) -> ProgressBar:
        if self._in_notebook:
            # In notebooks, use tqdm or simple percentage display
            try:
                from tqdm.auto import tqdm
                self._tqdm_bar = tqdm(total=self._total, desc=self._description, disable=_should_disable_progress())
                return self
            except ImportError:
                # Fallback: just track progress without display
                self._tqdm_bar = None
                return self

        self._progress.__enter__()
        self._task_id = self._progress.add_task(self._description, total=self._total)
        self._patch_stream_handlers()
        return self
    
    def __exit__(self, *args) -> None:
        if self._in_notebook:
            if hasattr(self, '_tqdm_bar') and self._tqdm_bar is not None:
                self._tqdm_bar.close()
            return

        try:
            self._restore_stream_handlers()
        finally:
            self._progress.__exit__(*args)
    
    def __iter__(self) -> Iterator:
        if self._iterable is None:
            raise ValueError("No iterable provided to iterate over")
        
        with self:
            for item in self._iterable:
                yield item
                self.advance()
    
    def advance(self, amount: int = 1) -> None:
        """Advance the progress bar by the given amount."""
        if self._in_notebook:
            if hasattr(self, '_tqdm_bar') and self._tqdm_bar is not None:
                self._tqdm_bar.update(amount)
            return

        if self._task_id is not None:
            self._progress.update(self._task_id, advance=amount)
    
    def update(self, *, description: str | None = None, total: int | None = None) -> None:
        """Update the progress bar's description or total."""
        if self._in_notebook:
            if hasattr(self, '_tqdm_bar') and self._tqdm_bar is not None:
                if description is not None:
                    self._tqdm_bar.set_description(description)
                if total is not None:
                    self._tqdm_bar.total = total
                    self._tqdm_bar.refresh()
            return

        if self._task_id is not None:
            kwargs = {}
            if description is not None:
                kwargs['description'] = description
            if total is not None:
                kwargs['total'] = total
            self._progress.update(self._task_id, **kwargs)

    def _patch_stream_handlers(self) -> None:
        if not (self._redirect_stdout or self._redirect_stderr):
            return

        def _iter_loggers() -> list[logging.Logger]:
            loggers: list[logging.Logger] = [logging.getLogger()]
            for logger in logging.Logger.manager.loggerDict.values():
                if isinstance(logger, logging.Logger):
                    loggers.append(logger)
            return loggers

        for logger in _iter_loggers():
            for handler in logger.handlers:
                if not isinstance(handler, logging.StreamHandler):
                    continue
                if handler.stream in (sys.__stderr__, sys.stderr) and self._redirect_stderr:
                    self._patched_handlers.append((handler, handler.stream))
                    handler.stream = sys.stderr
                elif handler.stream in (sys.__stdout__, sys.stdout) and self._redirect_stdout:
                    self._patched_handlers.append((handler, handler.stream))
                    handler.stream = sys.stdout

    def _restore_stream_handlers(self) -> None:
        if not self._patched_handlers:
            return
        for handler, stream in self._patched_handlers:
            handler.stream = stream
        self._patched_handlers.clear()


def track(
    iterable: Iterable,
    description: str = "Processing",
    total: int | None = None,
    *,
    spinner_style: str = TextStyle.BOLD + RichColor.MAGENTA,
    text_style: str = TextStyle.BOLD + RichColor.CYAN,
    bar_style: str = RichColor.BRIGHT_GREEN.value,
    bar_finished_style: str | None = None,
    progress_style: str = TextStyle.BOLD + RichColor.YELLOW,
    transient: bool = False,
    show_time: bool | str = False,
    redirect_stdout: bool = False,
    redirect_stderr: bool = True,
) -> Iterator:
    """
    Track progress over an iterable.

    A simple function to iterate with a progress bar (similar to tqdm).

    Args:
        iterable: The iterable to track.
        description: Text to display next to the progress bar.
        total: Total number of items. Inferred from iterable if not provided.
        spinner_style: Style for the spinner.
        text_style: Style for the description text.
        bar_style: Style for the progress bar (both in progress and finished).
        bar_finished_style: Style for the progress bar when finished. If None, uses bar_style.
        progress_style: Style for the percentage text.
        transient: If True, the progress bar disappears after completion.
        show_time: Time display mode. False (default) = no time,
                  'elapsed' = show elapsed time, 'remaining' = show time remaining,
                  True = show both elapsed and remaining.
        redirect_stdout: If True, redirect stdout so prints won't break the progress bar.
        redirect_stderr: If True, redirect stderr so logs won't break the progress bar.

    Yields:
        Items from the iterable.

    Note:
        Progress bars can be disabled globally by setting the environment variable
        PFUND_DISABLE_PROGRESS_BAR=1 (or 'true' or 'yes').

    Examples:
        # Basic usage
        for item in track([1, 2, 3, 4, 5], description="Processing"):
            process(item)

        # With elapsed time
        for item in track(data, description="Loading", show_time='elapsed'):
            load(item)

        # Custom colors
        for item in track(data, bar_style="red", text_style="bold white"):
            process(item)

        # Disable progress bars (useful for debugging)
        import os
        os.environ['PFUND_DISABLE_PROGRESS_BAR'] = '1'
    """
    yield from ProgressBar(
        iterable,
        total=total,
        description=description,
        spinner_style=spinner_style,
        text_style=text_style,
        bar_style=bar_style,
        bar_finished_style=bar_finished_style,
        progress_style=progress_style,
        transient=transient,
        show_time=show_time,
        redirect_stdout=redirect_stdout,
        redirect_stderr=redirect_stderr,
    )
