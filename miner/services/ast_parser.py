from tree_sitter import Language, Parser
import os

class ASTParser:
    def __init__(self):
        self.parsers = {}
        self.languages = {}
        self.build_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tree_sitter_builds')
        self.language_so = os.path.join(self.build_dir, 'languages.so')
        
    def setup_language(self, language_name: str):
        if language_name in self.parsers:
            return
        
        if not os.path.exists(self.language_so):
            raise FileNotFoundError(f"Language library not found at {self.language_so}. Run build_languages.py first.")
        
        self.languages[language_name] = Language(self.language_so, language_name)
        self.parsers[language_name] = Parser()
        self.parsers[language_name].set_language(self.languages[language_name])
    
    def setup_python(self):
        self.setup_language('python')
    
    def get_parser(self, file_extension: str):
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',  # JSX uses JavaScript parser
            '.ts': 'javascript',   # TypeScript (if tree-sitter-javascript supports it)
            '.tsx': 'javascript',  # TSX uses JavaScript parser
            '.java': 'java',
            '.go': 'go',
        }
        
        language = extension_map.get(file_extension)
        if not language:
            return None
        
        if language not in self.parsers:
            self.setup_language(language)
        
        return self.parsers.get(language), language
    
    def parse_file(self, source_code: str, file_path: str = None):
        if file_path:
            _, ext = os.path.splitext(file_path)
            parser, _ = self.get_parser(ext) or (None, None)
        else:
            parser = self.parsers.get('python')
        
        if not parser:
            return None
        
        tree = parser.parse(bytes(source_code, "utf8"))
        return tree
    
    def extract_functions(self, tree, source_code: str, language: str = 'python'):
        functions = []
        
        if not tree:
            return functions
        
        # Define all function-like node types for each language
        function_types = {
            'python': ['function_definition'],
            'javascript': [
                'function_declaration', 
                'function_expression',
                'arrow_function',
                'method_definition'
            ],
            'java': ['method_declaration'],
            'go': ['function_declaration'],
        }
        
        func_types = function_types.get(language, ['function_definition'])
        
        def traverse(node):
            if node.type in func_types:
                func_info = self._extract_function_info(node, source_code, language)
                if func_info:
                    functions.append(func_info)
            
            # Also check for variable declarations with function values (const Comp = () => {})
            if language == 'javascript' and node.type == 'variable_declarator':
                # Check if the value is a function
                for child in node.children:
                    if child.type in ['arrow_function', 'function_expression']:
                        func_info = self._extract_function_info(node, source_code, language)
                        if func_info:
                            functions.append(func_info)
                        break
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return functions
    
    def _extract_function_info(self, node, source_code: str, language: str = 'python'):
        name_node = None
        params_node = None
        
        # For variable_declarator (e.g., const MyComponent = () => {}), extract identifier
        if node.type == 'variable_declarator':
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                    break
            # Get params from the function value
            for child in node.children:
                if child.type in ['arrow_function', 'function_expression']:
                    for subchild in child.children:
                        if subchild.type == 'formal_parameters':
                            params_node = subchild
                            break
                    break
        else:
            # Normal function declaration/expression
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                elif child.type == 'parameters' or child.type == 'formal_parameters':
                    params_node = child
                # For method_definition, get property_identifier
                elif language == 'javascript' and child.type == 'property_identifier':
                    name_node = child
        
        if not name_node:
            return None
        
        func_name = source_code[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        params = []
        if params_node:
            for param in params_node.children:
                if param.type == 'identifier':
                    params.append(source_code[param.start_byte:param.end_byte])
                # Handle destructured parameters {prop1, prop2}
                elif param.type == 'object_pattern':
                    params.append(source_code[param.start_byte:param.end_byte])
        
        return {
            'name': func_name,
            'start_line': start_line,
            'end_line': end_line,
            'parameters': params,
            'complexity': self._calculate_complexity(node),
            'lines_of_code': end_line - start_line + 1
        }
    
    def _calculate_complexity(self, node):
        complexity = 1
        
        def count_branches(n):
            nonlocal complexity
            if n.type in ['if_statement', 'while_statement', 'for_statement', 
                         'except_clause', 'elif_clause', 'else_clause',
                         'switch_statement', 'case_statement']:
                complexity += 1
            for child in n.children:
                count_branches(child)
        
        count_branches(node)
        return complexity
