---
name: backup-junk-cleaner-v2-4
description: Use when asked to clean junk files from backup directories with full
  duplicate handling AND project fingerprint-based duplicate detection. Builds on
  v2.2 with automated file/directory duplicate removal plus new read-only project-level
  duplicate identification using a three-layer fingerprint (root structure, extension
  distribution, identity signals). Projects are never auto-deleted — only reported
  ordered by last modified time.
---

---
name: backup-junk-cleaner-v2-4
description: Use when asked to clean junk files from backup directories with full duplicate handling AND project fingerprint-based duplicate detection. Builds on v2.2 with automated file/directory duplicate removal plus new read-only project-level duplicate identification using a three-layer fingerprint (root structure, extension distribution, identity signals). Projects are never auto-deleted — only reported ordered by last modified time.
---

# Backup Junk Cleaner v2.3 - Project-Aware, IDE-Junk-Specific + Full Duplicate Handling + Project Fingerprint Detection

## When to activate
The user wants to clean junk files from a backup or data directory AND handle duplicates automatically:
- **Duplicate files**: moved to Trash (one copy kept)
- **Duplicate directories**: if under a project → kept read-only; otherwise → moved to Trash
- **Duplicate projects** (NEW in v2.3): fingerprint-based detection, reported only — never auto-deleted

This is the most comprehensive cleanup version. Builds on v2.2 with automated duplicate removal and new project-level duplicate identification.

## Prerequisites
- Python 3.8+ available on the system
- Source directory exists and is readable
- Trash destination path is known (or default to `~/Documents/Trash`)
- Sufficient RAM for hashing candidate files (chunked reading keeps memory low)

## Configuration
Before running, review or adjust these parameters in `cleanup_skill_v2_4.py`:

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
| `PROJECT_DUP_THRESHOLD` | `0.50` (50%) | Minimum similarity score to flag a project duplicate group |

### Project Detection (Dual-Validation) - same as v2.2
A directory is a project ONLY if BOTH conditions are met:
1. A **project marker** file/folder exists at the directory level
2. At least one **source code file** exists within `PROJECT_DEPTH_LIMIT` levels below

**Project markers:** `.sln`, `CMakeLists.txt`, `pom.xml`, `vcxproj`, `project.pbxproj`, `package.json`, `go.mod`, `Cargo.toml`, `build.gradle`, `Makefile`, `setup.py`, `setup.cfg`, `pyproject.toml`, `requirements.txt`, `Gemfile`, `composer.json`, `pubspec.yaml`, `.git`, `package-lock.json`, `yarn.lock`, `Podfile`, `Rakefile`, `Justfile`, `SConstruct`, `meson.build`, `BUILD`, `WORKSPACE`, `.pro`, `.cbp`

**Source code extensions:** `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.java`, `.kt`, `.py`, `.pyx`, `.js`, `.jsx`, `.ts`, `.tsx`, `.go`, `.rs`, `.swift`, `.dart`, `.lua`, `.rb`, `.php`, `.sql`, `.sh`, `.cmake`, `.pro`, `.fgl`

### Junk Categories - same as v2.2

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

### Case-Insensitive Extension Handling - same as v2.2
All file extensions are normalized to lowercase before comparison. This ensures `.PNG`, `.JPG`, `.TGA` etc. are caught by the same rules as `.png`, `.jpg`, `.tga`.

## New in v2.3: Project Fingerprint & Duplicate Detection

v2.3 adds **project-level duplicate detection** on top of v2.2's file and directory duplicate handling. Unlike earlier versions that only detected individual file or directory duplicates, this detects entire projects that are copies of each other — even across different versions where file counts and sizes differ significantly.

### How Project Fingerprinting Works

When a directory is confirmed as a project via dual-validation (marker + source files), a **three-layer fingerprint** is computed:

#### Layer 1 — Root Structure (weight: 35%)
- Collect all **base names** (extension-stripped) of files at the project root
- Collect all **base names** of directories at the project root
- Combine into a single set and compute **Jaccard similarity** against other projects' sets
- Example: `{"src", "build", "README", "main", "assets"}`

This layer is tolerant of version drift — new assets or build outputs don't break the match because Jaccard similarity handles partial overlap.

#### Layer 2 — Extension Distribution (weight: 30%)
- Compute the **percentage breakdown** of file extensions at the project root
- Example: `png: 40%, json: 25%, c: 15%, txt: 10%, other: 10%`
- Compare using **cosine similarity** between extension vectors

This layer is robust against count changes — a project with 100 PNGs and another with 200 PNGs will still match well.

#### Layer 3 — Identity Signals (weight: 35%)
Binary match on three signals:
1. **Project name**: extracted from marker files (`package.json.name`, `Cargo.toml.package.name`, etc.) — **takes priority over directory name**
2. **Language signature**: which source languages are present at root (`.py`, `.c`, `.cpp`, `.js`, `.go`, `.rs`, etc.)
3. **Marker types present**: which project markers exist (`package.json`, `Cargo.toml`, `.git`, etc.)

All three signals must match for full credit; partial matches earn proportional weight.

### Similarity Calculation

```
similarity = (jaccard_similarity(layer1_a, layer1_b) * 0.35) +
             (cosine_similarity(layer2_a, layer2_b) * 0.30) +
             (identity_match_score(layer3_a, layer3_b) * 0.35)
```

- **≥ 50% similarity** → reported as a project duplicate group
- Groups are **ordered by last modified time of the project root directory** (oldest first)
- Projects from the same template but distinct versions can still match at ≥ 50% and will be reported
- **Never auto-deleted** — only reported in scan output, never touched during `--execute`

### Why No Content Hashing?

Content hashing of marker files or source files was explicitly excluded because:
- Projects change frequently (new commits, build outputs, asset updates)
- Even a single changed line breaks MD5/SHA256 comparison
- The three-layer fingerprint captures structural and semantic similarity without being fragile to minor changes

### Output Format for Project Duplicates

```
[Project Duplicates]

Group "mygame" (similarity: 78%)
  * /home/cc/Backup/mygame_v1   (modified: 2024-03-15) ← OLDEST — likely original
  * /home/cc/Backup/mygame_v2   (modified: 2025-06-20) ← newer copy

Group "asset-pack" (similarity: 62%)
  * /home/cc/Backup/textures_2023 (modified: 2023-11-01)
  * /home/cc/Backup/Textures      (modified: 2024-08-15)

Group "shared-ui" (similarity: 55%)
  * /home/cc/Backup/frontend/ui-kit   (modified: 2024-01-10)
  * /home/cc/Backup/backend/ui-library (modified: 2024-07-22)
```

### Edge Cases

| Case | Handling |
|---|---|
| Renamed projects | Identity signals carry enough weight; marker-derived name takes priority over directory name |
| Nested duplicates | Fingerprint only at project-level roots (where markers exist), not common ancestors |
| Mono-repos | Each project root with its own markers is fingerprinted independently |
| Template-based projects | 50% threshold allows them through without false positives on truly distinct projects |

## Automated Duplicate Handling (v2.2 features, unchanged)

### File Duplicate Handling

**Detection** (unchanged from v2.1):
- Two-phase: size grouping → MD5 hashing
- First file alphabetically = "KEPT", all others = "DUPLICATE"

**On `--execute`:**
- All DUPLICATE files are **moved to Trash**
- The KEPT file remains in its original location
- Conflicts (file already exists in trash): skip and log
- Stats tracked: files moved as duplicates, space freed

### Directory Duplicate Handling (v2.2 features, unchanged)

**Detection:**
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

### Output Format for File & Directory Duplicates (v2.2, unchanged)

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

### Safety Guarantees for Duplicates (v2.2 + v2.3 additions)

- **File duplicates**: Moved to Trash (not deleted). One copy always kept.
- **Directory duplicates under projects**: Kept read-only, never moved or modified.
- **Directory duplicates not under projects**: Moved to Trash, one copy kept.
- **Project duplicates**: Never touched — reported in scan output only, never auto-deleted.
- Conflicting files in trash: skipped and logged (never overwritten).
- Hash collisions are virtually impossible with MD5; use `sha256` if paranoid.
- Content verification can be disabled for speed (`DUP_DIRS_VERIFY_CONTENT = False`).

## Execution Protocol

### Step 1 - Scan and Report (always first)
```bash
python cleanup_skill_v2_4.py --source /path/to/backup
```
- Performs a full scan and categorizes everything:
  - **Junk to move**: files/dirs matching junk patterns
  - **Projects detected**: directories with both markers and source files
  - **File content duplicates**: actual duplicate files identified by MD5 hash
  - **Directory duplicates**: directories flagged for automated handling (move or read-only)
  - **Project duplicates** (NEW in v2.3): fingerprint-based project-level duplicate groups, reported only — never auto-deleted
  - **Large archives**: `.rar`, `.zip`, `.7z`, `.tar.gz` files (reported but not moved)
  - **System fonts**: `.ttf` files in top-level `Art/` or system directories (flagged for review)
- Shows what WOULD be moved vs kept on `--execute`
- Review carefully before proceeding

### Step 2 - Execute
```bash
python cleanup_skill_v2_4.py --source /path/to/backup --trash /path/to/trash --execute
```
Actions performed in order:
1. Move junk files to Trash (same as v2.2)
2. Move junk directories to Trash (same as v2.2)
3. Move duplicate files to Trash (same as v2.2 — one copy kept)
4. Handle duplicate directories:
   - Project dirs → mark read-only
   - Non-project dirs → move duplicates to Trash
5. **Project duplicates**: no action taken — already reported in scan phase
6. Clean up empty directories in source

### Step 3 - Verify
```bash
find <trash> -type f | wc -l    # count moved files
ls -R <trash>                    # spot-check structure
find <source> -perm -o-w         # check for read-only project dirs
```

## Safety Guarantees
- Scan is the default; actual moves require `--execute`
- Trash mirrors original directory structure — files are never lost
- No data overwritten; conflicts logged and skipped
- Permission errors caught gracefully, counted in error stats
- Stdlib-only — zero external dependencies
- Empty directories cleaned up after move (reverse walk)
- Case-insensitive extension matching prevents missed files
- **File duplicates are moved to Trash on execute** (one copy always kept)
- **Directory duplicates under projects are kept read-only** (never moved)
- **Directory duplicates not under projects are moved to Trash** (one copy kept)
- **Project duplicates are NEVER auto-deleted or modified** — only reported, ordered by last modified time
- Large archives and system fonts are reported, not silently removed
- Content verification prevents moving non-identical directories
- Configuration separated from logic for easy auditing
- Chunked file hashing keeps memory usage low regardless of file size

## Customization Tips
- Add new source extensions to `SOURCE_CODE_EXTS` for languages you use (e.g., `.zig`, `.nim`, `.jl`)
- Add build directories to `PROJECT_JUNK_DIRS` if your projects produce them (e.g., `.vscode`, `build-cache`)
- Extend `WEB_NAME_RE` pattern with new prefixes like `^web_`, `^grab_`
- Increase or decrease `PROJECT_DEPTH_LIMIT` (3–10 range recommended)
- Add new project markers to `PROJECT_MARKERS` for your toolchain
- Adjust `MAX_WEB_SIZE_BYTES` based on your backup's typical file sizes
- **Disable `DUP_DIRS_VERIFY_CONTENT`** if you're confident about directory signatures and want faster execution
- **Use `sha256` instead of `md5`** if you want stronger collision resistance at the cost of speed
- **Adjust `PROJECT_DUP_THRESHOLD`** (0.30–0.70 recommended) — lower for template-based projects, higher for stricter matching

## Completion Checklist
- [ ] Scan completed and reviewed
- [ ] Config parameters verified for this specific backup
- [ ] Duplicate resolution strategy assessed (files moved, project dirs kept read-only, non-project dirs moved)
- [ ] **Project duplicate groups reviewed** — decide whether to manually clean up older or newer copies
- [ ] Large archives and system fonts reviewed (if any)
- [ ] `--execute` run completed successfully
- [ ] Trash directory spot-checked — no important files removed
- [ ] Read-only project directories verified (should have mode 555 or similar)
