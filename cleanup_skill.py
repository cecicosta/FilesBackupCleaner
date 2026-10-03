#!/usr/bin/env python3
"""Backup Junk Cleaner v2.2 - Project-Aware, IDE-Junk-Specific + Full Duplicate Handling"""

import os
import sys
import re
import shutil
import hashlib
import stat
from datetime import datetime
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
DUP_DIRS_VERIFY_CONTENT = True
DUP_DIRS_HASH_ALGO = "md5"
PROJECT_DUP_THRESHOLD = 0.50  # Minimum similarity to flag project duplicates

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
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def get_hash(filepath, algorithm="md5"):
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(DUP_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def get_project_fingerprint(dirpath):
    """Compute three-layer fingerprint for a project directory.
    
    Layer 1: Root structure (Jaccard similarity on base names)
    Layer 2: Extension distribution (cosine similarity)
    Layer 3: Identity signals (marker-derived name, language signature, marker types)
    """
    try:
        entries = os.listdir(dirpath)
    except PermissionError:
        return None
    
    # Layer 1: Root structure - base names of files and dirs at project root
    root_base_names = set()
    for name in entries:
        if os.path.isfile(os.path.join(dirpath, name)):
            base = os.path.splitext(name)[0]
            root_base_names.add(base)
        elif os.path.isdir(os.path.join(dirpath, name)):
            root_base_names.add(name)
    
    # Layer 2: Extension distribution at project root
    ext_counts = defaultdict(int)
    total_files = 0
    for name in entries:
        fpath = os.path.join(dirpath, name)
        if os.path.isfile(fpath):
            _, ext = os.path.splitext(name)
            ext = ext.lower()
            if ext:
                ext_counts[ext] += 1
                total_files += 1
    
    # Normalize to percentages
    ext_dist = {}
    if total_files > 0:
        for ext, count in ext_counts.items():
            ext_dist[ext] = count / total_files
    
    # Layer 3: Identity signals
    identity = {
        'name': None,
        'languages': set(),
        'markers': set()
    }
    
    # Extract project name from marker files
    for marker in ['package.json', 'Cargo.toml', 'setup.py', 'setup.cfg', 
                   'pyproject.toml', 'CMakeLists.txt', 'pom.xml']:
        marker_path = os.path.join(dirpath, marker)
        if os.path.isfile(marker_path):
            try:
                with open(marker_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Try to extract name from JSON
                    if marker == 'package.json':
                        import json
                        try:
                            data = json.loads(content)
                            identity['name'] = data.get('name', None)
                        except json.JSONDecodeError:
                            pass
                    # For TOML, look for name = ...
                    elif marker in ['Cargo.toml', 'setup.cfg', 'pyproject.toml']:
                        for line in content.split('\n'):
                            if '=' in line and 'name' in line.lower():
                                parts = line.split('=')
                                if len(parts) >= 2:
                                    val = parts[-1].strip().strip('"').strip("'")
                                    if val and not identity['name']:
                                        identity['name'] = val
                    break
            except (PermissionError, OSError):
                pass
    
    # If no name found in markers, use directory name
    if not identity['name']:
        identity['name'] = os.path.basename(dirpath)
    
    # Language signature - check for source files at root
    for name in entries:
        fpath = os.path.join(dirpath, name)
        if os.path.isfile(fpath):
            _, ext = os.path.splitext(name)
            if ext in SOURCE_CODE_EXTS:
                identity['languages'].add(ext)
    
    # Marker types present
    for marker in PROJECT_MARKERS:
        if marker in entries or (marker == '.git' and '.git' in entries):
            identity['markers'].add(marker)
    
    return {
        'layer1': root_base_names,
        'layer2': ext_dist,
        'layer3': identity
    }


def compute_project_similarity(fp_a, fp_b):
    """Compute similarity between two project fingerprints (0.0 to 1.0)."""
    if not fp_a or not fp_b:
        return 0.0
    
    # Layer 1: Jaccard similarity of root base names
    set_a = fp_a['layer1']
    set_b = fp_b['layer1']
    if len(set_a) == 0 and len(set_b) == 0:
        layer1_sim = 1.0
    else:
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        layer1_sim = intersection / union if union > 0 else 0.0
    
    # Layer 2: Cosine similarity of extension distributions
    ext_a = fp_a['layer2']
    ext_b = fp_b['layer2']
    all_exts = set(ext_a.keys()) | set(ext_b.keys())
    if len(all_exts) == 0:
        layer2_sim = 1.0
    else:
        dot_product = sum(ext_a.get(ext, 0) * ext_b.get(ext, 0) for ext in all_exts)
        mag_a = (sum(v**2 for v in ext_a.values())) ** 0.5
        mag_b = (sum(v**2 for v in ext_b.values())) ** 0.5
        if mag_a == 0 or mag_b == 0:
            layer2_sim = 0.0
        else:
            layer2_sim = dot_product / (mag_a * mag_b)
    
    # Layer 3: Identity signals
    id_a = fp_a['layer3']
    id_b = fp_b['layer3']
    
    name_match = 1.0 if id_a['name'] and id_b['name'] and id_a['name'].lower() == id_b['name'].lower() else 0.0
    lang_intersection = len(id_a['languages'] & id_b['languages'])
    lang_union = len(id_a['languages'] | id_b['languages'])
    lang_sim = lang_intersection / lang_union if lang_union > 0 else (1.0 if not id_a['languages'] and not id_b['languages'] else 0.0)
    marker_intersection = len(id_a['markers'] & id_b['markers'])
    marker_union = len(id_a['markers'] | id_b['markers'])
    marker_sim = marker_intersection / marker_union if marker_union > 0 else (1.0 if not id_a['markers'] and not id_b['markers'] else 0.0)
    
    layer3_sim = (name_match * 0.5) + (lang_sim * 0.25) + (marker_sim * 0.25)
    
    # Weighted combination
    similarity = (layer1_sim * 0.35) + (layer2_sim * 0.30) + (layer3_sim * 0.35)
    return similarity


def find_project_duplicates(projects_info):
    """Find duplicate projects using three-layer fingerprint.
    
    Args:
        projects_info: dict mapping project_rel_path -> {'fingerprint': fp, 'mtime': timestamp}
    
    Returns:
        List of groups, each group is a list of (path, mtime, similarity) tuples
    """
    if len(projects_info) < 2:
        return []
    
    project_pairs = []
    paths = list(projects_info.keys())
    
    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            path_a = paths[i]
            path_b = paths[j]
            fp_a = projects_info[path_a]['fingerprint']
            fp_b = projects_info[path_b]['fingerprint']
            
            similarity = compute_project_similarity(fp_a, fp_b)
            if similarity >= PROJECT_DUP_THRESHOLD:
                project_pairs.append((path_a, path_b, similarity))
    
    # Group related projects
    groups = []
    visited = set()
    
    for path_a, path_b, sim in sorted(project_pairs, key=lambda x: -x[2]):
        if path_a in visited and path_b in visited:
            continue
        
        group = [path_a, path_b]
        visited.add(path_a)
        visited.add(path_b)
        
        # Check for transitive matches
        for path_c in paths:
            if path_c in visited:
                continue
            fp_c = projects_info[path_c]['fingerprint']
            fp_a = projects_info[path_a]['fingerprint']
            sim_ac = compute_project_similarity(fp_a, fp_c)
            if sim_ac >= PROJECT_DUP_THRESHOLD:
                group.append(path_c)
                visited.add(path_c)
        
        # Sort by last modified time (oldest first)
        group.sort(key=lambda p: projects_info[p]['mtime'])
        groups.append(group)
    
    return groups


def is_project_dir(dirpath):
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
    return dirname.startswith("blendcache_")


def get_file_ext(filepath):
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
    dirname = os.path.basename(dirpath)
    if not dirname:
        return False, None
    if is_project_dir(os.path.dirname(dirpath)):
        if dirname.lower() in PROJECT_JUNK_DIRS or is_blendcache_dir(dirname):
            return True, "project_build_dir"
    if is_blendcache_dir(dirname):
        return True, "blendcache_dir"
    return False, None


def find_directory_duplicates(source_root, projects_set):
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


def get_dir_hash(dirpath):
    """Hash all files in a directory to verify identity."""
    file_hashes = []
    try:
        for root, dirs, files in os.walk(dirpath):
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                try:
                    h = get_hash(fpath, DUP_DIRS_HASH_ALGO)
                    rel = os.path.relpath(fpath, dirpath)
                    file_hashes.append((rel, h))
                except OSError:
                    pass
    except OSError:
        return None
    return tuple(file_hashes)


def find_file_duplicates(source_root):
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


def is_path_under_project(rel_path, projects_set):
    """Check if a relative path falls under any detected project."""
    parts = Path(rel_path).parts
    for i in range(len(parts)):
        partial = os.path.join(*parts[:i+1])
        if partial in projects_set:
            return True
    # Also check parent directories
    for proj in projects_set:
        if rel_path.startswith(proj + os.sep):
            return True
    return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backup Junk Cleaner v2.2")
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
    print("Backup Junk Cleaner v2.2")
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

    projects_set = set(projects_found)
    
    # v2.3: Compute fingerprints and find project duplicates
    print("\nComputing project fingerprints...")
    projects_info = {}
    for idx, proj_rel in enumerate(projects_found):
        proj_path = os.path.join(src_dir, proj_rel)
        fp = get_project_fingerprint(proj_path)
        if fp:
            mtime = os.path.getmtime(proj_path)
            projects_info[proj_rel] = {'fingerprint': fp, 'mtime': mtime}
            if (idx + 1) % 10 == 0:
                print(f"  Processed {idx + 1}/{len(projects_found)} projects...")
    
    print(f"  Fingerprinted {len(projects_info)} projects")
    project_dup_groups = find_project_duplicates(projects_info)
    
    dir_dupes = find_directory_duplicates(src_dir, projects_set)
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

    # v2.3: Project duplicates with fingerprint detection
    if project_dup_groups:
        print(f"\nPROJECT DUPLICATES (v2.3 fingerprint): {len(project_dup_groups)} groups")
        print("  NOTE: Projects are NEVER auto-deleted — only reported, ordered by last modified.")
        for group in project_dup_groups:
            if len(group) >= 2:
                # Compute average similarity within group
                sims = []
                for i in range(len(group)):
                    for j in range(i+1, len(group)):
                        fp_a = projects_info[group[i]]['fingerprint']
                        fp_b = projects_info[group[j]]['fingerprint']
                        sim = compute_project_similarity(fp_a, fp_b)
                        sims.append(sim)
                avg_sim = sum(sims) / len(sims) if sims else 0.0
                
                print(f"\n  Group (similarity: {avg_sim:.0%})")
                for idx, path in enumerate(group):
                    mtime = projects_info[path]['mtime']
                    mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
                    marker = "<- OLDEST" if idx == 0 else (f"<- newer copy ({idx} copies ahead)")
                    print(f"    * {path}")
                    print(f"      Modified: {mod_time} {marker}")
        
        total_project_dupes = sum(len(g) - 1 for g in project_dup_groups)
        print(f"\n  PROJECT DUPLICATES SUMMARY:")
        print(f"    Groups: {len(project_dup_groups)}")
        print(f"    Extra projects (not deleted): {total_project_dupes}")
        print(f"    Action: None — projects are never auto-deleted")

    # Directory duplicates with v2.2 strategy
    if dir_dupes:
        print(f"\nDIRECTORY DUPLICATES (v2.2 strategy): {len(dir_dupes)} groups")
        project_kept = 0
        non_project_moved = 0
        for key, paths in list(dir_dupes.items())[:15]:
            dirname, fcount, scount = key
            has_project = any(is_path_under_project(p, projects_set) for p in paths)
            print(f"\n  [{dirname}] ({fcount} files, {scount} subdirs) - {len(paths)} copies")
            if has_project:
                print(f"    -> STRATEGY: Under project - KEEP ALL as READ-ONLY")
                for i, p in enumerate(paths):
                    marker = "<- KEPT (project dir)" if i == 0 else "<- READ-ONLY (chmod 555)"
                    print(f"      * {p} {marker}")
                project_kept += len(paths)
            else:
                print(f"    -> STRATEGY: Not under project - MOVE duplicates to trash")
                for i, p in enumerate(paths):
                    marker = "<- KEPT" if i == 0 else "<- DUPLICATE (moved to trash)"
                    print(f"      * {p} {marker}")
                non_project_moved += len(paths) - 1

        if len(dir_dupes) > 15:
            remaining = len(dir_dupes) - 15
            print(f"\n  ... and {remaining} more duplicate groups (same strategy applied)")

    # File duplicates with v2.2 strategy
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
                marker = "<- KEPT (stays in place)" if i == 0 else "<- DUPLICATE (moved to trash on --execute)"
                print(f"    * {p} {marker}")

        print(f"\n  FILE DUPLICATES SUMMARY:")
        print(f"    Groups: {len(file_dupes)}")
        print(f"    Extra files (moved to trash): {total_extra}")
        print(f"    Estimated savings: {human_size(total_waste)}")

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
        print("EXECUTING...")
        print("=" * 60)

        os.makedirs(trash_dir, exist_ok=True)
        moved_files = 0
        moved_dirs = 0
        skipped_files = 0
        skipped_dirs = 0
        errors = 0
        dup_files_moved = 0
        dup_dirs_moved = 0
        read_only_dirs = 0

        # 1. Move junk files
        print("\n[1/5] Moving junk files...")
        for rel_path, category in junk_files:
            src = os.path.join(src_dir, rel_path)
            dst = os.path.join(trash_dir, rel_path)
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):
                    skipped_files += 1
                else:
                    shutil.move(src, dst)
                    moved_files += 1
            except Exception as e:
                errors += 1

        # 2. Move junk directories (deepest first)
        print("[2/5] Moving junk directories...")
        for rel_path, category in sorted(junk_dirs, key=lambda x: -x[0].count(os.sep)):
            src = os.path.join(src_dir, rel_path)
            dst = os.path.join(trash_dir, rel_path)
            try:
                if os.path.exists(dst):
                    skipped_dirs += 1
                else:
                    shutil.move(src, dst)
                    moved_dirs += 1
            except Exception as e:
                errors += 1

        # 3. Move duplicate files (v2.2 feature)
        print("[3/5] Moving duplicate files to trash...")
        for (digest, fsize), paths in file_dupes.items():
            # First is KEPT, rest are moved
            for fpath in paths[1:]:
                rel = os.path.relpath(fpath, src_dir)
                dst = os.path.join(trash_dir, rel)
                try:
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    if not os.path.exists(dst):
                        shutil.move(fpath, dst)
                        dup_files_moved += 1
                    else:
                        skipped_files += 1
                except Exception as e:
                    errors += 1

        # 4. Handle duplicate directories (v2.2 feature)
        print("[4/5] Handling duplicate directories...")
        for key, paths in dir_dupes.items():
            dirname, fcount, scount = key
            has_project = any(is_path_under_project(p, projects_set) for p in paths)

            if has_project:
                # Mark all as read-only
                for rel_path in paths:
                    full_path = os.path.join(src_dir, rel_path)
                    try:
                        os.chmod(full_path, 0o555)  # r-x for owner, group, other
                        read_only_dirs += 1
                    except Exception as e:
                        print(f"  Warning: Could not set read-only on {rel_path}: {e}")
            else:
                # Move duplicates (keep first alphabetically)
                sorted_paths = sorted(paths)
                for rel_path in sorted_paths[1:]:
                    src = os.path.join(src_dir, rel_path)
                    dst = os.path.join(trash_dir, rel_path)
                    try:
                        if os.path.exists(dst):
                            skipped_dirs += 1
                        else:
                            shutil.move(src, dst)
                            dup_dirs_moved += 1
                    except Exception as e:
                        errors += 1

        # 5. Clean up empty directories
        print("[5/5] Cleaning up empty directories...")
        for root, dirs, files in os.walk(src_dir, topdown=False):
            if root == src_dir:
                continue
            try:
                if not os.listdir(root):
                    os.rmdir(root)
            except OSError:
                pass

        # Summary
        print(f"\n{'=' * 60}")
        print("EXECUTION SUMMARY")
        print(f"{'=' * 60}")
        print(f"  Junk files moved:    {moved_files}")
        print(f"  Junk dirs moved:     {moved_dirs}")
        print(f"  Duplicate files moved: {dup_files_moved} (v2.2 feature)")
        print(f"  Duplicate dirs moved:  {dup_dirs_moved} (v2.2 feature)")
        print(f"  Dirs kept read-only:   {read_only_dirs} (project dirs, v2.2 feature)")
        print(f"  Files skipped:         {skipped_files}")
        print(f"  Dirs skipped:          {skipped_dirs}")
        print(f"  Errors:                {errors}")
        print(f"  Trash location:        {trash_dir}")

        if errors > 0:
            print("\nSome operations failed. Check the log above.")
    else:
        print("\n" + "=" * 60)
        print("SCAN COMPLETE - No files were moved.")
        print("To execute, run with --execute flag:")
        print(f"  python {sys.argv[0]} --source '{src_dir}' --trash '{trash_dir}' --execute")
        print("=" * 60)


if __name__ == "__main__":
    main()
