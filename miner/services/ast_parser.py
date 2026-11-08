from tree_sitter import Language, Parser
import os
import hashlib
import re
from typing import Optional, List, Dict, Any


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
            res = self.get_parser(ext)
            parser = res[0] if res else None
        else:
            parser = self.parsers.get('python')
        
        if not parser:
            return None
        
        tree = parser.parse(bytes(source_code, "utf8"))
        return tree
    
    def extract_functions(self, tree, source_code: str, language: str = 'python') -> List[Dict[str, Any]]:
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
            'go': ['function_declaration', 'method_declaration'],
        }
        
        func_types = function_types.get(language, ['function_definition'])
        
        # Class node types per language for computing qualified_name
        class_types = {
            'python': ['class_definition'],
            'javascript': ['class_declaration', 'class_expression'],
            'java': ['class_declaration', 'interface_declaration', 'enum_declaration', 'record_declaration'],
            'go': [],
        }
        enclosing_classes = class_types.get(language, [])
        
        scope_stack: List[str] = []
        
        def get_class_name(n) -> Optional[str]:
            name_node = n.child_by_field_name('name')
            if name_node:
                return source_code[name_node.start_byte:name_node.end_byte]
            for child in n.children:
                if child.type in ['identifier', 'type_identifier']:
                    return source_code[child.start_byte:child.end_byte]
            return None

        def traverse(node):
            is_class = node.type in enclosing_classes
            c_name = None
            if is_class:
                c_name = get_class_name(node)
                if c_name:
                    scope_stack.append(c_name)

            if node.type in func_types:
                func_info = self._extract_function_info(node, source_code, language, scope_stack)
                if func_info:
                    functions.append(func_info)
            elif language == 'javascript' and node.type == 'variable_declarator':
                # Check if the value is a function
                for child in node.children:
                    if child.type in ['arrow_function', 'function_expression']:
                        func_info = self._extract_function_info(node, source_code, language, scope_stack)
                        if func_info:
                            functions.append(func_info)
                        break
            
            for child in node.children:
                traverse(child)

            if is_class and c_name and scope_stack and scope_stack[-1] == c_name:
                scope_stack.pop()
        
        traverse(tree.root_node)
        return functions
    
    def _extract_function_info(self, node, source_code: str, language: str = 'python',
                               scope_stack: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        name_node = None
        params_node = None
        go_receiver_type = None

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
                        if subchild.type in ['formal_parameters', 'parameters']:
                            params_node = subchild
                            break
                    break
        elif language == 'go' and node.type == 'method_declaration':
            # In Go method declarations: func (s *Server) Start(p int) error
            # First parameter_list is receiver, second is method parameters
            param_lists = [c for c in node.children if c.type == 'parameter_list']
            if param_lists:
                receiver_list = param_lists[0]
                go_receiver_type = self._extract_go_receiver(receiver_list, source_code)
                if len(param_lists) > 1:
                    params_node = param_lists[1]
            for child in node.children:
                if child.type in ['field_identifier', 'identifier']:
                    name_node = child
                    break
        else:
            # Normal function declaration/expression
            for child in node.children:
                if child.type == 'identifier':
                    name_node = child
                elif child.type in ['parameters', 'formal_parameters', 'parameter_list']:
                    params_node = child
                # For method_definition (JS), get property_identifier
                elif language == 'javascript' and child.type == 'property_identifier':
                    name_node = child

        if not name_node:
            return None
        
        func_name = source_code[name_node.start_byte:name_node.end_byte]
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        
        # Qualified name computation
        if go_receiver_type:
            qualified_name = f"{go_receiver_type}.{func_name}"
        elif scope_stack:
            qualified_name = f"{'.'.join(scope_stack)}.{func_name}"
        else:
            qualified_name = func_name

        params = []
        if params_node:
            for param in params_node.children:
                if param.type == 'identifier':
                    params.append(source_code[param.start_byte:param.end_byte])
                elif param.type in ['formal_parameter', 'parameter_declaration']:
                    for sub in param.children:
                        if sub.type == 'identifier':
                            params.append(source_code[sub.start_byte:sub.end_byte])
                            break
                elif param.type == 'object_pattern':
                    params.append(source_code[param.start_byte:param.end_byte])
        
        # Extract body node and token-based normalized representation
        body_node = self._get_body_node(node, language)
        body_tokens = self._extract_body_tokens(body_node, source_code, language)
        body_hash = self._calculate_body_hash(body_tokens)
        
        return {
            'name': func_name,
            'qualified_name': qualified_name,
            'start_line': start_line,
            'end_line': end_line,
            'parameters': params,
            'complexity': self._calculate_complexity(node),
            'lines_of_code': end_line - start_line + 1,
            'body_hash': body_hash,
            'body_tokens': body_tokens,
            'signature_hash': self._signature_hash(func_name, params, language),
        }

    def _extract_go_receiver(self, receiver_list_node, source_code: str) -> Optional[str]:
        for child in receiver_list_node.children:
            if child.type == 'parameter_declaration':
                for sub in child.children:
                    if sub.type == 'type_identifier':
                        return source_code[sub.start_byte:sub.end_byte]
                    elif sub.type == 'pointer_type':
                        for p_sub in sub.children:
                            if p_sub.type == 'type_identifier':
                                return source_code[p_sub.start_byte:p_sub.end_byte]
        return None

    def _get_body_node(self, node, language: str):
        """
        Locate the body node of a function across different languages.
        Excludes the function header/signature.
        """
        if node.type == 'variable_declarator':
            for child in node.children:
                if child.type in ['arrow_function', 'function_expression']:
                    body = child.child_by_field_name('body')
                    if body:
                        return body
                    for sub in child.children:
                        if sub.type in ['statement_block', 'block']:
                            return sub
                    return child

        body = node.child_by_field_name('body')
        if body:
            return body

        for child in node.children:
            if child.type in ['block', 'statement_block']:
                return child

        return node

    def _extract_body_tokens(self, body_node, source_code: str, language: str) -> List[str]:
        """
        Walk the function's body Tree-sitter node recursively.
        - Skip comment nodes (node type contains 'comment').
        - Skip Python docstrings: expression_statement whose only named child is a string
          and which is the first named child of the function's body block.
        - Collect the text of leaf nodes (child_count == 0) in order.
        """
        if not body_node:
            return []

        tokens: List[str] = []

        # Identify Python docstring node if present
        docstring_node = None
        if language == 'python' and body_node.type == 'block':
            for child in body_node.children:
                if child.is_named:
                    if child.type == 'expression_statement':
                        named_children = [c for c in child.children if c.is_named]
                        if len(named_children) == 1 and named_children[0].type == 'string':
                            docstring_node = child
                    break

        def walk(n):
            if 'comment' in n.type:
                return
            if docstring_node is not None and n == docstring_node:
                return
            if n.child_count == 0:
                text = source_code[n.start_byte:n.end_byte].strip()
                if text:
                    tokens.append(text)
                return
            for child in n.children:
                walk(child)

        walk(body_node)
        return tokens

    def _calculate_body_hash(self, body_tokens: List[str]) -> str:
        """
        SHA-256 of leaf tokens joined by a single space.
        """
        joined = " ".join(body_tokens)
        return hashlib.sha256(joined.encode('utf-8')).hexdigest()[:16]

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

    @staticmethod
    def _signature_hash(name: str, params: list, language: str) -> str:
        """
        SHA-256 of "<language>:<name>(<param1>,<param2>,…)".
        """
        sig = f"{language}:{name}({','.join(params)})"
        return hashlib.sha256(sig.encode('utf-8')).hexdigest()[:16]
