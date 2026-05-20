# VIBE-CODED
"""
Tests for pfund_kit.paths module.

Tests three project layout scenarios:
1. src-layout: project_root/src/package_name/  (development)
2. flat-layout: project_root/package_name/  (development)
3. installed: site-packages/package_name/  (installed package)
"""

from pathlib import Path

import pytest

from pfund_kit.paths import ProjectPaths, _detect_project_layout


@pytest.fixture
def mock_home(tmp_path, monkeypatch):
    """Redirect Path.home() to tmp_path so user paths land under ~/.{project_name}/."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))  # Windows equivalent
    return tmp_path


class TestDetectProjectLayout:
    """Test the _detect_project_layout function with different project structures."""

    def test_src_layout_common_case(self, tmp_path):
        """src-layout: pfund/src/pfund/ (project == package name)"""
        project_root = tmp_path / "pfund"
        src_dir = project_root / "src"
        package_dir = src_dir / "pfund"
        module_file = package_dir / "paths.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        (project_root / "pyproject.toml").touch()

        project_name, package_path, detected_root = _detect_project_layout(module_file)

        assert project_name == "pfund"
        assert package_path == package_dir
        assert package_path.parent.name == "src"
        assert detected_root == project_root

    def test_src_layout_different_names(self, tmp_path):
        """src-layout where project and package names differ."""
        project_root = tmp_path / "my_project"
        src_dir = project_root / "src"
        package_dir = src_dir / "my_package"
        module_file = package_dir / "module.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        (project_root / "pyproject.toml").touch()

        project_name, package_path, detected_root = _detect_project_layout(module_file)

        # Should detect package name, not project root name.
        assert project_name == "my_package"
        assert package_path == package_dir
        assert detected_root == project_root

    def test_flat_layout(self, tmp_path):
        """flat-layout: project_root/package_name/module.py"""
        project_root = tmp_path / "pfund"
        package_dir = project_root / "pfund"
        module_file = package_dir / "paths.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()
        (project_root / "pyproject.toml").touch()

        project_name, package_path, detected_root = _detect_project_layout(module_file)

        assert project_name == "pfund"
        assert package_path == package_dir
        assert detected_root == project_root

    def test_installed_layout(self, tmp_path):
        """installed: site-packages/package_name/module.py (no pyproject.toml)."""
        site_packages = tmp_path / "site-packages"
        package_dir = site_packages / "pfund_kit"
        module_file = package_dir / "paths.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()

        project_name, package_path, detected_root = _detect_project_layout(module_file)

        assert project_name == "pfund_kit"
        assert package_path == package_dir
        # No pyproject.toml anywhere up the tree → detected_root is None.
        assert detected_root is None

    def test_real_pfund_kit_layout(self):
        """Real package: detection works in dev and any install."""
        from pfund_kit import paths
        actual_file = Path(paths.__file__)

        project_name, package_path, _ = _detect_project_layout(actual_file)

        assert project_name == "pfund_kit"
        assert package_path.name == "pfund_kit"
        parent_name = package_path.parent.name
        assert parent_name, "Parent directory name should not be empty"
        assert parent_name != "pfund_kit", "Parent should not have same name as package"


class TestProjectPathsClass:
    """Test the ProjectPaths class with different project structures."""

    def test_caller_auto_detection(self, mock_home):
        """source_file defaults to caller's __file__ when not provided."""
        paths = ProjectPaths(project_name='test_project')

        # The caller here is test_paths.py, in tests/.
        assert paths.package_path.name == 'tests'
        assert paths.project_name == 'test_project'
        assert paths.user_root == mock_home / '.test_project'
        assert paths.log_path == mock_home / '.test_project' / 'logs'

    def test_src_layout_with_custom_name(self, tmp_path, mock_home):
        """ProjectPaths honors custom project name over auto-detected."""
        package_dir = tmp_path / "test_project" / "src" / "test_package"
        module_file = package_dir / "test.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()

        paths = ProjectPaths(project_name='custom_name', source_file=str(module_file))

        assert paths.project_name == 'custom_name'
        assert paths.package_path == package_dir
        assert paths.user_root == mock_home / '.custom_name'
        assert paths.log_path == mock_home / '.custom_name' / 'logs'
        assert paths.data_path == mock_home / '.custom_name' / 'data'

    def test_flat_layout_auto_detect(self, tmp_path, mock_home):
        """ProjectPaths with flat-layout auto-detects project name."""
        package_dir = tmp_path / "test_project" / "test_package"
        module_file = package_dir / "test.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()

        paths = ProjectPaths(source_file=str(module_file))

        assert paths.project_name == 'test_package'
        assert paths.package_path == package_dir
        assert paths.log_path == mock_home / '.test_package' / 'logs'

    def test_installed_layout(self, tmp_path, mock_home):
        """ProjectPaths with installed package layout (no pyproject.toml)."""
        site_packages = tmp_path / "site-packages"
        package_dir = site_packages / "installed_package"
        module_file = package_dir / "module.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()

        paths = ProjectPaths(source_file=str(module_file))

        assert paths.project_name == 'installed_package'
        assert paths.package_path == package_dir
        assert paths.project_root is None

    def test_user_paths_consistency(self, tmp_path, mock_home):
        """User paths are identical across all layouts for a given project_name."""
        layouts = [
            tmp_path / "proj1" / "src" / "pkg1" / "mod.py",  # src-layout
            tmp_path / "proj2" / "pkg2" / "mod.py",          # flat-layout
            tmp_path / "site-packages" / "pkg3" / "mod.py",  # installed
        ]
        for module_file in layouts:
            module_file.parent.mkdir(parents=True)
            module_file.touch()

            paths = ProjectPaths(project_name='unified', source_file=str(module_file))

            assert paths.user_root == mock_home / '.unified'
            assert paths.log_path == mock_home / '.unified' / 'logs'
            assert paths.data_path == mock_home / '.unified' / 'data'
            assert paths.cache_path == mock_home / '.unified' / 'cache'
            assert paths.config_path == mock_home / '.unified' / 'config'


class TestProjectPathsInheritance:
    """Test that ProjectPaths can be subclassed properly."""

    def test_subclass_adds_custom_paths(self, tmp_path, mock_home):
        """Subclass can extend _setup_paths to add project-specific paths."""
        package_dir = tmp_path / "src" / "pfund"
        module_file = package_dir / "paths.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()

        class PfundPaths(ProjectPaths):
            def __init__(self, source_file):
                super().__init__(project_name='pfund', source_file=source_file)

            def _setup_paths(self, package_path: Path, project_root: Path | None = None):
                super()._setup_paths(package_path, project_root)
                # Add pfund-specific paths.
                self.strategies_path = self.data_path / 'strategies'
                self.models_path = self.data_path / 'models'

        paths = PfundPaths(source_file=str(module_file))

        assert paths.project_name == 'pfund'
        assert paths.package_path == package_dir
        assert paths.strategies_path == mock_home / '.pfund' / 'data' / 'strategies'
        assert paths.models_path == mock_home / '.pfund' / 'data' / 'models'


class TestDerivedPaths:
    """Paths derivable from package_path."""

    def test_derive_main_path_src_layout(self, tmp_path, mock_home):
        package_dir = tmp_path / "my_project" / "src" / "my_package"
        module_file = package_dir / "module.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()

        paths = ProjectPaths(source_file=str(module_file))

        # In src-layout, package_path.parent == src/
        assert paths.package_path.parent.name == "src"

    def test_derive_main_path_flat_layout(self, tmp_path, mock_home):
        project_root = tmp_path / "my_project"
        package_dir = project_root / "my_package"
        module_file = package_dir / "module.py"
        module_file.parent.mkdir(parents=True)
        module_file.touch()

        paths = ProjectPaths(source_file=str(module_file))

        # In flat-layout, package_path.parent == project_root.
        assert paths.package_path.parent == project_root
