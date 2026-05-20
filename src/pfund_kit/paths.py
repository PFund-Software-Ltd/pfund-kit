# VIBE-CODED
import inspect
from pathlib import Path

# User dirs live under ~/.{project_name}/ — same convention as docker, aws, git, kube.
# Intentionally not using platformdirs: macOS's ~/Library/Application Support is hostile
# to terminal-first developer workflows.
# from platformdirs import user_log_dir, user_data_dir, user_config_dir, user_cache_dir


def _detect_project_layout(source_file: Path) -> tuple[str, Path, Path | None]:
    """
    Auto-detect project layout and return (project_name, package_path, project_root).

    Handles three cases:
    1. src-layout: project_root/src/package_name/  (development)
    2. flat-layout: project_root/package_name/  (development)
    3. installed: site-packages/package_name/  (installed package)

    Returns:
        tuple: (project_name, package_path, project_root)
            - project_name: Name of the package (e.g., 'pfund_kit')
            - package_path: Actual package directory where code lives
            - project_root: Project root directory (None if installed in site-packages)
    """
    source_path = source_file.resolve()
    package_path = source_path.parent  # .../package_name/
    package_name = package_path.name

    # Try to find project root by looking for pyproject.toml
    # This helps distinguish development vs installed package
    project_root = None
    current = package_path
    for _ in range(10):  # Look up to 10 levels (handles deep nesting)
        current = current.parent
        if (current / 'pyproject.toml').exists():
            project_root = current
            break

    return package_name, package_path, project_root


class ProjectPaths:
    """Base class for managing project paths across pfund ecosystem."""

    def __init__(self, project_name: str | None = None, source_file: str | None = None):
        """
        Initialize project paths.

        Args:
            project_name: Name of the project. If None, auto-detects from source file.
            source_file: Path to a source file for determining project layout.
                        If None, auto-detects from the caller's __file__.
        """
        if source_file is None:
            frame = inspect.currentframe().f_back
            source_file = frame.f_globals['__file__']

        self._source_file = Path(source_file)

        # Auto-detect layout and paths
        detected_name, detected_package, detected_root = _detect_project_layout(self._source_file)

        # Use provided project_name or fall back to detected
        self.project_name = project_name or detected_name

        # Setup paths with detected package path and project root
        self._setup_paths(detected_package, detected_root)

    def _setup_paths(self, package_path: Path, project_root: Path | None = None):
        """
        Setup all project paths. Can be overridden by subclasses.

        Args:
            package_path: Path to the package directory (auto-detected).
            project_root: Path to the project root (None if installed package).
        """
        # Package path - where the code actually lives
        self.package_path = package_path

        # Project root - where pyproject.toml lives (None for installed packages)
        self.project_root = project_root

        # User paths — all under ~/.{project_name}/ regardless of OS.
        user_root = Path.home() / f'.{self.project_name}'
        self.user_root = user_root
        self.log_path = user_root / 'logs'
        self.data_path = user_root / 'data'
        self.cache_path = user_root / 'cache'
        self.config_path = user_root / 'config'
        # DEPRECATED: previous platform-native layout (kept for reference).
        # self.log_path = Path(user_log_dir()) / self.project_name
        # self.data_path = Path(user_data_dir()) / self.project_name
        # self.cache_path = Path(user_cache_dir()) / self.project_name
        # self.config_path = Path(user_config_dir()) / self.project_name / 'config'

    def __repr__(self):
        return f"{self.__class__.__name__}(project_name='{self.project_name}')"
