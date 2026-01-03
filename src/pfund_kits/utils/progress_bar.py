# VIBE-CODED
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Iterable, Iterator
    from rich.progress import TaskID

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from pfund_kits.utils import RichColor, RichTextStyle


class ProgressBar:
    """A simple wrapper around rich.progress.Progress for easy usage."""
    
    def __init__(
        self,
        iterable: Iterable | None = None,
        total: int | None = None,
        description: str = "Processing",
        *,
        spinner_style: str = (RichTextStyle.BOLD + RichColor.MAGENTA).value,
        text_style: str = (RichTextStyle.BOLD + RichColor.CYAN).value,
        bar_style: str = RichColor.BRIGHT_GREEN.value,
        bar_finished_style: str | None = None,
        progress_style: str = (RichTextStyle.BOLD + RichColor.YELLOW).value,
        transient: bool = False,
        show_time: bool | str = False,
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
        """
        from pfund_kits.utils import get_notebook_type
        
        self._iterable = iterable
        self._total = total if total is not None else (len(iterable) if hasattr(iterable, '__len__') else None)
        self._description = description
        self._transient = transient
        self._in_notebook = get_notebook_type() is not None
        
        # If bar_finished_style is not specified, use the same as bar_style
        if bar_finished_style is None:
            bar_finished_style = bar_style
        
        # Build columns list
        columns = [
            SpinnerColumn(style=spinner_style),
            TextColumn(f"[{text_style}]{{task.description}}"),
            BarColumn(complete_style=bar_style, finished_style=bar_finished_style),
            TaskProgressColumn(text_format=f"[{progress_style}]{{task.percentage:>3.0f}}%"),
        ]
        
        # Add time columns based on show_time parameter
        if show_time == 'elapsed':
            columns.append(TimeElapsedColumn())
        elif show_time == 'remaining':
            columns.append(TimeRemainingColumn())
        elif show_time is True:
            columns.append(TimeElapsedColumn())
            columns.append(TimeRemainingColumn())
        
        self._progress = Progress(*columns, transient=transient)
        self._task_id: TaskID | None = None
    
    def __enter__(self) -> ProgressBar:
        self._progress.__enter__()
        self._task_id = self._progress.add_task(self._description, total=self._total)
        return self
    
    def __exit__(self, *args) -> None:
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
        if self._task_id is not None:
            self._progress.update(self._task_id, advance=amount, refresh=self._in_notebook)
    
    def update(self, *, description: str | None = None, total: int | None = None) -> None:
        """Update the progress bar's description or total."""
        if self._task_id is not None:
            kwargs = {}
            if description is not None:
                kwargs['description'] = description
            if total is not None:
                kwargs['total'] = total
            if self._in_notebook:
                kwargs['refresh'] = True
            self._progress.update(self._task_id, **kwargs)


def track(
    iterable: Iterable,
    description: str = "Processing",
    total: int | None = None,
    *,
    spinner_style: str = (RichTextStyle.BOLD + RichColor.MAGENTA).value,
    text_style: str = (RichTextStyle.BOLD + RichColor.CYAN).value,
    bar_style: str = RichColor.BRIGHT_GREEN.value,
    bar_finished_style: str | None = None,
    progress_style: str = (RichTextStyle.BOLD + RichColor.YELLOW).value,
    transient: bool = False,
    show_time: bool | str = False,
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
    
    Yields:
        Items from the iterable.
    
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
    )
