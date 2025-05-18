#!/usr/bin/env python3

import os
import sys
import shutil
import argparse
from pathlib import Path

# Get the extension of a file, e.g. "pdf", "exe", or "no_ext" if none.
def get_extension(filename):
    return filename.suffix[1:].lower() if filename.suffix else "no_ext"
    
# Count and list unique file extensions in the given directory
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
def remove_empty_dirs(path, dry):
    # 🛣️ Traverse directories from bottom up
    log = ""
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        # 📂 If no subdirs and no files, it’s empty
        if not dirnames and not filenames:
            # ❌ Remove the empty directory
            if not dry:
                os.rmdir(dirpath)
            log += [{dirpath}]

    return log

# Prompt the user for yes/no confirmation (used in interactive mode)
def confirm(prompt):
    try:
        return input(f"{prompt} [y/N]: ").strip().lower() == "y"
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
    interactive=False,
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

    # 'Force' and 'Interactive' are not to be used together
    if force and interactive:
        print("Force and interactive are not compatible with each other. Exiting...")
        sys.exit(1)

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
    sorted(files, key=lambda x: x.suffix.lstrip('.'))

    # Sample output before running
    print(f"--- 📂 Operating inside [{directory}] 📂 ---")
    seen_exts = set()
    for file in files:
        ext = get_extension(file)  # e.g., "pdf", "exe", "txt"
        if ext not in seen_exts:
            target_dir = directory / ext
            print(f"📁 Create directory: [{target_dir}]")
            seen_exts.add(ext)
        else:
            print(f"⏩ Skipping {ext_dir}, folder already exists")
        
    for file in files:
        ext = get_extension(file)  # "pdf", "exe", "txt"
        target_dir = directory / ext  # "folder/txt"
        
        # Create Dir if it doesn't exists and move/copy files
        if not target_dir.exists():
            print(f"📁 Create directory: [{target_dir}]")
        print(f"    📄 {'Copy' if copy else 'Move'}: {file.name} → {ext}/")

    # Confirm before running unless -f
    if not force:
        if not confirm("Proceed?"):
            sys.exit(1)
            
    # Create directories
    for file in files:
        ext = get_extension(file)
        if ext not in seen_exts:
            ext_dir = directory / ext
            if not ext_dir.exists():
                ext_dir.mkdir(exist_ok=True)
                print(f"📁 Created directory: {ext_dir}")
            else:
                print(f"⏩ Skipping {ext_dir}, folder already exists")
    # Copy/Move/Dry actions
    for file in files:
        total += 1
        ext = get_extension(file)  # "pdf", "exe", "txt"
        target_dir = directory / ext  # Create subfolder like folder/txt
        target_path = target_dir / file.name # folder/file.txt

        # Handle file already existing at target location (if force, then overwrite anyways)
        if target_path.exists() and not force:
            # Ask for overwrite
            if interactive and not confirm(f"❓ {target_path} exists. Overwrite?"):
                print(f"    ⏩ Skipped: {file.name}")
                skipped += 1
                continue # no overwriting, skip this file

        # Dry-run just prints what *would* happen
        if dry:
            processed += 1
            print(f"    📄 {"(Dry) copy" if copy else "(Dry) move"}: {file.name} → {ext}/")
        else:
            try:
                processed += 1
                if copy:
                    shutil.copy2(file, target_path)  # Copy file (with metadata)
                    if verbose:
                        print(f"    📄 Copied: {file.name} → {ext}/")
                else:
                    shutil.move(file, target_path)  # Move file
                    if verbose:
                        print(f"    📄 Moved: {file.name} → {ext}/")
            except Exception as e:
                print(f"❌ Error: {e}")
                skipped += 1
                continue

        # Track sorted files for summary/logging
        ext_map.setdefault(ext, []).append(file.name)

    if recursive:
        remd_dirs = ""
        if force:
            remd_dirs = remove_empty_dirs(directory, dry=False)
        elif confirm("❓ Remove Empty dirs?"):
            remd_dirs = remove_empty_dirs(directory, dry)
        for dir in remd_dirs:
            print(f"🗑️ Removed: {dir}")

    print("Sorted directory:")
    for item in os.listdir(directory):
        print(f"- {item}")
    final_summary(total, processed, skipped, directory)

    return ext_map

def final_summary(total, processed, skipped, directory):
    print(f"\n📊 Summary: {directory}")
    print(f"   Total files found:     {total}")
    print(f"   Files moved/copied:    {processed}")
    print(f"   Files skipped:         {skipped}")


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
        "-i", "--interactive", action="store_true", help="Prompt before overwriting"
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
        print(f"🔢 Unique extensions: {ext_len}")
        for ext in ext_dict:
            print(f" - {ext}")
    else:
        # Run the file sorting function
        sort_files(
            args.directory,
            copy=args.copy,
            verbose=args.verbose,
            dry=args.dry,
            force=args.force,
            interactive=args.interactive,
            recursive=args.recursive,
        )


# Entry point of the script
if __name__ == "__main__":
    main()
