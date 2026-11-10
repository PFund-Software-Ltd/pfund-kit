## [0.1.25](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.24...v0.1.25) - 2026-11-10

### 🐛 Bug Fixes

- *(deps)* Lower pytz floor to 2026.1 for pyodide compatibility

## [0.1.24](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.23...v0.1.24) - 2026-11-10

### 🐛 Bug Fixes

- *(cli)* Harden remove command, expand ~ in config paths, shell alias completion
- *(pfund-shell)* Fit toolbar to terminal width, hide tui and full names of aliased commands

### ⚙️ Miscellaneous Tasks

- Re-init afterpython and fix all ruff/ty issues
- Add link venv script

## [0.1.23](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.22...v0.1.23) - 2026-11-07

### 💼 Other

- Lower packaging and pydantic floors so pfund-kit installs in Pyodide (WASM)
- Version 0.1.22 → 0.1.23

## [0.1.22](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.21...v0.1.22) - 2026-10-25

### 🚀 Features

- *(logging)* Accept an explicit logging_config in setup_logging
- *(utils)* Add ray utils moved from pfeed
- *(plugins)* Add PluginRegistry for entry point plugin discovery

### 🐛 Bug Fixes

- *(progress_bar)* Make ProgressBar and track generic over item type
- *(utils)* Remove stray self param from get_ray_num_cpus

### 🚜 Refactor

- *(config)* [**breaking**] Use .yaml extension for config, logging and compose files

### 💼 Other

- Drop uv.lock, add python 3.15, bump pixi to 0.82 and deps
- Disable exclude-newer cutoff until the package is stable
- Version 0.1.21 → 0.1.22

## [0.1.21](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.20...v0.1.21) - 2026-10-01

### 💼 Other

- Version 0.1.20 → 0.1.21
- Version 0.1.20 → 0.1.21

## [0.1.20](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.19...v0.1.20) - 2026-09-08

### 🐛 Bug Fixes

- The progress bar skips torch's read-only stderr handlers instead of trying to redirect them

### 💼 Other

- Version 0.1.19 → 0.1.20

## [0.1.19](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.18...v0.1.19) - 2026-09-06

### 💼 Other

- Version 0.1.18 → 0.1.19

## [0.1.18](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.17...v0.1.18) - 2026-09-06

### 💼 Other

- Version 0.1.17 → 0.1.18

## [0.1.17](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.16...v0.1.17) - 2026-08-06

### 🐛 Bug Fixes

- To_pascal_case and to_snake_case

### 💼 Other

- Version 0.1.16 → 0.1.17

## [0.1.16](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.15...v0.1.16) - 2026-08-06

### 💼 Other

- Version 0.1.15 → 0.1.16

## [0.1.15](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.14...v0.1.15) - 2026-07-24

### 💼 Other

- Version 0.1.14 → 0.1.15

## [0.1.14](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.13...v0.1.14) - 2026-07-18

### 🚀 Features

- Allow disabling the display of progress bar

### 💼 Other

- Version 0.1.13 → 0.1.14

## [0.1.13](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.12...v0.1.13) - 2026-07-18

### 🐛 Bug Fixes

- Report real caller location in ColoredLogger log records

### ⚙️ Miscellaneous Tasks

- Update to actions/checkout@v7

### 💼 Other

- Version 0.1.12 → 0.1.13

## [0.1.12](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.11...v0.1.12) - 2026-07-15

### 🚀 Features

- Declare style kwarg on ColoredLogger public log methods

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.11 → 0.1.12

## [0.1.11](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.10...v0.1.11) - 2026-05-25

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.10 → 0.1.11

## [0.1.10](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.9...v0.1.10) - 2026-05-20

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.9 → 0.1.10

## [0.1.9](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.8...v0.1.9) - 2026-05-17

### 🐛 Bug Fixes

- Cli version only shows pfund-kit's, not the real package's

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.8 → 0.1.9

## [0.1.8](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.7...v0.1.8) - 2026-05-17

### 🐛 Bug Fixes

- Cache logging config

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.7 → 0.1.8

## [0.1.7](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.6...v0.1.7) - 2026-05-14

### 💼 Other

- Version 0.1.6 → 0.1.7

## [0.1.6](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.5...v0.1.6) - 2026-05-13

### 💼 Other

- Version 0.1.5 → 0.1.6

## [0.1.5](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.4...v0.1.5) - 2026-05-11

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.4 → 0.1.5

## [0.1.4](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.3...v0.1.4) - 2026-03-21

### 🐛 Bug Fixes

- Config reset has no default file, needs to call config.save()

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.3 → 0.1.4

## [0.1.3](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.2...v0.1.3) - 2026-02-03

### 🚀 Features

- Support writing inline tables in toml dump
- Toml dump supports modes overwrite/update/merge

### 🐛 Bug Fixes

- Exclude aliases 'compose and 'rm' in pfund shell
- In pfund shell, invoke commands through their owning group (not shell_group) so the group's callback runs and sets up ctx.obj

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.2 → 0.1.3

## [0.1.2](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.1...v0.1.2) - 2026-01-31

### 🚀 Features

- Add handle_passthrough_help to cli utils

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.1 → 0.1.2

## [0.1.1](https://github.com/PFund-Software-Ltd/pfund-kit/compare/v0.1.0...v0.1.1) - 2026-01-28

### 🚀 Features

- Add MofNCompleteColumn to progress bar

### 🐛 Bug Fixes

- Increment stacklevel + 1 to skip the ColoredLogger._log() frame and find the actual caller.
- Remove .value in TextStyle + RichColor combo

### 🚜 Refactor

- Add SpacedStrEnum and TextStyle inherits from it

### ⚙️ Miscellaneous Tasks

- Reset version to 0.1.0 for proper release workflow

### 💼 Other

- Update pixi.lock after version bump
- Version 0.1.0 → 0.1.1
- Update pixi.lock after version bump
- Version 0.1.1 → 0.1.2
- Update pixi.lock after version bump
- Version 0.1.2 → 0.1.3
- Update pixi.lock after version bump
- Version 0.1.3 → 0.1.4
- Update pixi.lock after version bump
- Version 0.1.4 → 0.2.0
- Update pixi.lock after version bump
- Version 0.1.0 → 0.1.1

## [0.1.0] - 2026-01-23

### 🐛 Bug Fixes

- Use project root in local dev in config command
- Toml dump should deep merge
- Import error in progress bar
- Patch logging handlers to use Rich's FileProxy during progress bar display
- Move NotebookType out of TYPE_CHECKING
- Config migration bug
- Detect the correct package path in TrimmedPathFilter

### 💼 Other

- Version 0.0.1.dev1 → 0.1.0
