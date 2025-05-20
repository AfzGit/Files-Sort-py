# 🗂️ files-sort

A powerful command-line tool to **sort files** in a directory based on criteria like file **extension**, **size**, or **timestamps**. Supports copying, moving, dry runs, verbose output, and automatic cleanup of empty directories.

---

## 🚀 Features

-   📄 **Sort by Extension**: Groups files by file type (e.g., `.jpg`, `.pdf`).
-   📦 **Sort by Size**: Categorizes files into size buckets (e.g., 0–1KB, 1–100MB, etc.).
-   🕒 **Sort by Time**: Uses modified time (`mtime`) or created time (`ctime`) to group files by date.
-   🚚 **Move or Copy**: Choose whether to move or copy files.
-   🔍 **Dry Run Support**: Simulate the process before applying any changes.
-   💬 **Interactive Prompts**: Ask before overwriting or skipping conflicting files.
-   📁 **Recursive Support**: Process subdirectories.

---

## ✅ Requirements

-   Python 3.7+
-   [`colorama`](https://pypi.org/project/colorama/)

Install dependencies:

```bash
pip install -r requirements.txt
```

or

```bash
pip install colorama
```

---

## 📦 Installation

## Option 1: Pip

Install via pip (if packaged as a CLI tool):

```bash
pip install -i https://test.pypi.org/simple/ --no-deps files-sort
```

To upgrade:

```bash
pip install --upgrade -i https://test.pypi.org/simple/ --no-deps files-sort
```

## Option 2: Clone the repo

Clone the repo and make it executable:

```bash
git clone https://github.com/AfzGit/Files-Sort-py.git
cd Files-Sort-py/src/files_sort/
chmod +x files-sort.py
python files-sort.py -h
```

---

## 🧩 Usage

```bash
files-sort [OPTIONS] DIRECTORY
```

### 🔧 Options

| Option              | Description                                                             |
| ------------------- | ----------------------------------------------------------------------- |
| `-s`, `--sort`      | Sort by `extension`, `size`, `mtime`, or `ctime`. Default: `extension`. |
| `-c`, `--copy`      | Copy files instead of moving them.                                      |
| `-v`, `--verbose`   | Show detailed logs during processing.                                   |
| `-d`, `--dry`       | Simulate the sorting without actually moving/copying files.             |
| `-f`, `--force`     | Skip confirmation prompts and overwrite existing files.                 |
| `-r`, `--recursive` | Include subdirectories recursively.                                     |
| `-u`, `--unique`    | List unique file extensions in the directory and exit.                  |

---

## 📂 Examples

### 🔤 Sort files by extension

```bash
files-sort ~/Downloads
```

### 📏 Sort by size (dry run + verbose)

```bash
files-sort -s size -d -v ~/Documents
```

### 🕓 Sort by modified time (recursively)

```bash
files-sort -s mtime -r ~/Pictures
```

### 📝 Copy instead of move, force overwrite

```bash
files-sort -s extension -c -f ~/Videos
```

### 🔍 See unique file extensions

```bash
files-sort -u ~/Downloads
```

---

## 🧼 Auto Cleanup

If `--recursive` is used, the tool will also:

-   Detect and optionally remove empty directories after sorting.

---

## 📊 Output Summary

At the end of execution, you'll see:

-   Total files found
-   Number of files moved or copied
-   Number of files skipped
-   Final categorization by folder
