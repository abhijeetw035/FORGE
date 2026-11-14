import pytest
from services.ast_parser import ASTParser


@pytest.fixture(scope="module")
def parser():
    p = ASTParser()
    p.setup_language('python')
    p.setup_language('javascript')
    p.setup_language('java')
    p.setup_language('go')
    return p


# ============================================================================
# Baseline tests
# ============================================================================

def test_extract_python_functions(parser):
    code = """
def add(a, b):
    return a + b

def multiply(x, y):
    if x == 0:
        return 0
    return x * y
"""
    tree = parser.parse_file(code, "test.py")
    funcs = parser.extract_functions(tree, code, "python")
    assert len(funcs) == 2
    assert funcs[0]['name'] == 'add'
    assert funcs[0]['qualified_name'] == 'add'
    assert funcs[0]['parameters'] == ['a', 'b']
    assert funcs[0]['complexity'] == 1

    assert funcs[1]['name'] == 'multiply'
    assert funcs[1]['qualified_name'] == 'multiply'
    assert funcs[1]['parameters'] == ['x', 'y']
    assert funcs[1]['complexity'] == 2


def test_extract_javascript_functions(parser):
    code = """
function greet(name) {
    return "Hello " + name;
}
const add = (a, b) => {
    return a + b;
};
"""
    tree = parser.parse_file(code, "test.js")
    funcs = parser.extract_functions(tree, code, "javascript")
    names = [f['name'] for f in funcs]
    assert 'greet' in names
    assert 'add' in names


def test_extract_java_methods(parser):
    code = """
class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
    tree = parser.parse_file(code, "Test.java")
    funcs = parser.extract_functions(tree, code, "java")
    assert len(funcs) == 1
    assert funcs[0]['name'] == 'add'
    assert funcs[0]['qualified_name'] == 'Calculator.add'


def test_extract_go_functions(parser):
    code = """
package main
func Add(a int, b int) int {
    return a + b
}
"""
    tree = parser.parse_file(code, "test.go")
    funcs = parser.extract_functions(tree, code, "go")
    assert len(funcs) == 1
    assert funcs[0]['name'] == 'Add'
    assert funcs[0]['qualified_name'] == 'Add'


# ============================================================================
# Phase 1: Token-based normalization tests
# ============================================================================

def test_reindentation_same_hash(parser):
    """Reformatting/re-indenting should give the same body_hash."""
    code1 = """def foo():
    x = 1
    y = 2
    return x + y
"""
    code2 = """def foo():
        x = 1
        y = 2
        return x + y
"""
    tree1 = parser.parse_file(code1, "test.py")
    tree2 = parser.parse_file(code2, "test.py")
    f1 = parser.extract_functions(tree1, code1, "python")[0]
    f2 = parser.extract_functions(tree2, code2, "python")[0]
    assert f1['body_hash'] == f2['body_hash']


def test_single_line_comment_same_hash(parser):
    """Adding single-line comments should not change body_hash."""
    code1 = """def foo():
    # first comment
    x = 1
    return x
"""
    code2 = """def foo():
    x = 1
    # different comment
    return x
"""
    tree1 = parser.parse_file(code1, "test.py")
    tree2 = parser.parse_file(code2, "test.py")
    f1 = parser.extract_functions(tree1, code1, "python")[0]
    f2 = parser.extract_functions(tree2, code2, "python")[0]
    assert f1['body_hash'] == f2['body_hash']


def test_block_comment_same_hash(parser):
    """Adding /* */ block comments should give the same body_hash."""
    code1 = """function calculate(a, b) {
    /* calculate sum */
    return a + b;
}"""
    code2 = """function calculate(a, b) {
    /* different block comment
       spanning multiple lines */
    return a + b;
}"""
    tree1 = parser.parse_file(code1, "test.js")
    tree2 = parser.parse_file(code2, "test.js")
    f1 = parser.extract_functions(tree1, code1, "javascript")[0]
    f2 = parser.extract_functions(tree2, code2, "javascript")[0]
    assert f1['body_hash'] == f2['body_hash']


def test_docstring_same_hash(parser):
    """Adding or changing Python docstrings should give the same body_hash."""
    code1 = '''def compute(n):
    """Compute something important."""
    return n * 2
'''
    code2 = '''def compute(n):
    """Different docstring explanation."""
    return n * 2
'''
    code3 = '''def compute(n):
    return n * 2
'''
    tree1 = parser.parse_file(code1, "test.py")
    tree2 = parser.parse_file(code2, "test.py")
    tree3 = parser.parse_file(code3, "test.py")
    f1 = parser.extract_functions(tree1, code1, "python")[0]
    f2 = parser.extract_functions(tree2, code2, "python")[0]
    f3 = parser.extract_functions(tree3, code3, "python")[0]
    assert f1['body_hash'] == f2['body_hash']
    assert f1['body_hash'] == f3['body_hash']


def test_python_floor_division_different_hash(parser):
    """Python x = a // b vs x = a // c must produce DIFFERENT body_hash."""
    code1 = """def div(a, b, c):
    x = a // b
    return x
"""
    code2 = """def div(a, b, c):
    x = a // c
    return x
"""
    tree1 = parser.parse_file(code1, "test.py")
    tree2 = parser.parse_file(code2, "test.py")
    f1 = parser.extract_functions(tree1, code1, "python")[0]
    f2 = parser.extract_functions(tree2, code2, "python")[0]
    assert f1['body_hash'] != f2['body_hash']


def test_url_string_different_hash(parser):
    """'https://a.com' vs 'https://b.com' must produce DIFFERENT body_hash."""
    code1 = """function getUrl() {
    const url = "https://a.com";
    return url;
}"""
    code2 = """function getUrl() {
    const url = "https://b.com";
    return url;
}"""
    tree1 = parser.parse_file(code1, "test.js")
    tree2 = parser.parse_file(code2, "test.js")
    f1 = parser.extract_functions(tree1, code1, "javascript")[0]
    f2 = parser.extract_functions(tree2, code2, "javascript")[0]
    assert f1['body_hash'] != f2['body_hash']


def test_hex_color_string_different_hash(parser):
    """'#fff' vs '#000' must produce DIFFERENT body_hash."""
    code1 = """def getColor():
    return "#fff"
"""
    code2 = """def getColor():
    return "#000"
"""
    tree1 = parser.parse_file(code1, "test.py")
    tree2 = parser.parse_file(code2, "test.py")
    f1 = parser.extract_functions(tree1, code1, "python")[0]
    f2 = parser.extract_functions(tree2, code2, "python")[0]
    assert f1['body_hash'] != f2['body_hash']


def test_body_tokens_exclude_header(parser):
    """body_tokens must exclude function name and parameters."""
    code = """def my_func(arg1, arg2):
    res = arg1 + arg2
    return res
"""
    tree = parser.parse_file(code, "test.py")
    f = parser.extract_functions(tree, code, "python")[0]
    tokens = f['body_tokens']
    assert 'def' not in tokens
    assert 'my_func' not in tokens
    assert 'arg1' in tokens
    assert 'res' in tokens
    assert 'return' in tokens


# ============================================================================
# Phase 2: Qualified names tests
# ============================================================================

def test_qualified_names_python_classes(parser):
    code = """
class Parser:
    def __init__(self):
        pass
    def parse(self):
        return 42

class Serializer:
    def __init__(self):
        pass

def standalone():
    pass
"""
    tree = parser.parse_file(code, "test.py")
    funcs = parser.extract_functions(tree, code, "python")
    qnames = {f['qualified_name']: f['name'] for f in funcs}
    assert qnames['Parser.__init__'] == '__init__'
    assert qnames['Parser.parse'] == 'parse'
    assert qnames['Serializer.__init__'] == '__init__'
    assert qnames['standalone'] == 'standalone'


def test_qualified_names_js_classes(parser):
    code = """
class Calculator {
    add(a, b) {
        return a + b;
    }
}
"""
    tree = parser.parse_file(code, "test.js")
    funcs = parser.extract_functions(tree, code, "javascript")
    assert funcs[0]['qualified_name'] == 'Calculator.add'
    assert funcs[0]['name'] == 'add'


def test_qualified_names_go_methods(parser):
    code = """
package main
type Server struct{}

func (s *Server) Start() error {
    return nil
}
func Standalone() {}
"""
    tree = parser.parse_file(code, "test.go")
    funcs = parser.extract_functions(tree, code, "go")
    qnames = {f['qualified_name']: f['name'] for f in funcs}
    assert qnames['Server.Start'] == 'Start'
    assert qnames['Standalone'] == 'Standalone'


# ============================================================================
# Non-ASCII / byte-offset safety tests
# ============================================================================

def test_non_ascii_before_function_python(parser):
    """Non-ASCII chars before a function must not corrupt name/params/body_hash."""
    code = '# café — note: special chars: → ✓\nx = "héllo"\n\ndef compute(val, factor):\n    return val * factor\n'
    tree = parser.parse_file(code, "test.py")
    funcs = parser.extract_functions(tree, code, "python")
    assert len(funcs) == 1
    assert funcs[0]['name'] == 'compute'
    assert funcs[0]['qualified_name'] == 'compute'
    assert funcs[0]['parameters'] == ['val', 'factor']


def test_non_ascii_body_hash_stable_python(parser):
    """Changing only a non-ASCII comment must not change body_hash."""
    code1 = '# café\ndef add(a, b):\n    return a + b\n'
    code2 = '# different — comment with arrows → ✓\ndef add(a, b):\n    return a + b\n'
    t1 = parser.parse_file(code1, "test.py")
    t2 = parser.parse_file(code2, "test.py")
    f1 = parser.extract_functions(t1, code1, "python")[0]
    f2 = parser.extract_functions(t2, code2, "python")[0]
    assert f1['name'] == 'add'
    assert f2['name'] == 'add'
    assert f1['body_hash'] == f2['body_hash']


def test_non_ascii_before_function_javascript(parser):
    """Non-ASCII chars before a JS function must not corrupt its name."""
    code = '// résumé → check\nconst greeting = "héllo";\nfunction myFunc(arg1) {\n    return arg1 + 1;\n}\n'
    tree = parser.parse_file(code, "test.js")
    funcs = parser.extract_functions(tree, code, "javascript")
    names = [f['name'] for f in funcs]
    assert 'myFunc' in names
    # Verify no garbage in the name
    fn = next(f for f in funcs if f['name'] == 'myFunc')
    assert fn['qualified_name'] == 'myFunc'
    assert fn['parameters'] == ['arg1']


def test_non_ascii_before_function_go(parser):
    """Non-ASCII chars before a Go method must not corrupt qualified name or receiver."""
    code = 'package main\n// résumé — Server note →\ntype Server struct{}\nfunc (s *Server) Start() error {\n    return nil\n}\n'
    tree = parser.parse_file(code, "test.go")
    funcs = parser.extract_functions(tree, code, "go")
    assert len(funcs) == 1
    assert funcs[0]['name'] == 'Start'
    assert funcs[0]['qualified_name'] == 'Server.Start'


def test_non_ascii_body_hash_stable_go(parser):
    """Non-ASCII comment change before a Go function must not change body_hash."""
    code1 = 'package main\n// café\nfunc Compute(x int) int {\n    return x * 2\n}\n'
    code2 = 'package main\n// résumé → different\nfunc Compute(x int) int {\n    return x * 2\n}\n'
    t1 = parser.parse_file(code1, "test.go")
    t2 = parser.parse_file(code2, "test.go")
    f1 = parser.extract_functions(t1, code1, "go")[0]
    f2 = parser.extract_functions(t2, code2, "go")[0]
    assert f1['name'] == 'Compute'
    assert f2['name'] == 'Compute'
    assert f1['body_hash'] == f2['body_hash']
