# VIBE-CODED
"""
Tests for pfund_kits.paths module.

Tests three project layout scenarios:
1. src-layout: project_root/src/package_name/  (development)
2. flat-layout: project_root/package_name/  (development)
3. installed: site-packages/package_name/  (installed package)
"""

from pathlib import Path

import pytest

from pfund_kits.paths import ProjectPaths, _detect_project_layout


@pytest.fixture
def mock_platformdirs(tmp_path, monkeypatch):
    """
    Mock platformdirs functions to return paths under tmp_path.
    This ensures tests are hermetic and don't pollute the real filesystem.
    
    Uses monkeypatch (pytest built-in) for simple attribute patching.
    """
    mock_log_dir = tmp_path / "logs"
    mock_data_dir = tmp_path / "data"
    mock_cache_dir = tmp_path / "cache"
    mock_config_dir = tmp_path / "config"
    
    # Patch the functions in the paths module (where they're imported)
    monkeypatch.setattr('pfund_kits.paths.user_log_dir', lambda: str(mock_log_dir))
    monkeypatch.setattr('pfund_kits.paths.user_data_dir', lambda: str(mock_data_dir))
    monkeypatch.setattr('pfund_kits.paths.user_cache_dir', lambda: str(mock_cache_dir))
    monkeypatch.setattr('pfund_kits.paths.user_config_dir', lambda: str(mock_config_dir))
    
    return {
        'log': mock_log_dir,
        'data': mock_data_dir,
        'cache': mock_cache_dir,
        'config': mock_config_dir,
    }


class TestDetectProjectLayout:
    """Test the _detect_project_layout function with different project structures."""
    
    def test_src_layout_common_case(self, tmp_path):
        """Test src-layout: pfund/src/pfund/ (common case where project == package name)"""
        # Create directory structure where project and package name are the same
        project_root = tmp_path / "pfund"
        src_dir = project_root / "src"
        package_dir = src_dir / "pfund"
        module_file = package_dir / "paths.py"
        
        # Create the directories and file
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Test detection
        project_name, package_path = _detect_project_layout(module_file)
        
        assert project_name == "pfund"
        assert package_path == package_dir
        assert package_path.name == "pfund"
        assert package_path.parent.name == "src"
        assert package_path.parent.parent == project_root
    
    def test_src_layout_different_names(self, tmp_path):
        """Test src-layout: project_root/src/package_name/ (rare case with different names)"""
        # Create directory structure
        project_root = tmp_path / "my_project"
        src_dir = project_root / "src"
        package_dir = src_dir / "my_package"
        module_file = package_dir / "module.py"
        
        # Create the directories and file
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Test detection - should detect package name, not project root name
        project_name, package_path = _detect_project_layout(module_file)
        
        assert project_name == "my_package"
        assert package_path == package_dir
        assert package_path.parent.name == "src"
    
    def test_flat_layout(self, tmp_path):
        """Test flat-layout: project_root/package_name/module.py"""
        # Create directory structure
        project_root = tmp_path / "pfund"
        package_dir = project_root / "pfund"
        module_file = package_dir / "paths.py"
        
        # Create the directories and file
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Test detection
        project_name, package_path = _detect_project_layout(module_file)
        
        assert project_name == "pfund"
        assert package_path == package_dir
        assert package_path.name == "pfund"
        assert package_path.parent == project_root
    
    def test_installed_layout(self, tmp_path):
        """Test installed: site-packages/package_name/module.py"""
        # Create directory structure (simulating site-packages)
        site_packages = tmp_path / "site-packages"
        package_dir = site_packages / "pfund_kits"
        module_file = package_dir / "paths.py"
        
        # Create the directories and file
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Test detection
        project_name, package_path = _detect_project_layout(module_file)
        
        assert project_name == "pfund_kits"
        assert package_path == package_dir
        assert package_path.name == "pfund_kits"
        assert package_path.parent == site_packages
    
    def test_real_pfund_kits_layout(self):
        """Test with the actual pfund_kits package (works in dev and any install)."""
        # Use the actual paths.py file location
        from pfund_kits import paths
        actual_file = Path(paths.__file__)
        
        project_name, package_path = _detect_project_layout(actual_file)
        
        # These invariants are always true regardless of installation method
        assert project_name == "pfund_kits"
        assert package_path.name == "pfund_kits"
        
        # Verify parent directory is reasonable (not overly restrictive about what it can be)
        parent_name = package_path.parent.name
        assert parent_name, "Parent directory name should not be empty"
        assert parent_name != "pfund_kits", "Parent should not have same name as package"


class TestProjectPathsClass:
    """Test the ProjectPaths class with different project structures."""
    
    def test_caller_auto_detection(self, mock_platformdirs):
        """Test that source_file defaults to caller's __file__ when not provided."""
        # When source_file is not passed, it should detect the caller's file
        # In this test, the caller is test_paths.py
        paths = ProjectPaths(project_name='test_project')
        
        # The package_path should be the tests/ directory (parent of test_paths.py)
        assert paths.package_path.name == 'tests'
        assert paths.project_name == 'test_project'
        
        # User paths should still work correctly with the provided project_name
        assert paths.log_path == mock_platformdirs['log'] / 'test_project'
    
    def test_src_layout_with_custom_name(self, tmp_path, mock_platformdirs):
        """Test ProjectPaths with src-layout and custom project name."""
        # Create src-layout structure
        project_root = tmp_path / "test_project"
        src_dir = project_root / "src"
        package_dir = src_dir / "test_package"
        module_file = package_dir / "test.py"
        
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Create ProjectPaths with custom name
        paths = ProjectPaths(project_name='custom_name', source_file=str(module_file))
        
        assert paths.project_name == 'custom_name'
        assert paths.package_path == package_dir
        assert paths.log_path == mock_platformdirs['log'] / 'custom_name'
        assert paths.data_path == mock_platformdirs['data'] / 'custom_name'
        assert paths.config_file_path.name == 'custom_name_config.yml'
    
    def test_flat_layout_auto_detect(self, tmp_path, mock_platformdirs):
        """Test ProjectPaths with flat-layout and auto-detection."""
        # Create flat-layout structure
        project_root = tmp_path / "test_project"
        package_dir = project_root / "test_package"
        module_file = package_dir / "test.py"
        
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Create ProjectPaths with auto-detection
        paths = ProjectPaths(source_file=str(module_file))
        
        assert paths.project_name == 'test_package'
        assert paths.package_path == package_dir
        assert paths.log_path == mock_platformdirs['log'] / 'test_package'
    
    def test_installed_layout(self, tmp_path, mock_platformdirs):
        """Test ProjectPaths with installed package layout."""
        # Create installed layout structure
        site_packages = tmp_path / "site-packages"
        package_dir = site_packages / "installed_package"
        module_file = package_dir / "module.py"
        
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Create ProjectPaths
        paths = ProjectPaths(source_file=str(module_file))
        
        assert paths.project_name == 'installed_package'
        assert paths.package_path == package_dir
        assert paths.package_path.parent == site_packages
    
    def test_user_paths_consistency(self, tmp_path, mock_platformdirs):
        """Test that user paths are consistent across all layouts."""
        layouts = [
            # src-layout
            tmp_path / "proj1" / "src" / "pkg1" / "mod.py",
            # flat-layout
            tmp_path / "proj2" / "pkg2" / "mod.py",
            # installed
            tmp_path / "site-packages" / "pkg3" / "mod.py",
        ]
        
        for module_file in layouts:
            module_file.parent.mkdir(parents=True)
            module_file.touch()
            
            paths = ProjectPaths(project_name='unified', source_file=str(module_file))
            
            # All should have the same user paths (using mocked dirs)
            assert paths.log_path == mock_platformdirs['log'] / 'unified'
            assert paths.data_path == mock_platformdirs['data'] / 'unified'
            assert paths.cache_path == mock_platformdirs['cache'] / 'unified'
            assert paths.config_path == mock_platformdirs['config'] / 'unified' / 'config'
            assert paths.config_file_path.name == 'unified_config.yml'


class TestProjectPathsInheritance:
    """Test that ProjectPaths can be subclassed properly."""
    
    def test_subclass_adds_custom_paths(self, tmp_path, mock_platformdirs):
        """Test subclassing ProjectPaths to add custom paths."""
        # Create a test structure
        package_dir = tmp_path / "src" / "pfund"
        module_file = package_dir / "paths.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        # Create a subclass
        class PfundPaths(ProjectPaths):
            def __init__(self, source_file):
                super().__init__(project_name='pfund', source_file=source_file)
            
            def _setup_paths(self, package_path: Path):
                super()._setup_paths(package_path)
                # Add pfund-specific paths
                self.strategies_path = self.data_path / 'strategies'
                self.models_path = self.data_path / 'models'
        
        # Test the subclass
        paths = PfundPaths(source_file=str(module_file))
        
        assert paths.project_name == 'pfund'
        assert paths.package_path == package_dir
        assert paths.strategies_path == mock_platformdirs['data'] / 'pfund' / 'strategies'
        assert paths.models_path == mock_platformdirs['data'] / 'pfund' / 'models'


class TestEnsureDirs:
    """Test the ensure_dirs method using mocked platformdirs (hermetic tests)."""
    
    def test_ensure_dirs_creates_directories(self, tmp_path, mock_platformdirs):
        """Test that ensure_dirs creates directories in the mocked location."""
        # Create a test structure
        package_dir = tmp_path / "test_pkg"
        module_file = package_dir / "test.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        paths = ProjectPaths(source_file=str(module_file))
        
        # Verify directories don't exist yet
        assert not paths.log_path.exists()
        assert not paths.data_path.exists()
        assert not paths.cache_path.exists()
        assert not paths.config_path.exists()
        
        # Ensure directories are created
        paths.ensure_dirs()
        
        # Verify they now exist in the mocked location
        assert paths.log_path.exists()
        assert paths.data_path.exists()
        assert paths.cache_path.exists()
        assert paths.config_path.exists()
        
        # Verify they're in the right location (under tmp_path)
        assert str(paths.log_path).startswith(str(tmp_path))
        assert str(paths.data_path).startswith(str(tmp_path))
    
    def test_ensure_specific_dirs(self, tmp_path, mock_platformdirs):
        """Test ensuring specific directories only."""
        package_dir = tmp_path / "test_pkg"
        module_file = package_dir / "test.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        paths = ProjectPaths(source_file=str(module_file))
        
        # Ensure only log and data paths
        paths.ensure_dirs('log_path', 'data_path')
        
        # These should now exist
        assert paths.log_path.exists()
        assert paths.data_path.exists()
        
        # These should NOT be created
        assert not paths.cache_path.exists()
        assert not paths.config_path.exists()


class TestDerivedPaths:
    """Test that paths can be derived from package_path."""
    
    def test_derive_main_path_src_layout(self, tmp_path):
        """Test deriving main_path from package_path in src-layout."""
        project_root = tmp_path / "my_project"
        src_dir = project_root / "src"
        package_dir = src_dir / "my_package"
        module_file = package_dir / "module.py"
        
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        paths = ProjectPaths(source_file=str(module_file))
        
        # Derive main_path
        main_path = paths.package_path.parent  # src/
        
        assert main_path == src_dir
        assert main_path.parent == project_root
    
    def test_derive_main_path_flat_layout(self, tmp_path):
        """Test deriving main_path from package_path in flat-layout."""
        project_root = tmp_path / "my_project"
        package_dir = project_root / "my_package"
        module_file = package_dir / "module.py"
        
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        paths = ProjectPaths(source_file=str(module_file))
        
        # Derive main_path
        main_path = paths.package_path.parent
        
        assert main_path == project_root
    
    def test_config_filename_derived(self, tmp_path, mock_platformdirs):
        """Test that config filename can be derived from config_file_path."""
        package_dir = tmp_path / "test_pkg"
        module_file = package_dir / "test.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        
        paths = ProjectPaths(project_name='myapp', source_file=str(module_file))
        
        # Derive config filename
        config_filename = paths.config_file_path.name
        
        assert config_filename == 'myapp_config.yml'
