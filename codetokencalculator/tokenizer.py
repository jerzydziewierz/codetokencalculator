# codetokencalculator/codetokencalculator/tokenizer.py

"""
Handles the tokenization of text content using tiktoken,
specifically configured for Anthropic Claude models.
"""

import tiktoken

# The encoding used by Claude models like Claude 2, Claude 2.1, Claude Instant, Claude 3 Opus, Sonnet, Haiku
# See: https://github.com/anthropics/anthropic-tokenizer-python (points to tiktoken)
# And: https://platform.openai.com/docs/guides/embeddings/how-can-i-tell-how-many-tokens-a-string-has
# The cl100k_base encoding is used by gpt-4, gpt-3.5-turbo, text-embedding-ada-002, and also Claude models.
CLAUDE_ENCODING_MODEL = "cl100k_base"

# Global tokenizer instance to avoid reloading it repeatedly
_tokenizer = None

def _get_tokenizer():
    """
    Initializes and returns the tiktoken tokenizer for Claude models.
    Caches the tokenizer instance for efficiency.
    """
    global _tokenizer
    if _tokenizer is None:
        try:
            _tokenizer = tiktoken.get_encoding(CLAUDE_ENCODING_MODEL)
        except Exception as e:
            # This might happen if the encoding name is wrong or tiktoken has issues
            # For cl100k_base, it should generally be available as it's a common one.
            print(f"Error initializing tokenizer: {e}")
            raise RuntimeError(f"Could not load the tokenizer '{CLAUDE_ENCODING_MODEL}'. Ensure tiktoken is installed correctly.") from e
    return _tokenizer

def count_tokens_for_text(text_content: str) -> int:
    """
    Counts the number of tokens in the given text content using a Claude-compatible tokenizer.

    Args:
        text_content: The string content to tokenize.

    Returns:
        The number of tokens.
        Returns 0 if the text_content is empty or None.
    
    Raises:
        RuntimeError: If the tokenizer cannot be initialized.
    """
    if not text_content:
        return 0
    
    tokenizer = _get_tokenizer()
    tokens = tokenizer.encode(
        text_content,
        # disallowed_special=() # Allow all special tokens for counting purposes, consistent with Claude's API
    )
    return len(tokens)

if __name__ == '__main__':
    # Example usage, can be run with `python -m codetokencalculator.tokenizer`
    sample_text_1 = "This is a sample sentence."
    sample_text_2 = "def hello_world():\n  print('Hello, world!')\n"
    sample_text_3 = """
    This is a more complex example
    with multiple lines, special characters like !@#$%^&*()_+-={}[]|\:"';<>,.?/
    and some unicode characters: 你好, दुनिया, Привет
    """
    empty_text = ""
    
    print(f"Tokenizer: {CLAUDE_ENCODING_MODEL}")
    
    tokens_1 = count_tokens_for_text(sample_text_1)
    print(f"'{sample_text_1}' -> Tokens: {tokens_1}")

    tokens_2 = count_tokens_for_text(sample_text_2)
    print(f"'{sample_text_2}' -> Tokens: {tokens_2}")

    tokens_3 = count_tokens_for_text(sample_text_3)
    print(f"Sample text 3 -> Tokens: {tokens_3}")

    tokens_empty = count_tokens_for_text(empty_text)
    print(f"Empty text -> Tokens: {tokens_empty}")

    # Test with a larger piece of code
    large_code_sample = """
import os
import sys

class MyClass:
    def __init__(self, name):
        self.name = name

    def greet(self):
        print(f"Hello, {self.name}!")

def main_function(args):
    if len(args) > 1:
        instance = MyClass(args[1])
        instance.greet()
    else:
        print("Please provide a name.")

if __name__ == "__main__":
    main_function(sys.argv)
"""
    tokens_large_code = count_tokens_for_text(large_code_sample)
    print(f"Large code sample -> Tokens: {tokens_large_code}")