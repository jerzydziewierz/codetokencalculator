# codetokencalculator/codetokencalculator/calculator.py

"""
Core logic for scanning directories, processing files, and counting tokens.
"""

import os
import re
import re
from pathlib import Path
from typing import Optional, Set
from .tokenizer import count_tokens_for_text

# Default directories to exclude from scanning
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".vscode",
    ".idea",
    "build",
    "dist",
    "env",
    "venv",
    ".venv",
    "target", # For Rust/Java
    "*.egg-info" # Python packaging
}

# Default file extensions to consider as text/code.
# Using a set for efficient lookup.
DEFAULT_INCLUDE_EXTENSIONS = {
    # Common code files
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".kts", ".scala",
    ".pl", ".pm", ".sh", ".bash", ".zsh",
    # Common text/config files
    ".md", ".txt", ".json", ".yaml", ".yml", ".xml", ".html", ".css", ".scss",
    ".toml", ".ini", ".cfg", ".conf", ".sql", ".dockerfile", "Dockerfile",
    ".gitignore", ".gitattributes",
    # Notebooks (source part) - often large, but text parts are relevant
    # Note: .ipynb files are JSON, tokenizing the whole thing might not be what users expect
    # if they only care about code cells. For now, we treat it as a text file.
    ".ipynb"
}
# Files without extensions but are typically text
TEXT_FILENAMES_WITHOUT_EXTENSION = {
    "Dockerfile",
    "Makefile",
    "Jenkinsfile",
    "LICENSE",
    "README" # Often .md, but sometimes without extension
}


# Heuristic to detect binary files by checking for null bytes in the first few KB
def is_binary_file(filepath: Path, sample_size: int = 4096) -> bool:
    """
    Checks if a file is likely binary by looking for null bytes in a sample.
    """
    try:
        with open(filepath, "rb") as f:
            sample = f.read(sample_size)
            if b'\0' in sample:
                return True
    except IOError: # File might not be readable, treat as something to skip
        return True
    return False

def is_likely_text_file(filepath: Path) -> bool:
    """
    Determines if a file is likely a text file based on its extension or name.
    """
    if filepath.suffix.lower() in DEFAULT_INCLUDE_EXTENSIONS:
        return True
    if filepath.name in TEXT_FILENAMES_WITHOUT_EXTENSION:
        return True
    # If no extension, and not in the explicit list, it's ambiguous.
    # We might try to read it, but `is_binary_file` will be the main guard.
    if not filepath.suffix: # No extension
        return not is_binary_file(filepath) # Check content if no extension
    return False


def process_file(filepath: Path, exclude_extensions: Set[str]) -> tuple[Optional[int], Optional[str]]:
    """
    Reads a file and counts its tokens.

    Args:
        filepath: Path to the file.

    Returns:
        A tuple (token_count, error_message).
        token_count is None if an error occurs or file is skipped.
        error_message contains details if an error occurred.
    """
    try:
        file_extension_lower = filepath.suffix.lower()

        # 1. Check user-defined excluded extensions (only if file has an extension)
        if file_extension_lower and file_extension_lower in exclude_extensions:
            return None, f"Skipped (excluded extension: {file_extension_lower})"

        # 2. Determine if the file type is generally included (by is_likely_text_file)
        #    is_likely_text_file also handles binary check for extension-less files.
        if not is_likely_text_file(filepath):
            if file_extension_lower: # Has an extension, but not in our default include list
                return None, f"Skipped (extension {file_extension_lower} not in default inclusion list)"
            elif not filepath.suffix and is_binary_file(filepath): # No extension, and was found to be binary by is_likely_text_file
                return None, "Skipped (binary file without extension)"
            else: # No extension and not binary (but still is_likely_text_file=false), or other unhandled cases.
                return None, "Skipped (file type not recognized or not in default inclusion list)"

        # 3. For files that are "likely text" (passed above checks),
        #    do a final explicit binary content check. This is important for files with
        #    recognized text extensions that might still contain binary data.
        if is_binary_file(filepath):
            return None, "Skipped (binary content detected in recognized text file type)"

        # Try to read with UTF-8, common for code. Fallback if needed.
        try:
            content = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                # Common fallback for files not in UTF-8
                content = filepath.read_text(encoding="latin-1")
            except Exception as e_read:
                return None, f"Error reading file (tried utf-8, latin-1): {e_read}"
        except FileNotFoundError:
            return None, "Error: File not found during processing."
        except Exception as e_read: # Other read errors
            return None, f"Error reading file: {e_read}"

        if not content.strip(): # Check if content is empty or only whitespace
            return 0, "Empty or whitespace-only file"

        token_count = count_tokens_for_text(content)
        return token_count, None

    except Exception as e:
        # Catch-all for unexpected issues during file processing
        return None, f"Unexpected error processing file: {e}"


def process_directory(
    directory_path_str: str,
    file_regex_pattern: str,
    exclude_dirs: Optional[Set[str]] = None,
    exclude_extensions: Optional[Set[str]] = None
) -> dict:
    """
    Scans a directory, counts tokens for each valid file matching the regex, and returns a summary.

    Args:
        directory_path_str: The path to the directory to scan.
        file_regex_pattern: The regex pattern to match file paths against.
        exclude_dirs: A set of directory names to exclude. Defaults to DEFAULT_EXCLUDE_DIRS.
        exclude_extensions: A set of file extensions (e.g., {".log", ".tmp"}) to exclude.

    Returns:
        A dictionary containing:
        {
            "files": [
                {"path": "rel_path_to_file", "tokens": count, "status": "Processed"},
                {"path": "rel_path_to_file", "tokens": null, "status": "Error message or Skipped"},
                ...
            ],
            "summary": {
                "total_files_processed_successfully": int,
                "total_files_with_errors": int,
                "total_files_skipped": int,
                "total_tokens": int,
                "directories_explicitly_skipped": list_of_skipped_dir_paths
            },
            "errors": list_of_general_errors (e.g., if input directory is invalid)
        }
    """
    directory_path = Path(directory_path_str).resolve()
    if not directory_path.is_dir():
        return {
            "files": [],
            "summary": {
                "total_files_processed_successfully": 0,
                "total_files_with_errors": 0,
                "total_files_skipped": 0,
                "total_tokens": 0,
                "directories_explicitly_skipped": []
            },
            "errors": [f"Error: Path '{directory_path_str}' is not a valid directory or not accessible."]
        }

    try:
        compiled_regex = re.compile(file_regex_pattern)
    except re.error as e:
        return {
            "files": [],
            "summary": {
                "total_files_processed_successfully": 0,
                "total_files_with_errors": 0,
                "total_files_skipped": 0,
                "total_tokens": 0,
                "directories_explicitly_skipped": []
            },
            "errors": [f"Error: Invalid regex pattern '{file_regex_pattern}': {e}"]
        }

    if exclude_dirs is None:
        exclude_dirs_set = DEFAULT_EXCLUDE_DIRS
    else:
        exclude_dirs_set = set(exclude_dirs) # Assumes exclude_dirs is already a set of strings

    # Prepare exclude_extensions set, ensuring leading dot and lowercase
    current_exclude_extensions_set = set()
    if exclude_extensions:
        for ext in exclude_extensions:
            cleaned_ext = ext.lower().strip()
            if not cleaned_ext.startswith('.'):
                cleaned_ext = '.' + cleaned_ext
            current_exclude_extensions_set.add(cleaned_ext)

    results = {
        "files": [],
        "summary": {
            "total_files_processed_successfully": 0,
            "total_files_with_errors": 0,
            "total_files_skipped": 0,
            "total_tokens": 0,
            "directories_explicitly_skipped": [] # For directories matching names in exclude_dirs_set
        },
        "errors": []
    }

    processed_paths = set() # To avoid double processing if symlinks loop, though rglob might handle some of this

    for item_path in directory_path.rglob("*"):
        if item_path in processed_paths:
            continue
        processed_paths.add(item_path)

        rel_path_str = str(item_path.relative_to(directory_path))

        # Check if the item itself or any of its parent directories (up to the root_dir) are in exclude_dirs_set
        is_in_excluded_dir = False
        # Check current item if it's a directory and in exclude_dirs_set
        if item_path.is_dir() and item_path.name in exclude_dirs_set:
            if rel_path_str not in results["summary"]["directories_explicitly_skipped"]:
                 results["summary"]["directories_explicitly_skipped"].append(rel_path_str)
            # Do not descend further into this directory by virtue of how rglob works if we could prune.
            # With rglob, we simply skip files found within it later.
            # For now, we just mark the directory and files within will be skipped.
            is_in_excluded_dir = True


        # Check parents
        current_check_path = item_path.parent
        while current_check_path != directory_path and current_check_path != current_check_path.parent : # Stop before root_dir or filesystem root
            if current_check_path.name in exclude_dirs_set:
                is_in_excluded_dir = True
                # Add the top-most excluded directory found in the path to the list
                # This logic is a bit tricky with rglob as we get all paths.
                # A simpler approach is to check each file's path parts.
                break
            current_check_path = current_check_path.parent
        
        # Simpler check for file's path parts
        path_parts = set(item_path.relative_to(directory_path).parts)
        if any(part in exclude_dirs_set for part in path_parts):
            is_in_excluded_dir = True


        if item_path.is_file():
            # First, check if the file path matches the provided regex
            if not compiled_regex.search(rel_path_str):
                results["summary"]["total_files_skipped"] += 1
                results["files"].append({
                    "path": rel_path_str,
                    "tokens": None,
                    "status": f"Skipped (did not match regex: '{file_regex_pattern}')"
                })
                continue

            if is_in_excluded_dir:
                results["summary"]["total_files_skipped"] += 1
                # Find which excluded dir caused this
                offending_dir_part = "unknown"
                for part in item_path.relative_to(directory_path).parts:
                    if part in exclude_dirs_set:
                        offending_dir_part = part
                        break
                results["files"].append({
                    "path": rel_path_str,
                    "tokens": None,
                    "status": f"Skipped (in or under excluded directory '{offending_dir_part}')"
                })
                continue

            # Basic progress indication, can be made optional
            # print(f"Processing: {rel_path_str}...")

            token_count, status_msg = process_file(item_path, current_exclude_extensions_set)

            if token_count is not None:
                results["files"].append({
                    "path": rel_path_str,
                    "tokens": token_count,
                    "status": status_msg if status_msg else "Processed"
                })
                results["summary"]["total_tokens"] += token_count
                results["summary"]["total_files_processed_successfully"] += 1
            else:
                results["files"].append({
                    "path": rel_path_str,
                    "tokens": None,
                    "status": status_msg or "Skipped (Unknown reason)" # Should have a reason from process_file
                })
                results["summary"]["total_files_with_errors"] +=1 # Or map to skipped based on reason
                                                                 # Let's count errors separately from skips
        elif item_path.is_dir() and item_path.name in exclude_dirs_set and rel_path_str not in results["summary"]["directories_explicitly_skipped"]:
            # This ensures directories directly named in exclude_dirs_set are listed even if empty.
            results["summary"]["directories_explicitly_skipped"].append(rel_path_str)


    # Sort files by path for consistent output
    results["files"].sort(key=lambda x: x["path"])
    results["summary"]["directories_explicitly_skipped"] = sorted(list(set(results["summary"]["directories_explicitly_skipped"])))


    return results

if __name__ == '__main__':
    # Example usage for testing this module directly
    print("Testing calculator module...")
    from tempfile import TemporaryDirectory
    
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "file1.py").write_text("def hello():\n  print('world') # Python comment")
        (tmpdir_path / "file2.txt").write_text("This is some text with numbers 123 and symbols !@#.")
        (tmpdir_path / "binary_file.bin").write_bytes(b"binary\0content\0nulls")
        (tmpdir_path / "empty_file.py").write_text("")
        (tmpdir_path / "whitespace_file.js").write_text("   \n\t  \n ")
        (tmpdir_path / "Dockerfile").write_text("FROM python:3.9-slim\nWORKDIR /app")
        (tmpdir_path / "file_to_exclude.log").write_text("This is a log file and should be excluded.")
        (tmpdir_path / "another_to_exclude.tmp").write_text("Temporary data.")
        (tmpdir_path / "document.Py").write_text("# Case test for exclusion")

        
        sub_dir = tmpdir_path / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.js").write_text("console.log('test from subdir'); // JS comment")
        
        excluded_dir_git = tmpdir_path / ".git"
        excluded_dir_git.mkdir()
        (excluded_dir_git / "config").write_text("some git config data")
        (excluded_dir_git / "HEAD").write_text("ref: refs/heads/main")

        excluded_dir_node = tmpdir_path / "node_modules"
        excluded_dir_node.mkdir()
        (excluded_dir_node / "some_package.js").write_text("var x = 1;")


        print(f"\nProcessing test directory: {tmpdir_path} (with regex and extension exclusions)\n")
        data = process_directory(
            str(tmpdir_path),
            file_regex_pattern=r".*(\.(py|txt|js)$|Dockerfile|Makefile)", # Test regex
            exclude_extensions={"\.log", "\.tmp", "\.Py"} # Test case-insensitivity and leading dot
        )

        print("\n--- Results ---")
        for f_data in data["files"]:
            print(f"File: {f_data['path']}, Tokens: {f_data['tokens']}, Status: {f_data['status']}")
        
        print("\n--- Summary ---")
        print(f"Total files processed successfully: {data['summary']['total_files_processed_successfully']}")
        print(f"Total files with errors: {data['summary']['total_files_with_errors']}")
        print(f"Total files skipped (binary, excluded dir, etc.): {data['summary']['total_files_skipped']}")
        print(f"Total tokens: {data['summary']['total_tokens']}")
        if data['summary']['directories_explicitly_skipped']:
            print(f"Directories explicitly skipped (name matched exclude list): {data['summary']['directories_explicitly_skipped']}")
        if data["errors"]:
            print("\n--- General Errors ---")
            for err in data["errors"]:
                print(err)

        # Test with a non-existent directory
        print("\n--- Testing non-existent directory ---")
        non_existent_data = process_directory("a_s_d_f_path_does_not_exist_z_x_c_v", r".*") # Provide a dummy regex
        if non_existent_data["errors"]:
            print(f"Error for non-existent dir: {non_existent_data['errors'][0]}")
            assert "not a valid directory" in non_existent_data['errors'][0]
        else:
            print("Test failed: No error for non-existent directory.")

        # Test with an invalid regex
        print("\n--- Testing invalid regex ---")
        invalid_regex_data = process_directory(str(tmpdir_path), file_regex_pattern="*invalid[")
        if invalid_regex_data["errors"]:
            print(f"Error for invalid regex: {invalid_regex_data['errors'][0]}")
            assert "Invalid regex pattern" in invalid_regex_data['errors'][0]
        else:
            print("Test failed: No error for invalid regex.")
        
        print("\nCalculator module test completed.")
        # Test with an invalid regex
        print("\n--- Testing invalid regex ---")
        invalid_regex_data = process_directory(str(tmpdir_path), file_regex_pattern="*invalid[")
        if invalid_regex_data["errors"]:
            print(f"Error for invalid regex: {invalid_regex_data['errors'][0]}")
            assert "Invalid regex pattern" in invalid_regex_data['errors'][0]
        else:
            print("Test failed: No error for invalid regex.")
        
        print("\nCalculator module test completed.")
        # Test with an invalid regex
        print("\n--- Testing invalid regex ---")
        invalid_regex_data = process_directory(str(tmpdir_path), file_regex_pattern="*invalid[")
        if invalid_regex_data["errors"]:
            print(f"Error for invalid regex: {invalid_regex_data['errors'][0]}")
            assert "Invalid regex pattern" in invalid_regex_data['errors'][0]
        else:
            print("Test failed: No error for invalid regex.")
        
        print("\nCalculator module test completed.")
        # Test with an invalid regex
        print("\n--- Testing invalid regex ---")
        invalid_regex_data = process_directory(str(tmpdir_path), file_regex_pattern="*invalid[")
        if invalid_regex_data["errors"]:
            print(f"Error for invalid regex: {invalid_regex_data['errors'][0]}")
            assert "Invalid regex pattern" in invalid_regex_data['errors'][0]
        else:
            print("Test failed: No error for invalid regex.")
        
        print("\nCalculator module test completed.")
