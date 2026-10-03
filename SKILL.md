---
name: backup-junk-cleaner
description: Use when asked to clean up junk files (metadata, configs, thumbnails,
  installers, web-downloaded artifacts, build outputs) from backup directories. Automatically
  detects software projects via dual-validation and preserves project resources while
  removing only binaries and build artifacts inside them.
---

# Backup Junk Cleaner — Project-Aware

## When to activate
The user wants to clean junk files from a backup or data directory, especially when the directory contains software projects that should be preserved (source code, assets) but have build artifacts, IDE junk, and compiled binaries.

## Prerequisites
- Python 3.8+ available on the system
- Source directory exists and is readable
- Trash destination path is known (or default to `~/Documents/Trash`)

## Script Location
`/home/cc/Documents/LM/cleanup_skill.py` — stdlib-only, zero external dependencies.

## Configuration
Before running, review or adjust these parameters in the script:

| Parameter | Default | Purpose |
|---|---|---|
| `DEFAULT_SOURCE_DIR` | `/home/cc/Documents/Backup novo` | Root backup directory to scan |
| `DEFAULT_TRASH_DIR` | `/home/cc/Documents/Trash` | Destination for moved junk files |
| `MAX_WEB_SIZE_BYTES` | `50 * 1024` (50 KB) | Threshold below which web formats are considered junk |
| `PROJECT_DEPTH_LIMIT` | `5` | Max directory depth to search for source files during project validation |

### Project Detection (Dual-Validation)
A directory is a project ONLY if BOTH conditions are met:
1. A **project marker** file/folder exists at the directory level
2. At least one **source code file** exists within `PROJECT_DEPTH_LIMIT` levels below

**Project markers:** `.sln`, `CMakeLists.txt`, `pom.xml`, `vcxproj`, `project.pbxproj`, `package.json`, `go.mod`, `Cargo.toml`, `build.gradle`, `Makefile`, `setup.py`, `setup.cfg`, `pyproject.toml`, `requirements.txt`, `Gemfile`, `composer.json`, `pubspec.yaml`, `.git`, `package-lock.json`, `yarn.lock`, `Podfile`, `Rakefile`, `Justfile`, `SConstruct`, `meson.build`, `BUILD`, `WORKSPACE`

**Source code extensions:** `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.java`, `.kt`, `.py`, `.pyx`, `.js`, `.jsx`, `.ts`, `.tsx`, `.go`, `.rs`, `.swift`, `.dart`, `.lua`, `.rb`, `.php`, `.sql`, `.sh`, `.cmake`, `.pro`

### Junk Categories

**General junk** (applied to all files outside projects):
- Metadata: `desktop.ini`, `.ds_store`, `.metadata`, `thumbs.db`
- Thumbnails: `.thumb`, `.thumbnail`
- Configs: `.ini`, `.cfg`, `.conf`, `.env`, `.yaml`, `.yml`, `.toml`, `.json`, `.xml`, `.properties`, `.plist`
- Installers: `.exe`, `.msi`, `.dmg`, `.deb`, `.rpm`, `.pkg`, `.bat`, `.cmd`
- Web-downloaded artifacts: files with formats `.html`, `.htm`, `.css`, `.js`, `.svg`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.ico`, `.pdf`, `.txt` that are under `MAX_WEB_SIZE_BYTES` AND match names like `download_*`, `untitled_*`, `image_*`, `screenshot_*`, `temp_*`, `img###`, `pic###`, `photo`, `picture`, `snapshot`, `capture`, `clipboard`, `screen`

**Project junk** (applied only inside detected projects):
- Directories: `bin`, `obj`, `build`, `dist`, `target`, `out`, `release`, `debug`, `static`, `output`, `generated`, `.vs`, `.idea`, `.clion`, `__pycache__`, `.tox`, `.pytest_cache`, `.gradle`, `.cache`, `node_modules`, `venv`
- Compiled binaries: `.dll`, `.so`, `.a`, `.lib`, `.dylib`, `.exe`, `.bin`, `.out`, `.class`, `.wasm`, `.jar`, `.war`, `.o`, `.pyc`, `.pyo`, `.ilk`, `.pdb`, `.exp`, `.tmp`, `.bak`

**IMPORTANT: .obj files are NOT junk.** The `.obj` extension is excluded from project junk extensions because `.obj` files are legitimate 3D model assets in game projects. However, directories named `obj/` (Visual Studio build output) ARE still cleaned up.

## Execution Protocol

### Step 1 — Dry Run (always first, default behavior)
```bash
python cleanup_skill.py --source /path/to/backup --trash /path/to/trash
```
- Review the categorized log output and sample junk files listed
- Verify no important files are flagged for removal
- If adjustments needed, edit `SOURCE_CODE_EXTS`, `PROJECT_MARKERS`, `PROJECT_JUNK_DIRS`, or depth limits in the script

### Step 2 — Execute
```bash
python cleanup_skill.py --source /path/to/backup --trash /path/to/trash --execute
```
- Files are moved (not deleted) to the trash directory, preserving their original relative paths
- Conflicting files in trash are logged and skipped (never overwritten)
- After moving files, empty directories left behind in the source are automatically removed

### Step 3 — Verify
```bash
find <trash> -type f | wc -l    # count moved files
ls -R <trash>                    # spot-check structure
```

## Safety Guarantees
- ✅ Dry-run is the default; actual moves require `--execute`
- ✅ Trash mirrors original directory structure — files are never lost
- ✅ No data overwritten; conflicts logged and skipped
- ✅ Permission errors caught gracefully, counted in error stats
- ✅ Stdlib-only — zero external dependencies
- ✅ Empty directories cleaned up after move (reverse walk)
- ✅ Configuration separated from logic for easy auditing

## Customization Tips
- Add new source extensions to `SOURCE_CODE_EXTS` for languages you use (e.g., `.zig`, `.nim`, `.jl`)
- Add build directories to `PROJECT_JUNK_DIRS` if your projects produce them (e.g., `.vscode`, `build-cache`)
- Extend `WEB_NAME_RE` pattern with new prefixes like `^web_`, `^grab_`
- Increase or decrease `PROJECT_DEPTH_LIMIT` (3–10 range recommended)
- Add new project markers to `PROJECT_MARKERS` for your toolchain

## Completion Checklist
- [ ] Dry run completed and reviewed
- [ ] Config parameters verified for this specific backup
- [ ] `--execute` run completed successfully
- [ ] Trash directory spot-checked — no important files removed
