#!/usr/bin/env python3
"""
Backup Junk Cleaner — Project-Aware (Safe Mode)

Scans a backup directory for junk files while preserving software projects.
In safe mode, .obj 3D model files are excluded from project junk.

Junk files are moved to a trash directory mirroring the original structure.
No data is ever overwritten; conflicts are logged and skipped.

Stdlib-only — zero external dependencies.
"""

import argparse
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_SOURCE_DIR = "/home/cc/Documents/Backup novo"
DEFAULT_TRASH_DIR = "/home/cc/Documents/Trash"
MAX_WEB_SIZE_BYTES = 50 * 1024  # 50 KB threshold for web formats
PROJECT_DEPTH_LIMIT = 5

# Project detection requires BOTH: a marker file + source code within depth limit
PROJECT_MARKERS = {
    ".sln", "CMakeLists.txt", "pom.xml", "vcxproj", "project.pbxproj",
    "package.json", "go.mod", "Cargo.toml", "build.gradle", "Makefile",
    "setup.py", "setup.cfg", "pyproject.toml",
    "requirements.txt", "Gemfile", "composer.json", "pubspec.yaml",
    ".git", "package-lock.json", "yarn.lock", "Podfile", "Rakefile",
    "Justfile", "SConstruct", "meson.build", "BUILD", "WORKSPACE",
}

SOURCE_CODE_EXTS = {
    ".c", ".cpp", ".h", ".hpp", ".cs", ".java", ".kt", ".py", ".pyx",
    ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".swift", ".dart",
    ".lua", ".rb", ".php", ".sql", ".sh", ".cmake", ".pro",
}

# Junk categories — General (applied to all files outside projects)
GENERAL_JUNK_NAMES = {
    "desktop.ini", ".ds_store", ".metadata", "thumbs.db",
}

GENERAL_JUNK_EXTS = {
    # Thumbnails
    ".thumb", ".thumbnail",
    # Configs
    ".ini", ".cfg", ".conf", ".env", ".yaml", ".yml", ".toml", ".json",
    ".xml", ".properties", ".plist",
    # Installers
    ".exe", ".msi", ".dmg", ".deb", ".rpm", ".pkg", ".bat", ".cmd",
}

# Web name patterns for junk detection (under size threshold)
WEB_FORMATS = {
    ".html", ".htm", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".ico", ".pdf", ".txt",
}

WEB_NAME_RE = re.compile(
    r"^(download|untitled|image|screenshot|temp|img\d{3}|pic\d{3}|"
    r"photo|picture|snapshot|capture|clipboard|screen)"
    r"[_.\-\d]*$",
    re.IGNORECASE,
)

# Junk categories — Project junk (applied only inside detected projects)
PROJECT_JUNK_DIRS = {
    "bin", "obj", "build", "dist", "target", "out", "release", "debug",
    "static", "output", "generated", ".vs", ".idea", ".clion",
    "__pycache__", ".tox", ".pytest_cache", ".gradle", ".cache",
    "node_modules", "venv",
}

# NOTE: .obj (3D models) excluded — these are legitimate project assets, not build outputs
PROJECT_JUNK_EXTS = {
    ".dll", ".so", ".a", ".lib", ".dylib", ".exe", ".bin", ".out",
    ".class", ".wasm", ".jar", ".war", ".o", ".pyc", ".pyo",
    ".ilk", ".pdb", ".exp", ".tmp", ".bak",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _relpath(filepath, source_dir):
    return os.path.relpath(filepath, source_dir)


def _dir_depth(path, source_dir):
    rel = os.path.relpath(path, source_dir)
    if rel == ".":
        return 0
    return rel.count(os.sep) + 1


def _has_source_files(dirpath, source_dir, max_depth=None):
    if max_depth is None:
        max_depth = PROJECT_DEPTH_LIMIT
    current_depth = _dir_depth(dirpath, source_dir)
    for root, dirs, files in os.walk(dirpath):
        depth = _dir_depth(root, source_dir)
        if depth - current_depth >= max_depth:
            dirs.clear()
            continue
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SOURCE_CODE_EXTS:
                return True
    return False


def _is_project_marker_at(path, source_dir):
    parent_dir = os.path.dirname(path)
    for entry in os.listdir(parent_dir):
        if entry in PROJECT_MARKERS:
            return True
    return False


def _is_inside_project(filepath, source_dir):
    rel = os.path.relpath(filepath, source_dir)
    parts = Path(rel).parts
    for i in range(1, len(parts)):
        candidate = os.path.join(*parts[:i])
        candidate_path = os.path.join(source_dir, candidate)
        if not os.path.isdir(candidate_path):
            continue
        try:
            entries = os.listdir(candidate_path)
        except OSError:
            continue
        if any(entry in PROJECT_MARKERS for entry in entries):
            if _has_source_files(candidate_path, source_dir, PROJECT_DEPTH_LIMIT - i):
                return True
    return False


def _is_general_junk(filepath):
    basename = os.path.basename(filepath)
    ext = os.path.splitext(basename)[1].lower()
    name_no_ext = os.path.splitext(basename)[0]

    if basename.lower() in GENERAL_JUNK_NAMES:
        return True, "general_name"

    if ext and ext not in SOURCE_CODE_EXTS:
        if ext in GENERAL_JUNK_EXTS:
            return True, "general_ext"

    if ext in WEB_FORMATS:
        try:
            size = os.path.getsize(filepath)
        except OSError:
            size = 0
        if size <= MAX_WEB_SIZE_BYTES and WEB_NAME_RE.match(name_no_ext):
            return True, "web_junk"

    return False, None


def _is_project_junk(filepath):
    basename = os.path.basename(filepath)
    ext = os.path.splitext(basename)[1].lower()

    if basename in PROJECT_JUNK_DIRS:
        return True, "project_dir"

    if ext and ext in PROJECT_JUNK_EXTS:
        return True, "project_ext"

    return False, None


# ─── Main Logic ──────────────────────────────────────────────────────────────

def classify_file(filepath, source_dir):
    if _is_inside_project(filepath, source_dir):
        junk, cat = _is_project_junk(filepath)
        if junk:
            return True, f"project_{cat}"
        junk_general, cat_gen = _is_general_junk(filepath)
        if junk_general:
            return True, f"general_{cat_gen}"
    else:
        junk, cat = _is_general_junk(filepath)
        if junk:
            return True, cat

    return False, None


def scan_and_classify(source_dir):
    results = defaultdict(list)
    errors = []
    total_files = 0

    for root, dirs, files in os.walk(source_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            total_files += 1
            try:
                junk, cat = classify_file(fpath, source_dir)
                if junk:
                    results[cat].append(_relpath(fpath, source_dir))
            except PermissionError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"{fpath}: {e}")

    return results, total_files, errors


def run_dry_run(source_dir, trash_dir):
    print("=" * 70)
    print("BACKUP JUNK CLEANER — DRY RUN (Safe Mode)")
    print(f"Source: {source_dir}")
    print(f"Trash:  {trash_dir}")
    print(f"Note:   .obj 3D models preserved as project assets")
    print("=" * 70)

    results, total_files, errors = scan_and_classify(source_dir)

    if not results:
        print("\nNo junk files found. Nothing to clean.")
        return

    grand_total = sum(len(v) for v in results.values())
    print(f"\nScanned {total_files} files total.")
    print(f"Found {grand_total} potential junk files.\n")

    for cat in sorted(results.keys()):
        items = sorted(results[cat])
        print(f"--- [{cat}] ({len(items)} files) ---")
        for item in items:
            print(f"  {item}")
        print()

    if errors:
        print(f"\n⚠️  Encountered {len(errors)} errors:")
        for e in errors[:20]:
            print(f"  {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")

    print("=" * 70)
    print("No files were moved (dry run).")
    print("To execute, re-run with --execute flag.")
    print("=" * 70)


def run_execute(source_dir, trash_dir):
    print("=" * 70)
    print("BACKUP JUNK CLEANER — EXECUTE MODE (Safe Mode)")
    print(f"Source: {source_dir}")
    print(f"Trash:  {trash_dir}")
    print(f"Note:   .obj 3D models preserved as project assets")
    print("=" * 70)

    results, total_files, errors = scan_and_classify(source_dir)

    if not results:
        print("\nNo junk files found. Nothing to clean.")
        return

    grand_total = sum(len(v) for v in results.values())
    moved = 0
    skipped = 0

    os.makedirs(trash_dir, exist_ok=True)

    for cat in sorted(results.keys()):
        items = sorted(results[cat])
        print(f"\n--- [{cat}] ({len(items)} files) ---")
        for item in items:
            src = os.path.join(source_dir, item)
            dst = os.path.join(trash_dir, item)

            if not os.path.exists(src):
                print(f"  [MISSING] {item}")
                continue

            try:
                if os.path.exists(dst):
                    print(f"  [SKIP] {item} — already in trash")
                    skipped += 1
                    continue
                shutil.move(src, dst)
                print(f"  [MOVED] {item}")
                moved += 1
            except PermissionError as e:
                print(f"  [ERROR] {item}: permission denied")
                errors.append(str(e))
            except Exception as e:
                print(f"  [ERROR] {item}: {e}")
                errors.append(f"{item}: {e}")

    # Remove empty directories left behind (reverse walk)
    print("\n--- Cleaning up empty directories ---")
    removed_dirs = 0
    for root, dirs, files in os.walk(source_dir, topdown=False):
        if root == source_dir:
            continue
        try:
            if not os.listdir(root):
                os.rmdir(root)
                rel = _relpath(root, source_dir)
                print(f"  [RMDIR] {rel}")
                removed_dirs += 1
        except OSError:
            pass

    print(f"\n{'=' * 70}")
    print(f"Done. Moved: {moved}, Skipped: {skipped}, Empty dirs removed: {removed_dirs}")
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors[:10]:
            print(f"  {e}")
    print(f"Trash location: {trash_dir}")
    print(f"{'=' * 70}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Backup Junk Cleaner — Project-Aware (Safe Mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source", default=DEFAULT_SOURCE_DIR,
        help=f"Source backup directory (default: {DEFAULT_SOURCE_DIR})"
    )
    parser.add_argument(
        "--trash", default=DEFAULT_TRASH_DIR,
        help=f"Trash destination (default: {DEFAULT_TRASH_DIR})"
    )
    parser.add_argument("--execute", action="store_true",
                        help="Actually move files (default: dry run)")

    args = parser.parse_args()

    source_dir = os.path.abspath(args.source)
    trash_dir = os.path.abspath(args.trash)

    if not os.path.isdir(source_dir):
        print(f"Error: Source directory does not exist: {source_dir}", file=sys.stderr)
        sys.exit(1)

    if args.execute:
        run_execute(source_dir, trash_dir)
    else:
        run_dry_run(source_dir, trash_dir)


if __name__ == "__main__":
    main()
