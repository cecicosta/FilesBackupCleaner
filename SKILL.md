---
name: backup-junk-cleaner-v2-2
description: 'Use when asked to clean junk files from backup directories with full
  duplicate handling. Builds on v2.1 with automated file duplicate deletion (move
  to trash), and smart directory duplicate resolution: project-under dirs are kept
  read-only, non-project duplicates are moved to trash.'
---

# Backup Junk Cleaner v2.2 - Project-Aware, IDE-Junk-Specific + Full Duplicate Handling

## When to activate
The user wants to clean junk files from a backup or data directory AND handle duplicates automatically:
- **Duplicate files**: moved to Trash (one copy kept)
- **Duplicate directories**: if under a project → kept read-only; otherwise → moved to Trash

This is the most aggressive cleanup version. Builds on v2.1 with automated duplicate removal and smart project-awareness for directory deduplication.

## Prerequisites
- Python 3.8+ available on the system
- Source directory exists and is readable
- Trash destination path is known (or default to `~/Documents/Trash`)
- Sufficient RAM for hashing candidate files (chunked reading keeps memory low)

## Configuration
Before running, review or adjust these parameters in `cleanup_skill_v2_2.py`:

| Parameter | Default | Purpose |
|---|---|---|
| `DEFAULT_SOURCE_DIR` | `/home/cc/Documents/Backup novo` | Root backup directory to scan |
| `DEFAULT_TRASH_DIR` | `/home/cc/Documents/Trash` | Destination for moved junk files |
| `MAX_WEB_SIZE_BYTES` | `50 * 1024` (50 KB) | Threshold below which web formats are considered junk |
| `PROJECT_DEPTH_LIMIT` | `5` | Max directory depth to search for source files during project validation |
| `DUP_HASH_ALGORITHM` | `"md5"` | Hash algorithm for file content: md5, sha1, or sha256 (md5 is fastest) |
| `DUP_MIN_FILE_SIZE` | `4096` (4 KB) | Skip files smaller than this during duplicate detection (noise reduction) |
| `DUP_CHUNK_SIZE` | `65536` (64 KB) | Read buffer size for hashing (memory efficiency) |
| `DUP_DIRS_VERIFY_CONTENT` | `True` | Verify directories have identical contents before moving duplicates |
| `DUP_DIRS_HASH_ALGO` | `"md5"` | Hash algorithm for directory content verification |

### Project Detection (Dual-Validation) - same as v2.1
A directory is a project ONLY if BOTH conditions are met:
1. A **project marker** file/folder exists at the directory level
2. At least one **source code file** exists within `PROJECT_DEPTH_LIMIT` levels below

**Project markers:** `.sln`, `CMakeLists.txt`, `pom.xml`, `vcxproj`, `project.pbxproj`, `package.json`, `go.mod`, `Cargo.toml`, `build.gradle`, `Makefile`, `setup.py`, `setup.cfg`, `pyproject.toml`, `requirements.txt`, `Gemfile`, `composer.json`, `pubspec.yaml`, `.git`, `package-lock.json`, `yarn.lock`, `Podfile`, `Rakefile`, `Justfile`, `SConstruct`, `meson.build`, `BUILD`, `WORKSPACE`, `.pro`, `.cbp`

**Source code extensions:** `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.java`, `.kt`, `.py`, `.pyx`, `.js`, `.jsx`, `.ts`, `.tsx`, `.go`, `.rs`, `.swift`, `.dart`, `.lua`, `.rb`, `.php`, `.sql`, `.sh`, `.cmake`, `.pro`, `.fgl`

### Junk Categories - same as v2.1

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

### Case-Insensitive Extension Handling - same as v2.1
All file extensions are normalized to lowercase before comparison. This ensures `.PNG`, `.JPG`, `.TGA` etc. are caught by the same rules as `.png`, `.jpg`, `.tga`.

## New in v2.2: Automated Duplicate Handling

v2.2 adds **automated duplicate removal** on top of v2.1's read-only reporting. This is the key difference from v2.1.

### File Duplicate Handling

**Detection** (unchanged from v2.1):
- Two-phase: size grouping → MD5 hashing
- First file alphabetically = "KEPT", all others = "DUPLICATE"

**On `--execute`:**
- All DUPLICATE files are **moved to Trash**
- The KEPT file remains in its original location
- Conflicts (file already exists in trash): skip and log
- Stats tracked: files moved as duplicates, space freed

### Directory Duplicate Handling - NEW in v2.2

**Detection** (same signature-based approach from v2.1):
- Group directories by `(dirname, file_count, subdir_count)`
- Groups with 2+ members are potential duplicates

**Smart Resolution on `--execute`:**

For each duplicate directory group:

1. **Check if any path in the group is under a detected project**
   - Walk up from each path to see if it falls within a detected project tree
   
2. **If YES (under a project):**
   - Mark ALL copies as **read-only** (`chmod 555`)
   - Report them clearly: "Project duplicate - kept read-only"
   - Do NOT move any of them

3. **If NO (not under any project):**
   - Keep the first file alphabetically in place
   - Move all other copies to Trash
   - Log which were moved vs kept

**Content Verification (optional but recommended):**
- If `DUP_DIRS_VERIFY_CONTENT` is True, hash all files inside each candidate directory before moving
- Directories with different contents are NOT considered duplicates
- This prevents accidentally moving directories that just happen to have the same name/structure but different content

### Output Format for Duplicates

**File duplicates:**
```
[md5_hash_prefix...] (1.5 MB each, 3 copies)
  * project_a/assets/logo.png    <- KEPT (stays in place)
  * project_b/assets/logo.png    <- DUPLICATE (moved to trash on --execute)
  * backups_2024/assets/logo.png <- DUPLICATE (moved to trash on --execute)
```

**Directory duplicates:**
```
[Textures] (30 files, 3 copies)
  * Projects/Cenario_medieval/Resources/Textures  <- KEPT (project dir)
  * Projects/Editor/Resources/Textures            <- READ-ONLY (project dir, chmod 555)
  * Labirinto/Resources/Textures                  <- DUPLICATE (moved to trash on --execute)
```

### Safety Guarantees for Duplicates

- **File duplicates**: Moved to Trash (not deleted). One copy always kept.
- **Directory duplicates under projects**: Kept read-only, never moved or modified.
- **Directory duplicates not under projects**: Moved to Trash, one copy kept.
- Conflicting files in trash: skipped and logged (never overwritten).
- Hash collisions are virtually impossible with MD5; use `sha256` if paranoid.
- Content verification can be disabled for speed (`DUP_DIRS_VERIFY_CONTENT = False`).

## Execution Protocol

### Step 1 - Scan and Report (always first)
```bash
python cleanup_skill_v2_2.py --source /path/to/backup
```
- Performs a full scan and categorizes everything including duplicate analysis
- Shows what WOULD be moved vs kept on `--execute`
- Review carefully before proceeding

### Step 2 - Execute
```bash
python cleanup_skill_v2_2.py --source /path/to/backup --trash /path/to/trash --execute
```
Actions performed in order:
1. Move junk files to Trash (same as v2.1)
2. Move junk directories to Trash (same as v2.1)
3. Move duplicate files to Trash (NEW - one copy kept)
4. Handle duplicate directories:
   - Project dirs → mark read-only
   - Non-project dirs → move duplicates to Trash
5. Clean up empty directories in source

### Step 3 - Verify
```bash
find <trash> -type f | wc -l    # count moved files
ls -R <trash>                    # spot-check structure
find <source> -perm -o-w         # check for read-only project dirs
```

## Safety Guarantees
- Scan is the default; actual moves require `--execute`
- Trash mirrors original directory structure - files are never lost
- No data overwritten; conflicts logged and skipped
- Permission errors caught gracefully, counted in error stats
- Stdlib-only - zero external dependencies
- Empty directories cleaned up after move (reverse walk)
- Case-insensitive extension matching prevents missed files
- **File duplicates are moved to Trash on execute** (one copy always kept)
- **Directory duplicates under projects are kept read-only** (never moved)
- **Directory duplicates not under projects are moved to Trash** (one copy kept)
- Large archives and system fonts are reported, not silently removed
- Content verification prevents moving non-identical directories
- Configuration separated from logic for easy auditing
- Chunked file hashing keeps memory usage low regardless of file size

## Customization Tips
- Add new source extensions to `SOURCE_CODE_EXTS` for languages you use (e.g., `.zig`, `.nim`, `.jl`)
- Add build directories to `PROJECT_JUNK_DIRS` if your projects produce them (e.g., `.vscode`, `build-cache`)
- Extend `WEB_NAME_RE` pattern with new prefixes like `^web_`, `^grab_`
- Increase or decrease `PROJECT_DEPTH_LIMIT` (3-10 range recommended)
- Add new project markers to `PROJECT_MARKERS` for your toolchain
- Adjust `MAX_WEB_SIZE_BYTES` based on your backup's typical file sizes
- **Disable `DUP_DIRS_VERIFY_CONTENT`** if you're confident about directory signatures and want faster execution
- **Use `sha256` instead of `md5`** if you want stronger collision resistance at the cost of speed

## Completion Checklist
- [ ] Scan completed and reviewed
- [ ] Config parameters verified for this specific backup
- [ ] Duplicate resolution strategy assessed (files moved, project dirs kept read-only, non-project dirs moved)
- [ ] Large archives and system fonts reviewed (if any)
- [ ] `--execute` run completed successfully
- [ ] Trash directory spot-checked - no important files removed
- [ ] Read-only project directories verified (should have mode 555 or similar)
