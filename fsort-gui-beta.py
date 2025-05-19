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
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    logging.warning("colorama not installed; using plain text logging")
    Fore = Style = type('Dummy', (), {'__getattr__': lambda self, name: ''})()
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import asyncio
import threading
from queue import Queue

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

# Custom logging handler for Tkinter Text widget
class GUILogHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        # Configure tags for colored text
        self.text_widget.tag_configure("cyan", foreground="cyan")
        self.text_widget.tag_configure("green", foreground="green")
        self.text_widget.tag_configure("blue", foreground="blue")
        self.text_widget.tag_configure("red", foreground="red")

    def emit(self, record):
        msg = record.msg
        tag = None
        # Apply colors based on message content
        if msg.startswith("===") and msg.endswith("==="):
            msg = msg.replace(Fore.CYAN, '').replace(Style.RESET_ALL, '')
            tag = "cyan"
        elif "Created:" in msg:
            msg = msg.replace("Created:", "Created:").replace(Fore.GREEN, '').replace(Style.RESET_ALL, '')
            tag = "green"
        elif "Skipping" in msg:
            msg = msg.replace("Skipping", "Skipping").replace(Fore.BLUE, '').replace(Style.RESET_ALL, '')
            tag = "blue"
        elif "Error:" in msg:
            msg = msg.replace("Error:", "Error:").replace(Fore.RED, '').replace(Style.RESET_ALL, '')
            tag = "red"
        elif "Copied" in msg or "Moved" in msg:
            msg = msg.replace("Copied", "Copied").replace("Moved", "Moved").replace(Fore.GREEN, '').replace(Style.RESET_ALL, '')
            tag = "green"
        msg = f"= {msg}\n"
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg, tag)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

# Configure logger
logger = logging.getLogger("files-sort")
logger.setLevel(logging.INFO)

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

class SizeSortStrategy:
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
        try:
            return file.stat().st_size
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"{EMOJI['ERROR']} Skipping {file}: {e}")
            return -1

    def get_category(self, file: Path) -> str:
        size = self.get_key(file)
        if size == -1:
            return '11_empty'
        for threshold, bucket in self.SIZE_BUCKETS:
            if size >= threshold:
                return bucket
        return '11_empty'

    def get_category_name(self) -> str:
        return "File Size"

    def get_summary_title(self) -> str:
        return "SORTED FILES BY SIZE"

class TimeSortStrategy:
    def __init__(self, use_created: bool = False):
        self.time_func = os.path.getctime if use_created else os.path.getmtime

    def get_key(self, file: Path) -> float:
        try:
            return self.time_func(file)
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"{EMOJI['ERROR']} Skipping {file}: {e}")
            return 0.0

    def get_category(self, file: Path) -> str:
        try:
            return datetime.fromtimestamp(self.time_func(file)).strftime("%Y-%m-%d")
        except (FileNotFoundError, PermissionError, OSError):
            return "unknown_date"

    def get_category_name(self) -> str:
        return "Created Time" if self.time_func == os.path.getctime else "Modified Time"

    def get_summary_title(self) -> str:
        return "SORTED FILES BY DATE"

class ExtensionSortStrategy:
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
    def __init__(self, directory: str, strategy, config: Dict, progress_callback=None):
        self.directory = validate_directory(directory)
        self.strategy = strategy
        self.config = config
        self.category_map: Dict[str, List[str]] = {}
        self.stats = {'total': 0, 'processed': 0, 'skipped': 0}
        self.overwrite_all = False
        self.skip_all = False
        self.progress_callback = progress_callback

    def collect_files(self) -> List[Path]:
        all_files = self.directory.rglob("*") if self.config['recursive'] else self.directory.iterdir()
        excluded_dirs = set()
        if isinstance(self.strategy, SizeSortStrategy):
            excluded_dirs = {self.directory / bucket[1] for bucket in self.strategy.SIZE_BUCKETS}
        elif isinstance(self.strategy, ExtensionSortStrategy):
            excluded_dirs = {self.directory / ext for ext in ['no_ext'] + [
                f.suffix.lower().lstrip(".") for f in self.directory.iterdir() if f.is_file()
            ]}
        elif isinstance(self.strategy, TimeSortStrategy):
            excluded_dirs = {self.directory / datetime.fromtimestamp(self.strategy.get_key(f)).strftime("%Y-%m-%d")
                            for f in self.directory.iterdir() if f.is_file()}
        def is_not_in_excluded(file: Path) -> bool:
            return not any(file.is_relative_to(d) for d in excluded_dirs)
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
                    try:
                        category_dir.mkdir(parents=True, exist_ok=True)
                        logger.debug(f"📁 Created: {category_dir}")
                    except (PermissionError, OSError) as e:
                        logger.error(f"{EMOJI['ERROR']} Failed to create {category_dir}: {e}")
                else:
                    logger.debug(f"📁 Created: {category_dir}")
            else:
                logger.debug(f"{EMOJI['SKIP']} Skipping [{EMOJI['DIR']} {category_dir}], folder already exists")

    def process_file(self, file: Path, category: str) -> bool:
        target_dir = self.directory / category
        target_path = target_dir / file.name
        if target_path.exists() and not (self.config['force'] or self.overwrite_all):
            if self.skip_all:
                logger.info(f"{EMOJI['SKIP']} Skipped: {file.name}")
                self.stats['skipped'] += 1
                return False
            ans = messagebox.askyesnocancel("Overwrite Confirmation",
                                          f"{EMOJI['CONFIRM']} [{EMOJI['EXT']} {target_path}] exists. Overwrite?\n"
                                          "Yes: Overwrite this file\nNo: Skip this file\nCancel: Skip all")
            if ans is None:  # Cancel
                logger.info(f"{EMOJI['SKIP']} Skipping all files with conflicts")
                self.skip_all = True
                self.stats['skipped'] += 1
                return False
            elif ans:  # Yes
                pass
            else:  # No
                logger.info(f"{EMOJI['SKIP']} Skipped: {file.name}")
                self.stats['skipped'] += 1
                return False
        if self.config['dry']:
            logger.info(f"{EMOJI['COPY'] if self.config['copy'] else EMOJI['MOVE']} (Dry): [{EMOJI['EXT']} {file.name}] → [{EMOJI['DIR']} {category}/]")
            return True
        try:
            if self.config['copy']:
                shutil.copy2(file, target_path)
            else:
                shutil.move(file, target_path)
            logger.debug(f"{EMOJI['COPY'] + ' Copied ' if self.config['copy'] else EMOJI['MOVE'] + ' Moved'} [{EMOJI['EXT']} {file.name}] → [{EMOJI['DIR']} {category}/]")
            self.stats['processed'] += 1
            return True
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error(f"{EMOJI['ERROR']} Failed to process {file}: {e}")
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
            if not messagebox.askyesno("Confirm", f"{EMOJI['CONFIRM']} Proceed with sorting?"):
                logger.info(f"🚧 Status: {EMOJI['ERROR']} Stopped")
                logger.info("=== END ===")
                return {}
            logger.info(f"🚧 Status: {EMOJI['DONE']} Proceed")
            logger.info("=== WORKING ===")
        categories = {self.strategy.get_category(file) for file in files}
        self.create_category_dirs(categories)
        total_files = len(files)
        for i, file in enumerate(files, 1):
            self.stats['total'] += 1
            category = self.strategy.get_category(file)
            self.process_file(file, category)
            if self.progress_callback:
                self.progress_callback(i / total_files * 100)
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
            if self.config['force'] or messagebox.askyesno("Confirm", f"{EMOJI['CONFIRM']} Remove empty directories?"):
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
    try:
        for dirpath, dirnames, filenames in os.walk(path, topdown=False):
            if not dirnames and not filenames:
                try:
                    if not dry:
                        os.rmdir(dirpath)
                    log.append(Path(dirpath))
                except OSError as e:
                    logger.warning(f"{EMOJI['ERROR']} Could not remove {dirpath}: {e}")
    except OSError as e:
        logger.error(f"{EMOJI['ERROR']} Error walking directory {path}: {e}")
    return log

def final_summary(total: int, processed: int, skipped: int, directory: Path):
    logger.info(f"{EMOJI['DIR']} Sorted: {directory}")
    logger.info(f"➕ Total files found:     {total}")
    logger.info(f"{EMOJI['MOVE']} Files moved/copied:    {processed}")
    logger.info(f"{EMOJI['SKIP']} Files skipped:         {skipped}")

class FileSorterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Sorter")
        self.root.geometry("800x600")
        self.strategy_map = {
            "extension": ExtensionSortStrategy(),
            "size": SizeSortStrategy(),
            "mtime": TimeSortStrategy(use_created=False),
            "ctime": TimeSortStrategy(use_created=True),
        }
        self.config = {
            'copy': False,
            'verbose': False,
            'dry': False,
            'force': False,
            'recursive': False
        }
        self.directory = tk.StringVar()
        self.sort_criterion = tk.StringVar(value="extension")
        self.setup_gui()
        self.sort_task = None
        self.loop = asyncio.get_event_loop()

    def setup_gui(self):
        # Directory selection
        dir_frame = ttk.Frame(self.root)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(dir_frame, text="Directory:").pack(side=tk.LEFT)
        ttk.Entry(dir_frame, textvariable=self.directory, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).pack(side=tk.LEFT)

        # Options
        options_frame = ttk.Frame(self.root)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(options_frame, text="Sort by:").pack(side=tk.LEFT)
        ttk.Combobox(options_frame, textvariable=self.sort_criterion,
                     values=["extension", "size", "mtime", "ctime"], state="readonly").pack(side=tk.LEFT, padx=5)
        self.copy_var = tk.BooleanVar()
        self.verbose_var = tk.BooleanVar()
        self.dry_var = tk.BooleanVar()
        self.force_var = tk.BooleanVar()
        self.recursive_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Copy", variable=self.copy_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="Verbose", variable=self.verbose_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="Dry Run", variable=self.dry_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="Force", variable=self.force_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="Recursive", variable=self.recursive_var).pack(side=tk.LEFT, padx=5)

        # Log area
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text = tk.Text(log_frame, height=20, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text['yscrollcommand'] = scrollbar.set
        # Set up logger
        logger.handlers = []
        logger.addHandler(GUILogHandler(self.log_text))
        if self.verbose_var.get():
            logger.setLevel(logging.DEBUG)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.progress.pack(pady=5)

        # Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(button_frame, text="Sort Files", command=self.start_sort).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Show Unique Extensions", command=self.show_unique_extensions).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel_sort).pack(side=tk.LEFT, padx=5)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory.set(directory)

    def update_progress(self, value):
        self.progress['value'] = value
        self.root.update_idletasks()

    def start_sort(self):
        if not self.directory.get():
            messagebox.showerror("Error", "Please select a directory.")
            return
        self.config.update({
            'copy': self.copy_var.get(),
            'verbose': self.verbose_var.get(),
            'dry': self.dry_var.get(),
            'force': self.force_var.get(),
            'recursive': self.recursive_var.get()
        })
        logger.setLevel(logging.DEBUG if self.config['verbose'] else logging.INFO)
        self.progress['value'] = 0
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        sorter = FileSorter(self.directory.get(), self.strategy_map[self.sort_criterion.get()],
                           self.config, progress_callback=self.update_progress)
        self.sort_task = threading.Thread(target=self.run_sort, args=(sorter,))
        self.sort_task.start()

    def run_sort(self, sorter):
        try:
            sorter.sort()
        except Exception as e:
            logger.error(f"{EMOJI['ERROR']} Sorting failed: {e}")
        finally:
            self.sort_task = None
            self.root.after(0, lambda: messagebox.showinfo("Done", "Sorting completed."))

    def show_unique_extensions(self):
        if not self.directory.get():
            messagebox.showerror("Error", "Please select a directory.")
            return
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        count, exts = count_unique_extensions(self.directory.get(), self.recursive_var.get())
        logger.info(f"=== 🔢 Unique extensions: {count} ===")
        for i, ext in enumerate(exts, start=1):
            logger.info(f"{i}) {EMOJI['EXT']} {ext}")
        logger.info("=== END ===")

    def cancel_sort(self):
        if self.sort_task and self.sort_task.is_alive():
            messagebox.showwarning("Warning", "Sorting is in progress. Please wait for it to complete.")
        else:
            self.root.quit()

def main():
    root = tk.Tk()
    app = FileSorterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()