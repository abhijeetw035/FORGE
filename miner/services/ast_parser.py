from tree_sitter import Language, Parser
import os
import hashlib
import re
from typing import Optional, List, Dict, Any


# ── McCabe cyclomatic complexity: 1 + number of decision points ──────────────
# Verified against the tree-sitter grammars in use (see tests/test_complexity.py).
# NOT counted: else/default, the switch statement itself, finally, plain
# function calls.  Short-circuit operators are handled separately below.
DECISION_NODES = {
    'python': {
        'if_statement', 'elif_clause', 'for_statement', 'while_statement',
        'except_clause', 'conditional_expression',
        'boolean_operator',                      # each `and` / `or`
        'if_clause', 'for_in_clause',            # comprehensions / generators
        'case_clause',                           # match/case (wildcard `_` excluded below)
    },
    'javascript': {
        'if_statement', 'for_statement', 'for_in_statement', 'while_statement',
        'do_statement', 'catch_clause', 'ternary_expression',
        'switch_case',                           # `switch_default` is a different node
    },
    'java': {
        'if_statement', 'for_statement', 'enhanced_for_statement', 'while_statement',
        'do_statement', 'catch_clause', 'ternary_expression',
        'switch_label',                          # `default` labels excluded below
    },
    'go': {
        'if_statement', 'for_statement',
        'expression_case', 'type_case', 'communication_case',   # `default_case` is separate
    },
}
SHORT_CIRCUIT_OPS = {
    'javascript': {'&&', '||', '??'},
    'java': {'&&', '||'},
    'go': {'&&', '||'},
}
# Function-like nodes; one that is scored on its own is NOT counted toward its parent.
NESTED_FUNCS = {
    'function_definition', 'function_declaration', 'method_declaration',
    'method_definition', 'arrow_function', 'function_expression', 'func_literal',
}


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
        
        source_bytes = source_code.encode("utf-8")
        tree = parser.parse(source_bytes)
        return tree

    @staticmethod
    def _node_text(node, source_bytes: bytes) -> str:
        """Return the UTF-8 text covered by a tree-sitter node using byte offsets."""
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    
    def extract_functions(self, tree, source_code: str, language: str = 'python') -> List[Dict[str, Any]]:
        functions = []
        
        if not tree:
            return functions

        # Encode once; all node.start_byte/end_byte are byte offsets into this
        source_bytes = source_code.encode("utf-8")
        
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
                return self._node_text(name_node, source_bytes)
            for child in n.children:
                if child.type in ['identifier', 'type_identifier']:
                    return self._node_text(child, source_bytes)
            return None

        def traverse(node):
            is_class = node.type in enclosing_classes
            c_name = None
            if is_class:
                c_name = get_class_name(node)
                if c_name:
                    scope_stack.append(c_name)

            if node.type in func_types:
                func_info = self._extract_function_info(node, source_bytes, language, scope_stack)
                if func_info:
                    functions.append(func_info)
            elif language == 'javascript' and node.type == 'variable_declarator':
                # Check if the value is a function
                for child in node.children:
                    if child.type in ['arrow_function', 'function_expression']:
                        func_info = self._extract_function_info(node, source_bytes, language, scope_stack)
                        if func_info:
                            functions.append(func_info)
                        break
            
            for child in node.children:
                traverse(child)

            if is_class and c_name and scope_stack and scope_stack[-1] == c_name:
                scope_stack.pop()
        
        traverse(tree.root_node)
        return functions
    
    def _extract_function_info(self, node, source_bytes: bytes, language: str = 'python',
                               scope_stack: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        name_node = None
        params_node = None
        go_receiver_type = None

        # A bare arrow function has no name of its own: its first `identifier`
        # child is its (single, unparenthesised) PARAMETER, e.g. `x => x + 1`.
        # Named arrows are extracted through their variable_declarator instead.
        if node.type == 'arrow_function':
            return None

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
                go_receiver_type = self._extract_go_receiver(receiver_list, source_bytes)
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
        
        func_name = self._node_text(name_node, source_bytes)
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
                    params.append(self._node_text(param, source_bytes))
                elif param.type in ['formal_parameter', 'parameter_declaration']:
                    for sub in param.children:
                        if sub.type == 'identifier':
                            params.append(self._node_text(sub, source_bytes))
                            break
                elif param.type == 'object_pattern':
                    params.append(self._node_text(param, source_bytes))
        
        # Extract body node and token-based normalized representation
        body_node = self._get_body_node(node, language)
        body_tokens = self._extract_body_tokens(body_node, source_bytes, language)
        body_hash = self._calculate_body_hash(body_tokens)
        
        return {
            'name': func_name,
            'qualified_name': qualified_name,
            'start_line': start_line,
            'end_line': end_line,
            'parameters': params,
            'complexity': self._calculate_complexity(node, language),
            'lines_of_code': end_line - start_line + 1,
            'body_hash': body_hash,
            'body_tokens': body_tokens,
            'signature_hash': self._signature_hash(func_name, params, language),
        }

    def _extract_go_receiver(self, receiver_list_node, source_bytes: bytes) -> Optional[str]:
        for child in receiver_list_node.children:
            if child.type == 'parameter_declaration':
                for sub in child.children:
                    if sub.type == 'type_identifier':
                        return self._node_text(sub, source_bytes)
                    elif sub.type == 'pointer_type':
                        for p_sub in sub.children:
                            if p_sub.type == 'type_identifier':
                                return self._node_text(p_sub, source_bytes)
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

    def _extract_body_tokens(self, body_node, source_bytes: bytes, language: str) -> List[str]:
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
                text = self._node_text(n, source_bytes).strip()
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

    @staticmethod
    def _is_scored_function(n) -> bool:
        """
        True if `n` is a function that extract_functions() records on its own
        (so its branches belong to it, not to an enclosing function).
        Anonymous functions are not recorded, so their branches stay with the
        enclosing function; a function assigned to a variable is named by it.
        """
        if n.type not in NESTED_FUNCS:
            return False
        if n.parent is not None and n.parent.type == 'variable_declarator':
            return True
        if n.type == 'arrow_function':
            return False                          # an identifier child is a parameter, not a name
        return any(c.type in ('identifier', 'field_identifier', 'property_identifier')
                   for c in n.children)

    def _calculate_complexity(self, node, language: str = 'python', source_bytes: Optional[bytes] = None):
        """
        McCabe cyclomatic complexity = 1 + decision points.
        Counts real branches only (not else/default/the switch itself), counts
        short-circuit && || ?? (and/or in Python), and does not descend into
        nested functions that are scored separately.
        """
        rules = DECISION_NODES.get(language, DECISION_NODES['python'])
        short_ops = SHORT_CIRCUIT_OPS.get(language, set())

        # `const f = () => {...}`: the declarator wraps the real function node.
        root = node
        if node.type == 'variable_declarator':
            for child in node.children:
                if child.type in ('arrow_function', 'function_expression'):
                    root = child
                    break

        count = 1
        stack = [root]
        while stack:
            n = stack.pop()
            if n is not root and self._is_scored_function(n):
                continue                          # scored separately
            t = n.type
            if t in rules:
                if t == 'switch_label' and n.text.lstrip().startswith(b'default'):
                    pass                          # Java default is not a branch
                elif t == 'case_clause' and re.fullmatch(rb'case\s+_', n.text.split(b':', 1)[0].strip()):
                    pass                          # Python wildcard `case _:` is the default
                else:
                    count += 1
            elif t == 'binary_expression' and short_ops:
                op = n.child_by_field_name('operator')
                if op is not None and op.type in short_ops:
                    count += 1
            stack.extend(n.children)
        return count

    @staticmethod
    def _signature_hash(name: str, params: list, language: str) -> str:
        """
        SHA-256 of "<language>:<name>(<param1>,<param2>,…)".
        """
        sig = f"{language}:{name}({','.join(params)})"
        return hashlib.sha256(sig.encode('utf-8')).hexdigest()[:16]
