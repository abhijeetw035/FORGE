import os
import subprocess
from tree_sitter import Language
import git

BUILD_DIR = os.path.join(os.path.dirname(__file__), 'tree_sitter_builds')
os.makedirs(BUILD_DIR, exist_ok=True)

LANGUAGES = {
    'python': 'https://github.com/tree-sitter/tree-sitter-python',
    'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript',
    'java': 'https://github.com/tree-sitter/tree-sitter-java',
    'go': 'https://github.com/tree-sitter/tree-sitter-go',
}

VERSIONS = {
    'python': 'v0.21.0',
    'javascript': 'v0.21.0',
    'java': 'v0.21.0',
    'go': 'v0.21.0',
}

language_paths = []

for lang_name, repo_url in LANGUAGES.items():
    lang_path = os.path.join(BUILD_DIR, f'tree-sitter-{lang_name}')
    version = VERSIONS[lang_name]
    
    if not os.path.exists(lang_path):
        print(f"Cloning tree-sitter-{lang_name}...")
        repo = git.Repo.clone_from(repo_url, lang_path)
        print(f"Checking out {version}...")
        repo.git.checkout(version)
    else:
        print(f"tree-sitter-{lang_name} already exists, updating to {version}...")
        repo = git.Repo(lang_path)
        repo.git.fetch()
        repo.git.checkout(version)
    
    language_paths.append(lang_path)

LANGUAGE_SO = os.path.join(BUILD_DIR, 'languages.so')

print(f"Building language library...")
Language.build_library(LANGUAGE_SO, language_paths)

print(f"Language library built successfully at {LANGUAGE_SO}")
