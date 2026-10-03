---
name: backup-junk-cleaner-v2-1
description: Use when asked to clean junk files from backup directories with file duplication verification. Builds on v2.0 with MD5 content-based duplicate detection, two-phase size+hash filtering, and space savings estimation.
---

# Backup Junk Cleaner v2.1 - Project-Aware, IDE-Junk-Specific + File Duplication Verification

## When to activate
The user wants to clean junk files from a backup or data directory AND identify duplicate files by content. This is especially useful for backups that may contain multiple copies of the same file across different project folders, media collections, or versioned assets. Builds on v2.0 with full backward compatibility plus new duplicate detection.

## Prerequisites
- Python 3.8+ available on the system
- Source directory exists and is readable
- Trash destination path is known (or default to `~/Documents/Trash`)
- Sufficient RAM for hashing candidate files (chunked reading keeps memory low)

## Configuration
Before running, review or adjust these parameters in `cleanup_skill_v2_1.py`:

| Parameter | Default | Purpose |
|---|---|---|
| `DEFAULT_SOURCE_DIR` | `/home/cc/Documents/Backup novo` | Root backup directory to scan |
| `DEFAULT_TRASH_DIR` | `/home/cc/Documents/Trash` | Destination for moved junk files |
| `MAX_WEB_SIZE_BYTES` | `50 * 1024` (50 KB) | Threshold below which web formats are considered junk |
| `PROJECT_DEPTH_LIMIT` | `5` | Max directory depth to search for source files during project validation |
| `DUP_HASH_ALGORITHM` | `"md5"` | Hash algorithm: md5, sha1, or sha256 (md5 is fastest) |
| `DUP_MIN_FILE_SIZE` | `4096` (4 KB) | Skip files smaller than this during duplicate detection (noise reduction) |
| `DUP_CHUNK_SIZE` | `65536` (64 KB) | Read buffer size for hashing (memory efficiency) |

### Project Detection (Dual-Validation) - same as v2.0
A directory is a project ONLY if BOTH conditions are met:
1. A **project marker** file/folder exists at the directory level
2. At least one **source code file** exists within `PROJECT_DEPTH_LIMIT` levels below

**Project markers:** `.sln`, `CMakeLists.txt`, `pom.xml`, `vcxproj`, `project.pbxproj`, `package.json`, `go.mod`, `Cargo.toml`, `build.gradle`, `Makefile`, `setup.py`, `setup.cfg`, `pyproject.toml`, `requirements.txt`, `Gemfile`, `composer.json`, `pubspec.yaml`, `.git`, `package-lock.json`, `yarn.lock`, `Podfile`, `Rakefile`, `Justfile`, `SConstruct`, `meson.build`, `BUILD`, `WORKSPACE`, `.pro`, `.cbp`

**Source code extensions:** `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.java`, `.kt`, `.py`, `.pyx`, `.js`, `.jsx`, `.ts`, `.tsx`, `.go`, `.rs`, `.swift`, `.dart`, `.lua`, `.rb`, `.php`, `.sql`, `.sh`, `.cmake`, `.pro`, `.fgl`

### Junk Categories - same as v2.0

**General junk** (applied to all files outside projects):
- Metadata: `desktop.ini`, `.ds_store`, `.metadata`, `thumbs.db`
- FUSE artifacts: `.fuse_hidden*` (any file starting with `.fuse_hidden`)
- Thumbnails: `.thumb`, `.thumbnail`
- Configs: `.ini`, `.cfg`, `.conf`, `.env`, `.yaml`, `.yml`, `.toml`, `.json`, `.xml`, `.properties`, `.plist`
- Installers: `.exe`, `.msi`, `.dmg`, `.deb`, `.rpm`, `.pkg`, `.bat`, `.cmd`
- IDE project junk: `.cbp`, `.layout`, `.depend`, `.pro.user`, `.po~`
- Web-downloaded artifacts: files with formats `.html`, `.htm`, `.css`, `.js`, `.svg`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.ico`, `.pdf`, `.txt` that are under `MAX_WEB_SIZE_BYTES` AND match names like `download_*`, `untitled_*`, `image_*`, `screenshot_*`, `temp_*`, `img###`, `pic###`, `photo`, `picture`, `snapshot`, `capture`, `clipboard`, `screen`
- Man pages: `.3` extension (documentation, not source code)
- Blender backups: `.blend1` (auto-backup files from Blender)

**Project junk** (applied only inside detected projects):
- Directories: `bin`, `obj`, `build`, `dist`, `target`, `out`, `release`, `debug`, `static`, `output`, `generated`, `.vs`, `.idea`, `.clion`, `__pycache__`, `.tox`, `.pytest_cache`, `.gradle`, `.cache`, `node_modules`, `venv`, `blendcache_*`, `.vscode`
- Compiled binaries: `.dll`, `.so`, `.a`, `.lib`, `.dylib`, `.exe`, `.bin`, `.out`, `.class`, `.wasm`, `.jar`, `.war`, `.o`, `.pyc`, `.pyo`, `.ilk`, `.pdb`, `.exp`, `.tmp`, `.bak`
- Blender physics cache: `.bphys`

**IMPORTANT: .obj files are NOT junk.** The `.obj` extension is excluded from project junk extensions because `.obj` files are legitimate 3D model assets in game projects. However, directories named `obj/` (Visual Studio build output) AND `blendcache_*` ARE still cleaned up.

### Case-Insensitive Extension Handling - same as v2.0
All file extensions are normalized to lowercase before comparison. This ensures `.PNG`, `.JPG`, `.TGA` etc. are caught by the same rules as `.png`, `.jpg`, `.tga`.

## New in v2.1: File Duplication Verification

v2.1 adds **content-based duplicate detection** on top of v2.0's directory-level duplicate warnings. This uses a two-phase approach for efficiency:

### How Duplicate Detection Works

**Phase 1 - Size Grouping (fast filter)**
- All files are grouped by their exact byte size
- Files with unique sizes cannot be duplicates - they are skipped entirely
- Files below `DUP_MIN_FILE_SIZE` (default 4 KB) are skipped to avoid hashing noise (e.g., tiny config files, empty placeholders)

**Phase 2 - Content Hashing (verification)**
- Only files that share the same size are hashed using MD5 (configurable)
- Files with identical hashes are confirmed duplicates
- The first file alphabetically is marked as "KEPT", all others as "DUPLICATE"

### Why Two Phases?

Hashing every file in a large backup is slow and wastes CPU. By grouping by size first:
- A 100,000-file backup might only have ~500 files that share sizes with at least one other file
- Hashing drops from 100,000 operations to ~500 - a 200x speedup

### Output Format

During scan/execute, duplicate groups are displayed like this:

```
[md5_hash_prefix...] (1.5 MB each, 3 copies)
  * project_a/assets/logo.png  <- KEPT
  * project_b/assets/logo.png  <- DUPLICATE
  * backups_2024/project_a_assets/logo.png  <- DUPLICATE
```

The tool also reports:
- Total duplicate groups found
- Total extra files (copies beyond the first)
- Estimated space savings in human-readable format

### Safety Guarantees for Duplicates

- Duplicate detection is **read-only** - no files are deleted or moved based on duplicates
- Only the first file (alphabetically by path) is marked as "KEPT" - this is a suggestion, not an action
- The user must manually decide which copy to keep if they want to remove duplicates
- Hash collisions are virtually impossible with MD5 for typical backup files; use `sha256` if paranoid

## Execution Protocol

### Step 1 - Scan and Report (always first)
```bash
python cleanup_skill_v2_1.py --source /path/to/backup
```
- Performs a full scan and categorizes files into:
  - **Junk to move**: files/dirs matching junk patterns
  - **Projects detected**: directories with both markers and source files
  - **Directory duplicates**: directories that appear to be duplicates (same name, similar structure) - same as v2.0
  - **File content duplicates**: actual duplicate files identified by MD5 hash - **NEW in v2.1**
  - **Large archives**: `.rar`, `.zip`, `.7z`, `.tar.gz` files (reported but not moved)
  - **System fonts**: `.ttf` files in top-level `Art/` or system directories (flagged for review)
- Review the categorized log output and sample junk files listed
- Verify no important files are flagged for removal
- If adjustments needed, edit `SOURCE_CODE_EXTS`, `PROJECT_MARKERS`, `PROJECT_JUNK_DIRS`, or depth limits in the script

### Step 2 - Execute
```bash
python cleanup_skill_v2_1.py --source /path/to/backup --trash /path/to/trash --execute
```
- Files are moved (not deleted) to the trash directory, preserving their original relative paths
- Conflicting files in trash are logged and skipped (never overwritten)
- After moving files, empty directories left behind in the source are automatically removed
- Duplicate directory warnings are printed but directories are NOT automatically removed (user must confirm)
- **File content duplicates are reported but NOT auto-deleted** - user must manually remove copies

### Step 3 - Verify
```bash
find <trash> -type f | wc -l    # count moved files
ls -R <trash>                    # spot-check structure
```

## Safety Guarantees
- Scan is the default; actual moves require `--execute`
- Trash mirrors original directory structure - files are never lost
- No data overwritten; conflicts logged and skipped
- Permission errors caught gracefully, counted in error stats
- Stdlib-only - zero external dependencies
- Empty directories cleaned up after move (reverse walk)
- Case-insensitive extension matching prevents missed files
- Duplicate directory detection warns without auto-deleting
- **File content duplicate detection is read-only - no files deleted based on duplicates**
- Large archives and system fonts are reported, not silently removed
- Configuration separated from logic for easy auditing
- Chunked file hashing keeps memory usage low regardless of file size

## Customization Tips
- Add new source extensions to `SOURCE_CODE_EXTS` for languages you use (e.g., `.zig`, `.nim`, `.jl`)
- Add build directories to `PROJECT_JUNK_DIRS` if your projects produce them (e.g., `.vscode`, `build-cache`)
- Extend `WEB_NAME_RE` pattern with new prefixes like `^web_`, `^grab_`
- Increase or decrease `PROJECT_DEPTH_LIMIT` (3-10 range recommended)
- Add new project markers to `PROJECT_MARKERS` for your toolchain
- Adjust `MAX_WEB_SIZE_BYTES` based on your backup's typical file sizes
- **Lower `DUP_MIN_FILE_SIZE`** to detect duplicates among smaller files (but increases scan time)
- **Use `sha256` instead of `md5`** if you want stronger collision resistance at the cost of speed

## Completion Checklist
- [ ] Scan completed and reviewed
- [ ] Config parameters verified for this specific backup
- [ ] Duplicate warnings assessed (both directory-level and file-content)
- [ ] Large archives and system fonts reviewed (if any)
- [ ] `--execute` run completed successfully
- [ ] Trash directory spot-checked - no important files removed
- [ ] File duplicate groups reviewed - decide which copies to manually remove if needed
