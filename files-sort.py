#!/usr/bin/env python3

import os
import shutil
import argparse
from pathlib import Path


# Get the extension of a file, e.g. "pdf", "exe", or "no_ext" if none.
def get_extension(filename):
    return filename.suffix[1:].lower() if filename.suffix else "no_ext"


# Remove empty dirs
def remove_empty_dirs(path):
    # 🛣️ Traverse directories from bottom up
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        # 📂 If no subdirs and no files, it’s empty
        if not dirnames and not filenames:
            # ❌ Remove the empty directory
            os.rmdir(dirpath)


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

    # Check if the directory exists
    if not directory.is_dir():
        print(f"❌ Error: {directory} is not a valid directory.")
        return

    # 'Force' and 'Interactive' are not to be used together
    if force and interactive:
        print("Force and interactive are not compatible with each other. Exiting...")
        return

    # Gather only files in the given directory
    if not recursive:
        files = [f for f in directory.iterdir() if f.is_file()]
        if not files:
            print("📂 No files to sort.")
            return
    # Gather files the entire directory recursively
    elif recursive:
        files = [f for f in directory.rglob("*") if f.is_file()]

    for file in files:
        ext = get_extension(file)  # e.g., "pdf", "exe", "txt"
        target_dir = directory / ext  # Create subfolder like folder/txt
        target_path = target_dir / file.name # folder/file.txt

        # Handle file already existing at target location (if force, then overwrite anyways)
        if target_path.exists() and not force:
            # Ask for overwrite
            if not confirm(f"❓ {target_path} exists. Overwrite?"):
                print(f"    ⏩ Skipped: {file.name}")
                continue # no overwriting, skip this file

        # Ask before copying/moving each file
        if interactive:
            if not confirm(f"{"Copy" if copy else "Move"} {file.name} to {target_dir}?"):
                continue

        # Dry-run just prints what *would* happen
        if dry:
            print(f"📄 {"(Dry) copy" if copy else "(Dry) move"}: {file.name} → {ext}/")
        else:
            try:
                if not target_dir.exists():
                    target_dir.mkdir(exist_ok=True)
                    print(f"📁 Created directory: {target_dir}")
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
                continue

        # Track sorted files for summary/logging
        # ext_map.setdefault(ext, []).append(file.name)

    if recursive:
        if force:
            remove_empty_dirs(directory)
        elif confirm("Remove Empty dirs?"):
            if not dry:
                remove_empty_dirs(directory)
            if verbose or dry:
                print(f"Removed empty directory: {directory}")

    return ext_map

# Count and list unique file extensions in the given directory
def count_unique_extensions(directory):
    directory = Path(directory).expanduser().resolve()
    if not directory.is_dir():
        print(f"❌ Error: {directory} is not a valid directory.")
        return

    # Use a set to gather unique extensions
    extensions = {get_extension(f) for f in directory.iterdir() if f.is_file()}
    print(f"🔢 Unique extensions: {len(extensions)}")
    for ext in sorted(extensions):
        print(f" - {ext}")

# Argument parser and CLI logic
def main():
    parser = argparse.ArgumentParser(
        description="Sort files into directories based on their extensions.",
        usage="files_sort.py [OPTIONS] DIRECTORY",
    )

    # Directory to operate on (required)
    parser.add_argument("directory", help="Target directory to sort")

    # Optional flags
    parser.add_argument(
        "-c", "--copy", action="store_true", help="Copy files instead of moving"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Prompt before actions"
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
        count_unique_extensions(args.directory)
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
