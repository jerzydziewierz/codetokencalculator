# codetokencalculator/codetokencalculator/main.py

"""
Command-line interface for the Code Token Calculator.
"""

import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

from .calculator import process_directory, DEFAULT_EXCLUDE_DIRS, DEFAULT_INCLUDE_EXTENSIONS, TEXT_FILENAMES_WITHOUT_EXTENSION
from . import __version__

def format_results_text(data: dict, directory_path_str: str, sort_by_tokens: bool, show_skipped_files: bool) -> str:
    """
    Formats the token count results into a human-readable text block.
    """
    output_lines = []
    base_path = Path(directory_path_str).resolve()

    output_lines.append(f"Code Token Calculator Report - v{__version__}")
    output_lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append(f"Target Directory: {base_path}")
    output_lines.append("-" * 80)

    if data["errors"]:
        output_lines.append("ERRORS ENCOUNTERED:")
        for err in data["errors"]:
            output_lines.append(f"- {err}")
        output_lines.append("-" * 80)
        return "\n".join(output_lines)

    output_lines.append("\nFile Token Counts:")
    if not show_skipped_files and any(f["tokens"] is None for f in data["files"]):
        output_lines.append("(Skipped/errored files are hidden from this list. Use --show-skipped to display them.)")
    header = f"{'Path':<60} | {'Tokens':>10} | Status"
    output_lines.append(header)
    output_lines.append("-" * len(header))

    max_path_len = 60 # Default, adjust if needed based on actual paths

    files_to_display = data["files"]
    if sort_by_tokens:
        # Sort by tokens (descending), then by path (ascending) for tie-breaking
        # Handle None tokens by placing them at the end (or treating as -1 for sorting purposes)
        files_to_display = sorted(
            files_to_display,
            key=lambda x: (x["tokens"] is None, - (x["tokens"] or 0), x["path"])
        )
        output_lines.append("Sorted by token count (descending).")
        output_lines.append("---")


    for file_info in files_to_display:
        if not show_skipped_files and file_info["tokens"] is None:
            continue # Do not list skipped/errored files if not requested

        path_str = file_info["path"]
        tokens_str = str(file_info["tokens"]) if file_info["tokens"] is not None else "N/A"
        status_str = file_info["status"]

        # Truncate long paths for display
        if len(path_str) > max_path_len -3: # -3 for "..."
             display_path = "..." + path_str[-(max_path_len-3):]
        else:
            display_path = path_str

        output_lines.append(f"{display_path:<{max_path_len}} | {tokens_str:>10} | {status_str}")

    output_lines.append("-" * len(header))
    output_lines.append("\nSummary:")
    output_lines.append("-" * 80)

    summary = data["summary"]
    output_lines.append(f"Total files processed successfully: {summary['total_files_processed_successfully']:>10}")
    output_lines.append(f"Total files with errors:          {summary['total_files_with_errors']:>10}")
    output_lines.append(f"Total files skipped:              {summary['total_files_skipped']:>10}")
    output_lines.append(f"Total tokens counted:             {summary['total_tokens']:>10}")

    if summary['directories_explicitly_skipped']:
        output_lines.append("\nDirectories explicitly skipped (due to name matching exclude list):")
        for skipped_dir in summary['directories_explicitly_skipped']:
            output_lines.append(f"- {skipped_dir}")

    output_lines.append("-" * 80)
    return "\n".join(output_lines)


def main_cli():
    """
    Main command-line interface function.
    """
    epilog_text = (
        "example usage:\n"
        "  codetokencalculator \"\\.py$\"                                  # Count for Python files in current directory (directory defaults to '.')\n"
        "  codetokencalculator \"\\.(py|cpp|h)$\" ./src --show-skipped       # Count for .py, .cpp, .h files in ./src, show skipped\n"
        "  codetokencalculator \"^src/api/.*\\.js$\" --show-skipped         # Count for .js in src/api/ of current dir, show skipped\n\n"
        "The <file_regex_pattern> is a mandatory Python regular expression used to match against relative file paths.\n"
        "The [directory_path] is an optional argument specifying the directory to scan. If omitted, it defaults\n"
        "to the current directory ('.'). Ensure to quote the pattern if it contains shell special characters.\n"
        "For example, to match only .py files, use \"\\.py$\". To match .py or .cpp files, use \"\\.(py|cpp)$\"."
    )

    parser = argparse.ArgumentParser(
        description=f"Code Token Calculator v{__version__}. Counts LLM input tokens for files in a directory matching a regex pattern, using a Claude-compatible tokenizer.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog_text
    )
    parser.add_argument(
        "file_regex_pattern",
        type=str,
        help="Regular expression pattern to match file paths to analyze (e.g., \"\\.py$\" or \"\\.(py|cpp)$\" )."
    )
    parser.add_argument(
        "directory",
        type=str,
        nargs='?',
        default='.',
        help="The path to the directory to scan. Defaults to the current directory ('.') if not specified."
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=str,
        help="Optional. Path to save the detailed report (text format)."
    )
    parser.add_argument(
        "--sort-by-tokens",
        action="store_true",
        help="Sort the results by token count (descending) instead of by path."
    )
    parser.add_argument(
        "--exclude-extensions",
        type=str,
        help=(
            "Comma-separated list of file extensions to exclude (e.g., .log,.tmp,.bak).\n"
            "Extensions should include the leading dot. Case-insensitive."
        )
    )
    parser.add_argument(
        "--show-skipped",
        action="store_true",
        help="Include skipped and errored files in the detailed file list. By default, they are hidden."
    )
    parser.add_argument(
        "--exclude-dirs",
        type=str,
        help=(
            "Comma-separated list of directory names to exclude.\n"
            f"Defaults: {','.join(sorted(list(DEFAULT_EXCLUDE_DIRS)))}"
        )
    )
    # TODO: Implement --include-extensions and --exclude-extensions if needed
    # parser.add_argument(
    #     "--include-extensions",
    #     type=str,
    #     help=(
    #         "Comma-separated list of file extensions to include (e.g., .py,.js,.md).\n"
    #         "Specify '.' for files without extensions. \n"
    #         f"Defaults to a predefined list: {','.join(sorted(list(DEFAULT_INCLUDE_EXTENSIONS)))} \n"
    #         f"and known text filenames: {','.join(sorted(list(TEXT_FILENAMES_WITHOUT_EXTENSION)))}"
    #     )
    # )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    args = parser.parse_args()

    file_regex_pattern = args.file_regex_pattern
    target_directory = args.directory

    exclude_dirs_set = set(DEFAULT_EXCLUDE_DIRS)
    if args.exclude_dirs:
        exclude_dirs_set.update(d.strip() for d in args.exclude_dirs.split(',') if d.strip())

    exclude_extensions_set = set()
    if args.exclude_extensions:
        for ext in args.exclude_extensions.split(','):
            cleaned_ext = ext.strip().lower()
            if cleaned_ext:
                if not cleaned_ext.startswith('.'):
                    cleaned_ext = '.' + cleaned_ext
                exclude_extensions_set.add(cleaned_ext)

    print(f"Starting token count for directory: {Path(target_directory).resolve()}")
    print(f"Using tokenizer: cl100k_base (Claude-compatible)")
    if exclude_dirs_set:
        print(f"Excluding directories named: {', '.join(sorted(list(exclude_dirs_set)))}")
    if exclude_extensions_set:
        print(f"Excluding extensions: {', '.join(sorted(list(exclude_extensions_set)))}")
    if args.sort_by_tokens:
        print("Sorting output by token count (descending).")
    if not args.show_skipped:
        print("Note: Skipped/errored files are hidden from the detailed list by default (use --show-skipped to display).")
    print("Processing...")

    try:
        results_data = process_directory(
            directory_path_str=target_directory,
            file_regex_pattern=file_regex_pattern,
            exclude_dirs=exclude_dirs_set,
            exclude_extensions=exclude_extensions_set
        )
    except Exception as e:
        print(f"\nAn unexpected error occurred during processing: {e}", file=sys.stderr)
        sys.exit(1)

    report_text = format_results_text(results_data, target_directory, args.sort_by_tokens, args.show_skipped)

    print("\n" + report_text)

    if args.output_file:
        output_file_path = Path(args.output_file)
        try:
            output_file_path.write_text(report_text, encoding="utf-8")
            print(f"\nReport also saved to: {output_file_path.resolve()}")
        except IOError as e:
            print(f"\nError saving report to file '{output_file_path}': {e}", file=sys.stderr)

    if results_data["errors"] or results_data["summary"]["total_files_with_errors"] > 0 :
        # Indicate an issue in exit code if there were processing errors
        # sys.exit(1) # User might still want to see partial results
        pass


if __name__ == "__main__":
    # This allows running the CLI script directly for development/testing
    # e.g., python -m codetokencalculator.main "\\.py$" ./my_project
    #   or python -m codetokencalculator.main "\\.py$"
    main_cli()
