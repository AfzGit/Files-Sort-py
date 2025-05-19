#!/usr/bin/env python3

import os
import sys
import shutil
import argparse
from pathlib import Path

# Get the extension of a file
# Returns [extensions string] (pdf, exe, no_ext)
def get_extension(filename):
    return filename.suffix[1:].lower() if filename.suffix else "no_ext"
    
def sorted_files(ext_map):
    for ext in sorted(ext_map):  # Sort extensions alphabetically
        print(f"= 📂 {ext}/")
        for fname in sorted(ext_map[ext], key=str.lower):  # Sort files alphabetically (case-insensitive)
            print(f"=   📄 {fname}")

# Count and list unique file extensions in the given directory
# Returns [number of unique extensions], [set of unique extensions]
def count_unique_extensions(directory, recursive):
    directory = Path(directory).expanduser().resolve()
    if not directory.is_dir():
        print(f"❌ Error: {directory} is not a valid directory.")
        sys.exit(1)

    # Use a set to gather unique extensions
    if recursive:
        extensions = {get_extension(f) for f in directory.rglob("*") if f.is_file()}
    else:
        extensions = {get_extension(f) for f in directory.iterdir() if f.is_file()}

    return len(extensions), sorted(extensions)

# Remove empty dirs
# Returns [array of directories to delete]
def remove_empty_dirs(path, dry):
    # 🛣️ Traverse directories from bottom up
    log = []
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        # 📂 If no subdirs and no files, it’s empty
        if not dirnames and not filenames:
            # ❌ Remove the empty directory
            if not dry:
                os.rmdir(dirpath)
            log.append(dirpath)

    return log

# Prompt the user for yes/no confirmation 
def confirm(prompt):
    try:
        return input(f"{prompt} [y/N]: ").strip().lower() == "y"
    except KeyboardInterrupt:
        sys.exit(1)
    except EOFError:
        return False

# for overwriting, accepts A as input
def confirm_A(prompt):
    try:
        response = input(f"{prompt} \n= [y]es | [N]O | [a]ll: ").strip().lower()
        if response in {"y", "a", "n"}:
            return response
        return "n"  # default to "n" on empty or invalid input
    except KeyboardInterrupt:
        sys.exit(1)
    except EOFError:
        return False

# Main function that performs sorting based on extensions
def sort_files(
    directory,
    *,
    copy=False,
    verbose=False,
    dry=False,
    force=False,
    recursive=False,
):
    directory = Path(directory).expanduser().resolve()
    ext_map = {}  # Dictionary to store extension -> list of filenames

    # Counters
    total = 0
    skipped = 0
    processed = 0

    # Check if the directory exists
    if not directory.is_dir():
        print(f"❌ Error: {directory} is not a valid directory.")
        return


    # Gather only files in the given directory
    if not recursive:
        files = [f for f in directory.iterdir() if f.is_file()]
    # Gather files the entire directory recursively
    elif recursive:
        files = [f for f in directory.rglob("*") if f.is_file()]
    if not files:
        print("📂 No files to sort.")
        return

    # sort files by ext (file.a, file.b, ..., file.z)
    files = sorted(files, key=lambda x: x.suffix.lstrip('.').lower())

    # Sample output before running
    print("=== DETAILS ===")
    print(f"= ➡ 📂 Directory: [{directory}]")
    print(f"= ➡ 🎬 Action: {'📝 Copying' if copy else '🚚 Moving'}")

    # Create Dir if it doesn't exists, else skip
    # Sample copy and move files 
    print("=== ACTIONS ===")
    seen_exts = set()
    for file in files:
        ext = get_extension(file)
        ext_dir = directory / ext

        if ext not in seen_exts:
            if ext_dir.exists():
                print(f"= ❌ 📁 [{ext_dir}] (Already exists)")
            else:
                print(f"= ✅ 📁 [{ext_dir}]")
            seen_exts.add(ext)

        print(f"=    ➡ 📄 {file.name}")

    print("=== CONFIRMATION ===")
    if not force:
        if not confirm("= ❓ Proceed?"):
            print("= 🚧 Status: ❌ Stopped")
            print("=== End ===")
            sys.exit(1)
        else:
            print("= 🚧 Status: ✅ Proceed")
            print("=== WORKING ===")

    # Create directories (skip existing)
    for ext in seen_exts:
        ext_dir = directory / ext
        if not ext_dir.exists():
            if not dry:
                ext_dir.mkdir(parents=True, exist_ok=True)
            if verbose:
                print(f"= 📁 Created directory: {ext_dir}")
        else:
            if verbose:
                print(f"= ⏩ Skipping as already exists: [{ext_dir}]")

    # Copy/Move/Dry actions
    overwrite = False
    for file in files:
        total += 1
        ext = get_extension(file)  # "pdf", "exe", "txt"
        target_dir = directory / ext  # Create subfolder like folder/txt
        target_path = target_dir / file.name # folder/file.txt

        # Skip if already in correct target location
        if file.resolve() == target_path.resolve():
            if verbose:
                print(f"= 🔁 Skipping as already sorted: {file.name}")
            skipped += 1
            continue

        # Handle file already existing at target location (if force, then overwrite anyways)
        if target_path.exists() and not force and not overwrite:
            print("=")
            ans = confirm_A(f"= ❓ {target_path} exists. Overwrite?")
            if ans == 'a':
                overwrite = True # Overwrite all files
                print("= ⚔️ Overwritting all files")
            elif ans == 'n' and not overwrite:
                print(f"= ⏩ Skipped: {file.name}")
                skipped += 1
                continue # No overwriting, skip this file

        # Dry-run just prints what *would* happen
        if dry:
            processed += 1
            print(f"= 📄 {"(Dry) copy" if copy else "(Dry) move"}: {file.name} → {ext}/")
        else:
            try:
                processed += 1
                if copy:
                    shutil.copy2(file, target_path)  # Copy file (with metadata)
                    if verbose:
                        print(f"= 📝 Copied: {file.name} → {ext}/")
                else:
                    shutil.move(file, target_path)  # Move file
                    if verbose:
                        print(f"= 🚚 Moved: {file.name} → {ext}/")
            except Exception as e:
                print(f"= ❌ Error: {e}")
                skipped += 1
                continue

        # Track sorted files for summary/logging
        ext_map.setdefault(ext, []).append(file.name)

    if recursive:
        print("=== CLEANUP ===")
        remd_dirs = remove_empty_dirs(directory, dry=True)
        if not remd_dirs:
            print("= No empty dirs found")
            empty = True
        else:
            for dir in remd_dirs:
                print(f"= ⚠ Found empty dir: [{dir}]")
            empty = False

        if not empty:
            if force:
                remove_empty_dirs(directory, dry=False)
            elif confirm("=❓ Remove Empty dirs?"):
                remove_empty_dirs(directory, dry)
                for dir in remd_dirs:
                    print(f"= 🗑 Removed: [{dir}]")
            else:
                print(f"= ❌️ Did not remove empty directories")

    if processed != 0:
        print("=== SORTED FILES ===")
        sorted_files(ext_map)

    print("=== FINAL SUMMARY ===")
    final_summary(total, processed, skipped, directory)
    print("=== END ===")

    return ext_map

# Prints the results of file counters
def final_summary(total, processed, skipped, directory):
    print(f"= 📊 Sorted: {directory}")
    print(f"= ➕ Total files found:     {total}")
    print(f"= 🚚 Files moved/copied:    {processed}")
    print(f"= ⏩ Files skipped:         {skipped}")

def main():
    # get args
    parser = argparse.ArgumentParser(
        description="Sort files into directories based on their extensions.",
        usage="files_sort.py [OPTIONS] DIRECTORY",
    )

    # Directory to operate on (required)
    parser.add_argument("directory", help="Target directory to sort")

    # Flags
    parser.add_argument(
        "-c", "--copy", action="store_true", help="Copy files instead of moving"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="Prevent prompts and proceed with changes, overwrites already existing files without prompt"
    )
    parser.add_argument(
        "-d", "--dry", action="store_true", help="Dry run (simulate actions)"
    )
    parser.add_argument(
        "-u", "--unique", action="store_true", help="Show unique extensions and exit"
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively sort sub-directories as well",
    )
    args = parser.parse_args()

    # Just list unique extensions and exit
    if args.unique:
        ext_len, ext_dict = count_unique_extensions(args.directory, args.recursive)
        print(f"=== 🔢 Unique extensions: {ext_len} ===")
        for i, ext in enumerate(ext_dict, start=1):
            print(f"{i})📄 {ext}")

        print(f"=== END ===")
    else:
        # Run the file sorting function
        sort_files(
            args.directory,
            copy=args.copy,
            verbose=args.verbose,
            dry=args.dry,
            force=args.force,
            recursive=args.recursive,
        )

# Entry point of the script
if __name__ == "__main__":
    main()