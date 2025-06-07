# Quickly estimate the total complexity of your repository, as measured by LLM tokens.

The tokenization process uses a tokenizer compatible with Anthropic Claude models (specifically, `cl100k_base` via the `tiktoken` library), making the results representative for estimating Claude API usage or context window limits.

## Features

-   Calculates token counts on a per-file basis.
-   Provides a summary of total token counts for the specified directory.
-   Uses `tiktoken` library for Claude-compatible tokenization.
-   Ignores binary files and common non-code directories by default (e.g., `.git`, `__pycache__`).
-   Filters files to analyze using a regular expression pattern.
-   Allows excluding specific file extensions (e.g., `.log`, `.tmp`).
-   Allows excluding specific directory names (e.g., `.git`, `node_modules`).
-   Optional sorting of results by token count.
-   Optional display of skipped/errored files in the detailed list.

## Installation

To install the `codetokencalculator`, you can clone this repository and install it using pip:

```bash
git clone <repository_url>
cd codetokencalculator
pip install .
```

Alternatively, if packaged and uploaded to PyPI:

```bash
pip install codetokencalculator
```

## Usage

Once installed, you can run the tool from your terminal:

```bash
codetokencalculator "<file_regex_pattern>" [directory_path] [options]
```
The `<file_regex_pattern>` is a **mandatory** Python regular expression used to match against relative file paths.
The `[directory_path]` is an optional argument specifying the directory to scan. If omitted, it defaults to the current directory (`.`).
Ensure to quote the pattern if it contains shell special characters.

**Examples:**
- To count tokens for all Python files (`.py`) in the current directory (if `[directory_path]` is omitted, it defaults to `.`):
  ```bash
  codetokencalculator "\\.py$"
  ```
- To count tokens for Python (`.py`) or C++ (`.cpp`, `.h`) files by explicitly specifying the `./src` directory as `[directory_path]`:
  ```bash
  codetokencalculator "\\.(py|cpp|h)$" ./src
  ```
- To count tokens for JavaScript files (`.js`) only within a `src/api/` subdirectory of the current directory (using the default `[directory_path]`), and also show skipped files:
  ```bash
  codetokencalculator "^src/api/.*\\.js$" --show-skipped
  ```

This will output a list of files matching the pattern (and not otherwise excluded) with their respective token counts, followed by a total count for the repository.

### Options

-   `--output-file <filepath>`, `-o <filepath>`: (Optional) Path to save the output report.
-   `--sort-by-tokens`: (Optional) Sort the results by token count (descending) instead of by path.
-   `--show-skipped`: (Optional) Include skipped and errored files in the detailed file list. By default, they are hidden from the per-file list but included in the summary counts.
-   `--exclude-extensions <ext1,ext2,...>`: (Optional) Comma-separated list of file extensions to exclude (e.g., `.log,.tmp,.bak`). These files will be skipped even if their path matches the main `<file_regex_pattern>`. Extensions are case-insensitive (e.g., `.PY` is treated as `.py`).
-   `--exclude-dirs <dir1,dir2,...>`: (Optional) Comma-separated list of directory names to exclude. Files within these directories will be skipped. Defaults to a common set including `.git`, `node_modules`, `__pycache__`, `venv`, etc.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
