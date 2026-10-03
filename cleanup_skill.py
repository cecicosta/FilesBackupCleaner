#!/usr/bin/env python3
"""Backup Junk Cleaner v2.1 - Project-Aware, IDE-Junk-Specific + File Duplication Verification"""

import os
import sys
import re
import shutil
import hashlib
from collections import defaultdict
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_SOURCE_DIR = "/home/cc/Documents/Backup novo"
DEFAULT_TRASH_DIR = os.path.expanduser("~/Documents/Trash")
MAX_WEB_SIZE_BYTES = 50 * 1024
PROJECT_DEPTH_LIMIT = 5
DUP_HASH_ALGORITHM = "md5"
DUP_MIN_FILE_SIZE = 4096
DUP_CHUNK_SIZE = 65536

PROJECT_MARKERS = {
    ".sln", "CMakeLists.txt", "pom.xml", "vcxproj", "project.pbxproj",
    "package.json", "go.mod", "Cargo.toml", "build.gradle", "Makefile",
    "setup.py", "setup.cfg", "pyproject.toml", "requirements.txt", "Gemfile",
    "composer.json", "pubspec.yaml", "package-lock.json", "yarn.lock",
    "Podfile", "Rakefile", "Justfile", "SConstruct", "meson.build",
    "BUILD", "WORKSPACE", ".pro", ".cbp",
}

SOURCE_CODE_EXTS = {
    ".c", ".cpp", ".h", ".hpp", ".cs", ".java", ".kt", ".py", ".pyx",
    ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".swift", ".dart",
    ".lua", ".rb", ".php", ".sql", ".sh", ".cmake", ".pro", ".fgl",
}

METADATA_NAMES = {
    "desktop.ini", ".ds_store", ".metadata", "thumbs.db",
}

CONFIG_EXTS = {".ini", ".cfg", ".conf", ".env", ".yaml", ".yml", ".toml",
              ".json", ".xml", ".properties", ".plist"}

INSTALLER_EXTS = {".exe", ".msi", ".dmg", ".deb", ".rpm", ".pkg", ".bat", ".cmd"}

IDE_JUNK_EXTS = {".cbp", ".layout", ".depend", ".pro.user", ".po~"}

WEB_FORMATS = {".html", ".htm", ".css", ".js", ".svg", ".png", ".jpg",
               ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".txt"}

WEB_NAME_RE = re.compile(
    r"^(download_|untitled_|image_|screenshot_|temp_|img\d{3,}|pic\d{3,}|"
    r"photo|picture|snapshot|capture|clipboard|screen)",
    re.IGNORECASE,
)

PROJECT_JUNK_DIRS = {
    "bin", "obj", "build", "dist", "target", "out", "release", "debug",
    "static", "output", "generated", ".vs", ".idea", ".clion", "__pycache__",
    ".tox", ".pytest_cache", ".gradle", ".cache", "node_modules", "venv",
    ".vscode",
}

COMPILED_EXTS = {".dll", ".so", ".a", ".lib", ".dylib", ".exe", ".bin", ".out",
                 ".class", ".wasm", ".jar", ".war", ".o", ".pyc", ".pyo",
                 ".ilk", ".pdb", ".exp", ".tmp", ".bak"}

LARGE_ARCHIVE_EXTS = {".rar", ".zip", ".7z", ".tar.gz", ".tar.bz2", ".tar.xz"}


def human_size(nbytes):
    """Convert bytes to human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def get_hash(filepath, algorithm="md5"):
    """Read file in chunks and return hex digest."""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(DUP_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def is_project_dir(dirpath):
    """Dual-validation: marker + source files within depth limit."""
    try:
        entries = os.listdir(dirpath)
    except PermissionError:
        return False

    has_marker = any(
        name in PROJECT_MARKERS or (isinstance(name, str) and name.lower() == ".git")
        for name in entries
    )
    if not has_marker:
        return False

    base_depth = dirpath.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(dirpath):
        current_depth = root.rstrip(os.sep).count(os.sep) - base_depth
        if current_depth >= PROJECT_DEPTH_LIMIT:
            dirs.clear()
            continue
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SOURCE_CODE_EXTS:
                return True
    return False


def is_blendcache_dir(dirname):
    """Check if directory matches blendcache_* pattern."""
    return dirname.startswith("blendcache_")


def get_file_ext(filepath):
    """Get lowercase file extension, handling .tar.gz etc."""
    name = os.path.basename(filepath)
    if name.endswith(".tar.gz"):
        return ".tar.gz"
    if name.endswith(".tar.bz2"):
        return ".tar.bz2"
    if name.endswith(".tar.xz"):
        return ".tar.xz"
    _, ext = os.path.splitext(name)
    return ext.lower()


def check_junk_file(filepath, dirpath):
    """Check if a file is junk. Returns (is_junk, category) tuple."""
    basename = os.path.basename(filepath)
    ext = get_file_ext(filepath)

    if basename.lower() in METADATA_NAMES:
        return True, "metadata"

    if basename.startswith(".fuse_hidden"):
        return True, "fuse_artifact"

    if ext in (".thumb", ".thumbnail"):
        return True, "thumbnail"

    if ext in CONFIG_EXTS:
        return True, "config"

    if ext in INSTALLER_EXTS:
        return True, "installer"

    if ext in IDE_JUNK_EXTS:
        return True, "ide_junk"

    if ext == ".3":
        return True, "man_page"

    if ext == ".blend1":
        return True, "blender_backup"

    if ext in WEB_FORMATS:
        try:
            fsize = os.path.getsize(filepath)
        except OSError:
            fsize = 0
        if fsize <= MAX_WEB_SIZE_BYTES and WEB_NAME_RE.search(basename):
            return True, "web_artifact"

    is_project = is_project_dir(dirpath)
    if is_project and ext in COMPILED_EXTS:
        return True, "compiled_binary"

    if ext == ".bphys":
        return True, "blender_physics_cache"

    return False, None


def check_junk_dir(dirpath):
    """Check if a directory is junk. Returns (is_junk, category) tuple."""
    dirname = os.path.basename(dirpath)
    if not dirname:
        return False, None

    if is_project_dir(os.path.dirname(dirpath)):
        if dirname.lower() in PROJECT_JUNK_DIRS or is_blendcache_dir(dirname):
            return True, "project_build_dir"

    if is_blendcache_dir(dirname):
        return True, "blendcache_dir"

    return False, None


def find_directory_duplicates(source_root):
    """Find potential duplicate directories by name and structure."""
    dir_info = defaultdict(list)
    for root, dirs, files in os.walk(source_root):
        rel_path = os.path.relpath(root, source_root)
        if rel_path == ".":
            continue
        dirname = os.path.basename(root)
        file_count = len(files)
        subdirs_count = len(dirs)
        dir_info[(dirname, file_count, subdirs_count)].append(rel_path)

    duplicates = {}
    for key, paths in dir_info.items():
        if len(paths) > 1:
            duplicates[key] = paths
    return duplicates


def find_file_duplicates(source_root):
    """Two-phase duplicate detection: size grouping + content hashing."""
    print("\n" + "=" * 60)
    print("PHASE 1: Grouping files by size...")
    print("=" * 60)

    size_groups = defaultdict(list)
    total_files = 0
    skipped_small = 0

    for root, dirs, files in os.walk(source_root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                fsize = os.path.getsize(fpath)
            except OSError:
                continue

            total_files += 1
            if fsize < DUP_MIN_FILE_SIZE:
                skipped_small += 1
                continue
            size_groups[fsize].append(fpath)

    print(f"  Scanned {total_files} files, skipped {skipped_small} small files (<{DUP_MIN_FILE_SIZE} bytes)")
    dup_candidates = sum(len(v) for v in size_groups.values() if len(v) > 1)
    print(f"  Files in size groups (potential duplicates): {dup_candidates}")

    print("\nPHASE 2: Hashing potential duplicates...")
    print("=" * 60)

    dup_groups = defaultdict(list)
    hashes_computed = 0
    hash_algorithm = DUP_HASH_ALGORITHM

    for fsize, paths in size_groups.items():
        if len(paths) < 2:
            continue
        paths.sort()
        for fpath in paths:
            try:
                digest = get_hash(fpath, hash_algorithm)
                dup_groups[(digest, fsize)].append(fpath)
                hashes_computed += 1
            except OSError as e:
                print(f"  Warning: Could not read {fpath}: {e}", file=sys.stderr)

    dup_groups = {k: v for k, v in dup_groups.items() if len(v) > 1}

    print(f"  Hashed {hashes_computed} candidate files")
    print(f"  Found {len(dup_groups)} duplicate groups\n")

    return dup_groups


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backup Junk Cleaner v2.1")
    parser.add_argument("--source", default=DEFAULT_SOURCE_DIR, help="Source backup directory")
    parser.add_argument("--trash", default=DEFAULT_TRASH_DIR, help="Trash destination directory")
    parser.add_argument("--execute", action="store_true", help="Actually move files to trash")
    args = parser.parse_args()

    src_dir = os.path.abspath(args.source)
    trash_dir = os.path.abspath(args.trash)

    if not os.path.isdir(src_dir):
        print(f"ERROR: Source directory does not exist: {src_dir}")
        sys.exit(1)

    print("=" * 60)
    print("Backup Junk Cleaner v2.1")
    print(f"Source: {src_dir}")
    print(f"Trash:  {trash_dir}")
    print(f"Execute mode: {'YES' if args.execute else 'NO (scan only)'}")
    print("=" * 60)

    junk_files = []
    junk_dirs = []
    projects_found = []
    large_archives = []
    ttf_system_fonts = []

    for root, dirs, files in os.walk(src_dir):
        rel_root = os.path.relpath(root, src_dir)
        if rel_root == ".":
            continue

        dirpath = os.path.join(src_dir, rel_root)
        is_proj = is_project_dir(dirpath)

        if is_proj:
            proj_rel = os.path.relpath(dirpath, src_dir)
            projects_found.append(proj_rel)

        for dname in list(dirs):
            dpath = os.path.join(src_dir, rel_root, dname)
            is_junk, category = check_junk_dir(dpath)
            if is_junk:
                junk_dirs.append((os.path.join(rel_root, dname), category))

        for fname in files:
            fpath = os.path.join(src_dir, rel_root, fname)
            is_junk, category = check_junk_file(fpath, dirpath)
            if is_junk:
                junk_files.append((os.path.join(rel_root, fname), category))

            ext = get_file_ext(fname)
            if ext in LARGE_ARCHIVE_EXTS:
                large_archives.append(os.path.join(rel_root, fname))

            if ext == ".ttf" and rel_root in (".", "Art"):
                ttf_system_fonts.append(os.path.join(rel_root, fname))

    dir_dupes = find_directory_duplicates(src_dir)
    file_dupes = find_file_duplicates(src_dir)

    # ---- Print Report ----
    print("\n" + "=" * 60)
    print("SCAN REPORT")
    print("=" * 60)

    print(f"\nJUNK FILES TO MOVE: {len(junk_files)}")
    junk_by_cat = defaultdict(list)
    for fpath, cat in junk_files:
        junk_by_cat[cat].append(fpath)
    for cat, paths in sorted(junk_by_cat.items()):
        print(f"  [{cat}] {len(paths)} files")
        for p in paths[:10]:
            print(f"    - {p}")
        if len(paths) > 10:
            print(f"    ... and {len(paths) - 10} more")

    print(f"\nJUNK DIRECTORIES TO MOVE: {len(junk_dirs)}")
    dir_by_cat = defaultdict(list)
    for dpath, cat in junk_dirs:
        dir_by_cat[cat].append(dpath)
    for cat, paths in sorted(dir_by_cat.items()):
        print(f"  [{cat}] {len(paths)} dirs")
        for p in paths[:10]:
            print(f"    - {p}")
        if len(paths) > 10:
            print(f"    ... and {len(paths) - 10} more")

    print(f"\nPROJECTS DETECTED: {len(projects_found)}")
    for p in sorted(projects_found)[:20]:
        print(f"  - {p}")
    if len(projects_found) > 20:
        print(f"  ... and {len(projects_found) - 20} more")

    if dir_dupes:
        print(f"\nDIRECTORY DUPLICATES (potential): {len(dir_dupes)} groups")
        for key, paths in list(dir_dupes.items())[:10]:
            dirname, fcount, scount = key
            print(f"  [{dirname}] ({fcount} files, {scount} subdirs) - {len(paths)} copies:")
            for p in paths:
                print(f"    - {p}")

    if file_dupes:
        total_extra = 0
        total_waste = 0
        for (digest, fsize), paths in sorted(file_dupes.items()):
            hash_prefix = digest[:12]
            waste = fsize * (len(paths) - 1)
            total_extra += len(paths) - 1
            total_waste += waste
            print(f"\n  [{hash_prefix}] ({human_size(fsize)} each, {len(paths)} copies)")
            for i, p in enumerate(paths):
                marker = "<- KEPT" if i == 0 else "<- DUPLICATE"
                print(f"    * {p} {marker}")

        print(f"\n  FILE DUPLICATES SUMMARY:")
        print(f"    Groups: {len(file_dupes)}")
        print(f"    Extra files: {total_extra}")
        print(f"    Estimated savings: {human_size(total_waste)}")
        print(f"    Read-only: no files deleted based on duplicates")

    if large_archives:
        print(f"\nLARGE ARCHIVES (reported, not moved): {len(large_archives)}")
        for p in sorted(large_archives)[:10]:
            print(f"  - {p}")
        if len(large_archives) > 10:
            print(f"  ... and {len(large_archives) - 10} more")

    if ttf_system_fonts:
        print(f"\nSYSTEM FONTS (flagged for review): {len(ttf_system_fonts)}")
        for p in ttf_system_fonts[:10]:
            print(f"  - {p}")

    # ---- Execute Phase ----
    if args.execute:
        print("\n" + "=" * 60)
        print("EXECUTING: Moving junk files to trash...")
        print("=" * 60)

        os.makedirs(trash_dir, exist_ok=True)
        moved_files = 0
        moved_dirs = 0
        skipped_files = 0
        skipped_dirs = 0
        errors = 0

        for rel_path, category in junk_files:
            src = os.path.join(src_dir, rel_path)
            dst = os.path.join(trash_dir, rel_path)
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):
                    print(f"  SKIP (exists): {rel_path}")
                    skipped_files += 1
                else:
                    shutil.move(src, dst)
                    moved_files += 1
            except PermissionError as e:
                print(f"  ERROR (permission): {rel_path}: {e}")
                errors += 1
            except Exception as e:
                print(f"  ERROR: {rel_path}: {e}")
                errors += 1

        for rel_path, category in sorted(junk_dirs, key=lambda x: -x[0].count(os.sep)):
            src = os.path.join(src_dir, rel_path)
            dst = os.path.join(trash_dir, rel_path)
            try:
                if os.path.exists(dst):
                    print(f"  SKIP (exists): {rel_path}")
                    skipped_dirs += 1
                else:
                    shutil.move(src, dst)
                    moved_dirs += 1
            except Exception as e:
                print(f"  ERROR: {rel_path}: {e}")
                errors += 1

        print("\nCleaning up empty directories...")
        for root, dirs, files in os.walk(src_dir, topdown=False):
            if root == src_dir:
                continue
            try:
                if not os.listdir(root):
                    os.rmdir(root)
            except OSError:
                pass

        print(f"\n{'=' * 60}")
        print("EXECUTION SUMMARY")
        print(f"{'=' * 60}")
        print(f"  Files moved:   {moved_files}")
        print(f"  Dirs moved:    {moved_dirs}")
        print(f"  Files skipped: {skipped_files}")
        print(f"  Dirs skipped:  {skipped_dirs}")
        print(f"  Errors:        {errors}")
        print(f"  Trash location: {trash_dir}")

        if errors > 0:
            print("\nSome operations failed. Check the log above.")
    else:
        print("\n" + "=" * 60)
        print("SCAN COMPLETE - No files were moved.")
        print("To execute, run with --execute flag:")
        print(f"  python {sys.argv[0]} --source \'{src_dir}\' --trash \'{trash_dir}\' --execute")
        print("=" * 60)


if __name__ == "__main__":
    main()
