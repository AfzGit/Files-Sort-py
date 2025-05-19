#!/usr/bin/env python3

import os
import sys
import shutil
import argparse
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from colorama import init, Fore, Style  # Import colorama

# Initialize colorama for cross-platform support
init(autoreset=True)

# Emoji constants
EMOJI = {
    'COPY': '📝',
    'MOVE': '🚚',
    'SKIP': '⏩',
    'ERROR': '❌',
    'CONFIRM': '❓',
    'DONE': '✅',
    'EMPTY': '🗑️',
    'EXT': '📄',
    'DIR': '📂'
}

# Configure logger with colored formatter
logger = logging.getLogger("files-sort")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()

# Custom formatter to add colors
class ColoredFormatter(logging.Formatter):
    def format(self, record):
        msg = record.msg
        # Color headers (e.g., === DETAILS ===)
        if msg.startswith("===") and msg.endswith("==="):
            msg = f"{Fore.CYAN}{msg}{Style.RESET_ALL}"
        # Color specific actions
        elif "Created:" in msg:
            msg = msg.replace("Created:", f"{Fore.GREEN}Created:{Style.RESET_ALL}")
        elif "Skipping" in msg:
            msg = msg.replace("Skipping", f"{Fore.BLUE}Skipping{Style.RESET_ALL}")
        elif "Error:" in msg:
            msg = msg.replace("Error:", f"{Fore.RED}Error:{Style.RESET_ALL}")
        elif "Copied" in msg or "Moved" in msg:
            msg = msg.replace("Copied", f"{Fore.GREEN}Copied{Style.RESET_ALL}")
            msg = msg.replace("Moved", f"{Fore.GREEN}Moved{Style.RESET_ALL}")
        return f"= {msg}"

handler.setFormatter(ColoredFormatter())
logger.addHandler(handler)

class SortStrategy(ABC):
    @abstractmethod
    def get_key(self, file: Path) -> str:
        pass

    @abstractmethod
    def get_category(self, file: Path) -> str:
        pass

    @abstractmethod
    def get_category_name(self) -> str:
        pass

    @abstractmethod
    def get_summary_title(self) -> str:
        pass

class SizeSortStrategy(SortStrategy):
    SIZE_BUCKETS = [
        (float('inf'), '01_20GB+'),
        (20 * 1024**3, '02_10GB-20GB'),
        (10 * 1024**3, '03_5GB-10GB'),
        (5 * 1024**3, '04_1GB-5GB'),
        (1024**3, '05_500MB-1GB'),
        (500 * 1024**2, '06_100MB-500MB'),
        (100 * 1024**2, '07_1MB-100MB'),
        (1024**2, '08_500KB-1MB'),
        (500 * 1024, '09_1KB-500KB'),
        (1024, '10_0-1KB'),
        (0, '11_empty')
    ]

    def get_key(self, file: Path) -> int:
        return file.stat().st_size

    def get_category(self, file: Path) -> str:
        size = file.stat().st_size
        for threshold, bucket in self.SIZE_BUCKETS:
            if size >= threshold:
                return bucket
        return '11_empty'

    def get_category_name(self) -> str:
        return "File Size"

    def get_summary_title(self) -> str:
        return "SORTED FILES BY SIZE"

class TimeSortStrategy(SortStrategy):
    def __init__(self, use_created: bool = False):
        self.time_func = os.path.getctime if use_created else os.path.getmtime

    def get_key(self, file: Path) -> float:
        return self.time_func(file)

    def get_category(self, file: Path) -> str:
        return datetime.fromtimestamp(self.time_func(file)).strftime("%Y-%m-%d")

    def get_category_name(self) -> str:
        return "Created Time" if self.time_func == os.path.getctime else "Modified Time"

    def get_summary_title(self) -> str:
        return "SORTED FILES BY DATE"

class ExtensionSortStrategy(SortStrategy):
    def get_extension(self, file: Path) -> str:
        return file.suffix.lower().lstrip(".") or "no_ext"

    def get_key(self, file: Path) -> str:
        return self.get_extension(file)

    def get_category(self, file: Path) -> str:
        return self.get_extension(file)

    def get_category_name(self) -> str:
        return "File Extension"

    def get_summary_title(self) -> str:
        return "SORTED FILES BY EXTENSION"

class FileSorter:
    def __init__(self, directory: str, strategy: SortStrategy, config: Dict):
        self.directory = validate_directory(directory)
        self.strategy = strategy
        self.config = config
        self.category_map: Dict[str, List[str]] = {}
        self.stats = {'total': 0, 'processed': 0, 'skipped': 0}
        self.overwrite_all = False
        self.skip_all = False

    def collect_files(self) -> List[Path]:
        all_files = self.directory.rglob("*") if self.config['recursive'] else self.directory.iterdir()
        
        # Identify excluded folders (created by sorter itself)
        excluded_dirs = set()
        if isinstance(self.strategy, SizeSortStrategy):
            excluded_dirs = {str(self.directory / bucket[1]) for bucket in self.strategy.SIZE_BUCKETS}
        elif isinstance(self.strategy, ExtensionSortStrategy):
            excluded_dirs = {str(self.directory / ext) for ext in ['no_ext'] + [
                f.suffix.lower().lstrip(".") for f in self.directory.iterdir() if f.is_file()
            ]}
        elif isinstance(self.strategy, TimeSortStrategy):
            excluded_dirs = {str(self.directory / datetime.fromtimestamp(self.strategy.get_key(f)).strftime("%Y-%m-%d"))
                            for f in self.directory.iterdir() if f.is_file()}

        def is_not_in_excluded(file: Path) -> bool:
            return not any(str(file).startswith(d + os.sep) for d in excluded_dirs)

        return sorted([f for f in all_files if f.is_file() and is_not_in_excluded(f)], key=self.strategy.get_key)

    def log_details(self, files: List[Path]):
        logger.info("=== DETAILS ===")
        logger.info(f"➡ {EMOJI['DIR']} Directory: [{self.directory}]")
        logger.info(f"➡ 🎬 Action: {EMOJI['COPY'] + ' Copying' if self.config['copy'] else EMOJI['MOVE'] + ' Moving'}")
        logger.info(f"➡ 📦 Sorted by: {self.strategy.get_category_name()}")

        seen_categories = set()
        logger.info("=== ACTIONS ===")
        for file in files:
            category = self.strategy.get_category(file)
            category_dir = self.directory / category
            if category not in seen_categories:
                msg = f"{EMOJI['ERROR']} 📁 [{category_dir}] (Already exists)" if category_dir.exists() else f"{EMOJI['DONE']} 📁 [{category_dir}]"
                logger.info(msg)
                seen_categories.add(category)
            try:
                stat = file.stat()
                size_info = f" ({human_readable_size(stat.st_size)})" if isinstance(self.strategy, SizeSortStrategy) else ""
            except FileNotFoundError:
                size_info = " (not found)"
            logger.info(f"   ➡ {EMOJI['EXT']} {file.name}{size_info}")

    def create_category_dirs(self, categories: set):
        for category in categories:
            category_dir = self.directory / category
            if not category_dir.exists():
                if not self.config['dry']:
                    category_dir.mkdir(parents=True, exist_ok=True)
                if self.config['verbose']:
                    logger.info(f"📁 Created: {category_dir}")
            elif self.config['verbose']:
                logger.info(f"{EMOJI['SKIP']} Skipping [{EMOJI['DIR']} {category_dir}], folder already exists")

    def process_file(self, file: Path, category: str) -> bool:
        target_dir = self.directory / category
        target_path = target_dir / file.name

        if target_path.exists() and not (self.config['force'] or self.overwrite_all):
            if not self.skip_all:
                ans = confirm_overwrite_choice(f"{EMOJI['CONFIRM']} [{EMOJI['EXT']} {target_path}] exists. Overwrite?")
            else:
                ans = 's'
            if ans == "a":
                self.overwrite_all = True
                logger.info("⚔️ Overwriting all files")
            elif ans in {"n", "s"}:
                if ans == "s" and not self.skip_all:
                    logger.info(f"{EMOJI['SKIP']} Skipping all files with conflicts")
                    self.skip_all = True
                logger.info(f"{EMOJI['SKIP']} Skipped: {file.name}")
                self.stats['skipped'] += 1
                return False
            elif ans != "y":
                return False

        if self.config['dry']:
            logger.info(f"{EMOJI['COPY'] if self.config['copy'] else EMOJI['MOVE']} (Dry): [{EMOJI['EXT']} {file.name}] → [{EMOJI['DIR']} {category}/]")
            self.stats['processed'] += 1
            return True

        try:
            if self.config['copy']:
                shutil.copy2(file, target_path)
            else:
                shutil.move(file, target_path)
            if self.config['verbose']:
                logger.info(f"{EMOJI['COPY'] + ' Copied ' if self.config['copy'] else EMOJI['MOVE'] + ' Moved'} [{EMOJI['EXT']} {file.name}] → [{EMOJI['DIR']} {category}/]")
            self.stats['processed'] += 1
            return True
        except Exception as e:
            logger.error(f"{EMOJI['ERROR']} Error: {e}")
            self.stats['skipped'] += 1
            return False

    def sort(self) -> Dict[str, List[str]]:
        files = self.collect_files()
        if not files:
            logger.info(f"{EMOJI['DIR']} No files to sort.")
            return {}

        self.log_details(files)
        
        if not self.config['force']:
            logger.info("=== CONFIRMATION ===")
            if not confirm(f"= {EMOJI['CONFIRM']} Proceed?"):
                logger.info(f"🚧 Status: {EMOJI['ERROR']} Stopped")
                logger.info("=== END ===")
                sys.exit(1)
            logger.info(f"🚧 Status: {EMOJI['DONE']} Proceed")
            logger.info("=== WORKING ===")

        categories = {self.strategy.get_category(file) for file in files}
        self.create_category_dirs(categories)

        for file in files:
            self.stats['total'] += 1
            category = self.strategy.get_category(file)
            if self.process_file(file, category):
                self.category_map.setdefault(category, []).append(file.name)

        if self.config['recursive']:
            self.cleanup_empty_dirs()

        if not self.config['dry']:
            self.log_summary()

        logger.info("=== FINAL SUMMARY ===")
        final_summary(self.stats['total'], self.stats['processed'], self.stats['skipped'], self.directory)
        logger.info("=== END ===")
        return self.category_map

    def cleanup_empty_dirs(self):
        logger.info("=== CLEANUP ===")
        empty_dirs = remove_empty_dirs(self.directory, dry=True)
        if empty_dirs:
            for d in empty_dirs:
                logger.info(f"⚠️ Found empty dir: [{d}]")
            if self.config['force'] or confirm(f"= {EMOJI['CONFIRM']} Remove empty directories?"):
                remove_empty_dirs(self.directory, dry=self.config['dry'])
                if not self.config['dry']:
                    for d in empty_dirs:
                        logger.info(f"{EMOJI['EMPTY']} Removed: [{d}]")
            else:
                logger.info("❌️ Did not remove empty directories")
        else:
            logger.info("No empty dirs found")

    def log_summary(self):
        logger.info(f"=== {self.strategy.get_summary_title()} ===")
        for category in sorted(self.category_map):
            logger.info(f"{EMOJI['DIR']} {category}/")
            for fname in sorted(self.category_map[category], key=str.lower):
                logger.info(f"  {EMOJI['EXT']} {fname}")

def validate_directory(path: str) -> Path:
    path = Path(path).expanduser().resolve()
    if not path.is_dir():
        logger.error(f"{EMOJI['ERROR']} Error: {path} is not a valid directory.")
        sys.exit(1)
    return path

def human_readable_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"

def count_unique_extensions(directory: str, recursive: bool) -> tuple[int, List[str]]:
    directory = validate_directory(directory)
    files = directory.rglob("*") if recursive else directory.iterdir()
    extensions = {ExtensionSortStrategy().get_extension(f) for f in files if f.is_file()}
    return len(extensions), sorted(extensions)

def remove_empty_dirs(path: Path, dry: bool) -> List[Path]:
    log = []
    for dirpath, dirnames, filenames in os.walk(path, topdown=False):
        if not dirnames and not filenames:
            try:
                if not dry:
                    os.rmdir(dirpath)
                log.append(Path(dirpath))
            except Exception as e:
                logger.warning(f"{EMOJI['ERROR']} Could not remove {dirpath}: {e}")
    return log

def final_summary(total: int, processed: int, skipped: int, directory: Path):
    logger.info(f"{EMOJI['DIR']} Sorted: {directory}")
    logger.info(f"➕ Total files found:     {total}")
    logger.info(f"{EMOJI['MOVE']} Files moved/copied:    {processed}")
    logger.info(f"{EMOJI['SKIP']} Files skipped:         {skipped}")

def confirm(prompt: str) -> bool:
    try:
        return input(f"{prompt} [y/N]: ").strip().lower() == "y"
    except (KeyboardInterrupt, EOFError):
        sys.exit(1)

def confirm_overwrite_choice(prompt: str) -> str:
    try:
        response = input(f"=\n= {prompt}\n= [y]es | [N]O | [a]ll | [s]kip all: ").strip().lower()
        return response if response in {"y", "a", "n", "s"} else "n"
    except (KeyboardInterrupt, EOFError):
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Sort files into directories based on specified criteria.",
        usage="files-sort.py [OPTIONS] DIRECTORY",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("directory", help="Target directory to sort")
    parser.add_argument("-c", "--copy", action="store_true", help="Copy files instead of moving")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-f", "--force", action="store_true", help="Run without prompts, overwrite all existing files")
    parser.add_argument("-d", "--dry", action="store_true", help="Dry run (simulate actions)")
    parser.add_argument("-u", "--unique", action="store_true", help="Show unique extensions and exit")
    parser.add_argument("-r", "--recursive", action="store_true", help="Recursively sort sub-directories")
    parser.add_argument(
        "-s",
        "--sort",
        choices=["extension", "size", "mtime", "ctime"],
        default="extension",
        help="Sort criterion: extension, size, mtime (modified time), ctime (created time)",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.unique:
        count, exts = count_unique_extensions(args.directory, args.recursive)
        logger.info(f"=== 🔢 Unique extensions: {count} ===")
        for i, ext in enumerate(exts, start=1):
            logger.info(f"{i}) {EMOJI['EXT']} {ext}")
        logger.info("=== END ===")
        return

    strategy_map = {
        "extension": ExtensionSortStrategy(),
        "size": SizeSortStrategy(),
        "mtime": TimeSortStrategy(use_created=False),
        "ctime": TimeSortStrategy(use_created=True),
    }
    
    config = {
        'copy': args.copy,
        'verbose': args.verbose,
        'dry': args.dry,
        'force': args.force,
        'recursive': args.recursive
    }

    sorter = FileSorter(args.directory, strategy_map[args.sort], config)
    sorter.sort()

if __name__ == "__main__":
    main()