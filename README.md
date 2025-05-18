# 🗂️ files-sort.py

A Python utility to **organize files into subfolders based on their extensions**. Supports moving or copying files, interactive prompts, dry-run mode, and recursive sorting.

---

## 🚀 Features

-   📦 Sorts files into folders like `pdf/`, `txt/`, `no_ext/`, etc.
-   🔄 Move or copy files
-   ❓ Interactive mode for per-file confirmation
-   ⚠️ Force mode to overwrite without prompts
-   🧪 Dry-run to simulate actions
-   🔁 Recursive sorting into subfolders
-   📊 List unique file extensions in a directory

---

## 📌 Usage

```bash
./files-sort.py [OPTIONS] DIRECTORY
```

---

## 🧩 Options

| Flag                  | Description                                                                       |
| --------------------- | --------------------------------------------------------------------------------- |
| `-c`, `--copy`        | Copy files instead of moving them                                                 |
| `-v`, `--verbose`     | Enable verbose output (show moved/copied files)                                   |
| `-i`, `--interactive` | Prompt before each file is moved/copied                                           |
| `-f`, `--force`       | Overwrite existing files and suppress prompts (incompatible with `--interactive`) |
| `-d`, `--dry`         | Perform a dry run (simulate actions without changes)                              |
| `-u`, `--unique`      | List all unique file extensions in the directory and exit                         |
| `-r`, `--recursive`   | Recursively sort files in all subdirectories                                      |

---

## 🧪 Examples

-   👉 Move files by extension:

    ```bash
    ./files-sort.py ~/Downloads
    ```

-   🧾 Copy files with verbose output:

    ```bash
    ./files-sort.py -cv ~/Documents
    ```

-   ❓ Interactive dry-run:

    ```bash
    ./files-sort.py -id ~/Desktop
    ```

-   🔁 Recursively sort and remove empty folders:

    ```bash
    ./files-sort.py -r -f ~/Projects
    ```

-   📊 Just list extensions:

    ```bash
    ./files-sort.py -u ~/Downloads
    ```

---

## 🛠️ Requirements

-   Python 3.6+

No third-party dependencies required.

---

## 📂 How it Works

1. Scans the target directory (optionally recursively).
2. Groups files by extension.
3. Creates subfolders (e.g., `txt/`, `jpg/`, `no_ext/`).
4. Moves or copies files into corresponding folders.
5. Optionally removes empty directories (in recursive + force mode).

---

## ⚠️ Notes

-   `--force` and `--interactive` cannot be used together.
-   The `no_ext` folder is used for files without extensions.
-   Recursive mode may clean up empty folders if `--force` is used or upon confirmation.
