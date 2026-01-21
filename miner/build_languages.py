import os
import subprocess
from tree_sitter import Language

BUILD_DIR = os.path.join(os.path.dirname(__file__), 'tree_sitter_builds')
os.makedirs(BUILD_DIR, exist_ok=True)

LANGUAGES = {
    'python': 'https://github.com/tree-sitter/tree-sitter-python',
    'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript',
    'java': 'https://github.com/tree-sitter/tree-sitter-java',
    'cpp': 'https://github.com/tree-sitter/tree-sitter-cpp',
    'go': 'https://github.com/tree-sitter/tree-sitter-go',
}

language_paths = []

for lang_name, repo_url in LANGUAGES.items():
    lang_path = os.path.join(BUILD_DIR, f'tree-sitter-{lang_name}')
    
    if not os.path.exists(lang_path):
        print(f"Cloning tree-sitter-{lang_name}...")
        subprocess.run(['git', 'clone', '--depth', '1', repo_url, lang_path], check=True)
    else:
        print(f"tree-sitter-{lang_name} already exists, skipping...")
    
    language_paths.append(lang_path)

LANGUAGE_SO = os.path.join(BUILD_DIR, 'languages.so')

print(f"Building language library...")
Language.build_library(LANGUAGE_SO, language_paths)

print(f"Language library built successfully at {LANGUAGE_SO}")
