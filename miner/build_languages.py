import os
import subprocess
from tree_sitter import Language

BUILD_DIR = os.path.join(os.path.dirname(__file__), 'tree_sitter_builds')
os.makedirs(BUILD_DIR, exist_ok=True)

PYTHON_REPO = 'https://github.com/tree-sitter/tree-sitter-python'
PYTHON_PATH = os.path.join(BUILD_DIR, 'tree-sitter-python')

if not os.path.exists(PYTHON_PATH):
    print(f"Cloning tree-sitter-python...")
    subprocess.run(['git', 'clone', PYTHON_REPO, PYTHON_PATH], check=True)

LANGUAGE_SO = os.path.join(BUILD_DIR, 'languages.so')

print(f"Building language library...")
Language.build_library(
    LANGUAGE_SO,
    [PYTHON_PATH]
)

print(f"Language library built successfully at {LANGUAGE_SO}")
