#!/usr/bin/env python3

import os
import shutil
import argparse
from pathlib import Path


def get_extension(filename):
    return filename.suffix[1:].lower() if filename.suffix else "no_ext"


def confirm(prompt):
    try:
        return input(f"{prompt} [y/N]: ").strip().lower() == "y"
    except EOFError:
        return False


def sort_files(
    directory, *, copy=False, verbose=False, dry=False, force=False, interactive=False
):
    directory = Path(directory).expanduser().resolve()
    if not directory.is_dir():
        print(f"❌ Error: {directory} is not a valid directory.")
        return

    files = [f for f in directory.iterdir() if f.is_file()]
    if not files:
        print("📂 No files to sort.")
        return

    ext_map = {}

    for file in files:
        ext = get_extension(file)
        target_dir = directory / ext
        target_dir.mkdir(exist_ok=True)

        target_path = target_dir / file.name
        if target_path.exists() and not force:
            if interactive:
                if not confirm(f"❓ {target_path} exists. Overwrite?"):
                    if verbose:
                        print(f"⏩ Skipped: {file.name}")
                    continue
            else:
                if verbose:
                    print(f"⚠️  Exists: {target_path}, use -f to overwrite.")
                continue

        if dry:
            action = "Would copy" if copy else "Would move"
        else:
            try:
                if copy:
                    shutil.copy2(file, target_path)
                    action = "Copied"
                else:
                    shutil.move(file, target_path)
                    action = "Moved"
            except Exception as e:
                print(f"❌ Error: {e}")
                continue

        if verbose:
            print(f"✅ {action}: {file.name} → {ext}/")

        ext_map.setdefault(ext, []).append(file.name)

    return ext_map


def count_unique_extensions(directory):
    directory = Path(directory).expanduser().resolve()
    if not directory.is_dir():
        print(f"❌ Error: {directory} is not a valid directory.")
        return
    extensions = {get_extension(f) for f in directory.iterdir() if f.is_file()}
    print(f"🔢 Unique extensions: {len(extensions)}")
    for ext in sorted(extensions):
        print(f" - {ext}")


def main():
    parser = argparse.ArgumentParser(
        description="Sort files into directories based on their extensions.",
        usage="files_sort.py [OPTIONS] DIRECTORY",
    )
    parser.add_argument("directory", help="Target directory to sort")
    parser.add_argument(
        "-c", "--copy", action="store_true", help="Copy files instead of moving"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Prompt before overwrite"
    )
    parser.add_argument("-f", "--force", action="store_true", help="Force overwrite")
    parser.add_argument(
        "-d", "--dry", action="store_true", help="Dry run (no actual move/copy)"
    )
    parser.add_argument(
        "-u", "--unique", action="store_true", help="Show unique extensions and exit"
    )
    # parser.add_argument( "-h", "--help", action="help", help="Show help message and exit")

    args = parser.parse_args()

    if args.unique:
        count_unique_extensions(args.directory)
    else:
        sort_files(
            args.directory,
            copy=args.copy,
            verbose=args.verbose,
            dry=args.dry,
            force=args.force,
            interactive=args.interactive,
        )


if __name__ == "__main__":
    main()
