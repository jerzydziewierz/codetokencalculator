from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = ""
readme_path = this_directory / "README.md"
if readme_path.exists():
    long_description = readme_path.read_text()

setup(
    name='codetokencalculator',
    version='0.1.0',
    author='AI Assistant & User',
    author_email='your_email@example.com',
    description='A tool to count LLM input tokens in a code repository for Anthropic Claude models.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    # url='https://github.com/yourusername/codetokencalculator', # Replace with your actual URL
    packages=find_packages(exclude=['tests*']),
    install_requires=[
        'tiktoken>=0.5.1', # tiktoken supports cl100k_base, used by Claude models
    ],
    entry_points={
        'console_scripts': [
            'codetokencalculator=codetokencalculator.main:main_cli',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License', # Assuming MIT, you can change this
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Text Processing :: General',
    ],
    python_requires='>=3.7',
)