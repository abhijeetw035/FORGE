import tree_sitter
from tree_sitter import Language, Parser
import os

class ASTParser:
    def __init__(self):
        self.parser = None
        self.language = None
        
    def setup_python(self):
        pass
    
    def parse_file(self, source_code: str):
        if not self.parser:
            return None
        
        tree = self.parser.parse(bytes(source_code, "utf8"))
        return tree
    
    def extract_functions(self, tree, source_code: str):
        functions = []
        
        if not tree:
            return functions
        
        def traverse(node):
            if node.type == 'function_definition':
                func_info = self._extract_function_info(node, source_code)
                if func_info:
                    functions.append(func_info)
            
            for child in node.children:
                traverse(child)
        
        traverse(tree.root_node)
        return functions
    
    def _extract_function_info(self, node, source_code: str):
        name_node = None
        params_node = None
        
        for child in node.children:
            if child.type == 'identifier':
                name_node = child
            elif child.type == 'parameters':
                params_node = child
        
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
            if n.type in ['if_statement', 'while_statement', 'for_statement', 'except_clause']:
                complexity += 1
            for child in n.children:
                count_branches(child)
        
        count_branches(node)
        return complexity
