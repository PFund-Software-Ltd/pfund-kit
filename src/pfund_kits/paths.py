# VIBE-CODED
import inspect
from pathlib import Path

from platformdirs import user_log_dir, user_data_dir, user_config_dir, user_cache_dir


def _detect_project_layout(source_file: Path) -> tuple[str, Path]:
    """
    Auto-detect project layout and return (project_name, package_path).
    
    Handles three cases:
    1. src-layout: project_root/src/package_name/  (development)
    2. flat-layout: project_root/package_name/  (development)
    3. installed: site-packages/package_name/  (installed package)
    
    Returns:
        tuple: (project_name, package_path)
            - project_name: Name of the package (e.g., 'pfund_kits')
            - package_path: Actual package directory where code lives
    
    Note: If you need the project root (main_path), use package_path.parent
    """
    source_path = source_file.resolve()
    package_path = source_path.parent  # .../package_name/
    package_name = package_path.name
    
    return package_name, package_path


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
        detected_name, detected_package = _detect_project_layout(self._source_file)
        
        # Use provided project_name or fall back to detected
        self.project_name = project_name or detected_name
        
        # Setup paths with detected package path
        self._setup_paths(detected_package)
    
    def _setup_paths(self, package_path: Path):
        """
        Setup all project paths. Can be overridden by subclasses.
        
        Args:
            package_path: Path to the package directory (auto-detected).
        """
        # Package path - where the code actually lives
        self.package_path = package_path
        
        # User paths (platform-specific user directories) - THE IMPORTANT ONES
        self.log_path = Path(user_log_dir()) / self.project_name
        self.data_path = Path(user_data_dir()) / self.project_name
        self.cache_path = Path(user_cache_dir()) / self.project_name
        self.config_path = Path(user_config_dir()) / self.project_name / 'config'
        
        # Config file
        config_filename = f'{self.project_name}_config.yml'
        self.config_file_path = self.config_path / config_filename
    
    def ensure_dirs(self, *attrs: str):
        """Ensure specified directory paths exist."""
        if not attrs:
            attrs = ('log_path', 'data_path', 'cache_path', 'config_path')
        
        for attr in attrs:
            path = getattr(self, attr, None)
            if path and isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)
    
    def __repr__(self):
        return f"{self.__class__.__name__}(project_name='{self.project_name}')"
