"""McCabe complexity = 1 + decision points. Known answers per language."""
import pytest
from services.ast_parser import ASTParser

EXT = {'python': 'py', 'javascript': 'js', 'java': 'java', 'go': 'go'}


@pytest.fixture(scope="module")
def parser():
    p = ASTParser()
    for lang in EXT:
        p.setup_language(lang)
    return p


def cx(parser, lang, code):
    """{function name: complexity} for every function extracted from `code`."""
    tree = parser.parse_file(code, f"t.{EXT[lang]}")
    return {f['name']: f['complexity'] for f in parser.extract_functions(tree, code, lang)}


def one(parser, lang, code, name='f'):
    return cx(parser, lang, code)[name]


# ── Python ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body,expected", [
    ("    pass", 1),                                                     # empty function
    ("    if a:\n        pass\n    else:\n        pass", 2),              # if/else is 2, not 3
    ("    if a and b:\n        pass", 3),
    ("    return a or b or c", 3),                                       # each and/or
    ("    if a:\n        pass\n    elif b:\n        pass\n    else:\n        pass", 3),
    ("    for i in a:\n        pass\n    while a:\n        pass", 3),
    ("    try:\n        pass\n    except ValueError:\n        pass", 2),
    ("    try:\n        pass\n    except A:\n        pass\n    except B:\n        pass\n    finally:\n        pass", 3),
    ("    return 1 if a else 2", 2),                                     # ternary
    ("    return [i for i in a if i]", 3),                               # for_in_clause + if_clause
    ("    match a:\n        case 1:\n            pass\n        case 2:\n            pass\n"
     "        case 3:\n            pass\n        case _:\n            pass", 4),  # 3 cases + wildcard default
    ("    g = lambda z: z if z else 0\n    return g", 2),                 # lambdas aren't scored separately
])
def test_python_known_answers(parser, body, expected):
    assert one(parser, 'python', f"def f(a, b=None, c=None):\n{body}\n") == expected


def test_python_nested_function_not_counted_toward_parent(parser):
    code = ("def outer(a):\n"
            "    if a:\n        pass\n"
            "    def inner(x):\n"
            "        if x:\n            pass\n"
            "        if x > 1:\n            pass\n"
            "        if x > 2:\n            pass\n"
            "    return inner\n")
    r = cx(parser, 'python', code)
    assert r['outer'] == 2        # its own `if` only
    assert r['inner'] == 4        # scored separately


# ── JavaScript ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("body,expected", [
    ("", 1),
    ("if (a) {} else {}", 2),
    ("if (a && b) {}", 3),
    ("if (a || b) {}", 3),
    ("return a ?? b;", 2),
    ("try { x(); } catch (e) { y(); }", 2),
    ("try { x(); } catch (e) {} finally { z(); }", 2),                 # finally is not a branch
    ("return a ? 1 : 2;", 2),
    ("switch (a) { case 1: break; case 2: break; case 3: break; default: break; }", 4),
    ("for (let i = 0; i < 1; i++) {} for (const k in a) {} for (const v of a) {}", 4),
    ("while (a) {} do {} while (b);", 3),
    ("arr.map(x => x ? 1 : 2);", 2),                                    # anonymous callback stays with parent
])
def test_javascript_known_answers(parser, body, expected):
    assert one(parser, 'javascript', f"function f(a, b, arr) {{ {body} }}") == expected


def test_javascript_nested_named_function_not_counted_toward_parent(parser):
    code = "function outer(a) { if (a) {} function inner(x) { if (x) {} if (x>1) {} } }"
    r = cx(parser, 'javascript', code)
    assert (r['outer'], r['inner']) == (2, 3)


def test_javascript_arrow_assigned_to_variable_is_scored(parser):
    r = cx(parser, 'javascript', "const f = (a) => a ? 1 : 2;\nconst g = (a) => { if (a && a.b) {} };")
    assert (r['f'], r['g']) == (2, 3)


def test_javascript_method_definition(parser):
    code = "class C { m(a) { if (a) {} else if (a > 1) {} else {} } }"
    assert one(parser, 'javascript', code, 'm') == 3                    # if + else-if; else not counted


# ── Java ─────────────────────────────────────────────────────────────────────

def _java(body):
    return f"class T {{ int f(int a, int b, int[] xs) {{ {body} return 0; }} }}"


@pytest.mark.parametrize("body,expected", [
    ("", 1),
    ("if (a > 1) {} else {}", 2),
    ("if (a > 1 && b > 2) {}", 3),
    ("boolean q = a > 1 || b > 2;", 2),
    ("try { a++; } catch (Exception e) {} finally { b++; }", 2),
    ("int x = a > 1 ? 1 : 2;", 2),
    ("for (int v : xs) {}", 2),
    ("for (int i = 0; i < 1; i++) {} while (a > 0) {} do {} while (b > 0);", 4),
    ("switch (a) { case 1: break; case 2: break; case 3: break; default: break; }", 4),
    ("int y = switch (a) { case 1 -> 1; case 2 -> 2; case 3 -> 3; default -> 0; };", 4),
    ("Runnable r = () -> { if (a > 1) {} };", 2),                       # lambda not scored separately
])
def test_java_known_answers(parser, body, expected):
    assert one(parser, 'java', _java(body)) == expected


# ── Go ───────────────────────────────────────────────────────────────────────

def _go(body):
    return f"package main\nfunc f(a int, b int, i interface{{}}, c chan int) {{\n{body}\n}}\n"


@pytest.mark.parametrize("body,expected", [
    ("", 1),
    ("if a > 1 {} else {}", 2),
    ("if a > 1 && b > 2 || a < 0 {}", 4),
    ("for j := 0; j < 1; j++ {}", 2),
    ("for range c {}", 2),
    ("switch a { case 1: case 2: case 3: default: }", 4),
    ("switch i.(type) { case int: case string: default: }", 3),
    ("select { case <-c: default: }", 2),
    ("g := func() { if a > 1 {} }\n_ = g", 2),                          # func literal isn't scored separately
])
def test_go_known_answers(parser, body, expected):
    assert one(parser, 'go', _go(body)) == expected


def test_go_method_declaration(parser):
    code = "package main\ntype S struct{}\nfunc (s *S) Run(a int) {\n if a > 1 && a < 5 {}\n}\n"
    assert one(parser, 'go', code, 'Run') == 3


def test_bare_arrow_callback_is_not_extracted_as_function_named_after_its_parameter(parser):
    code = "function f(arr) { return arr.map(x => x ? 1 : 2); }\nconst g = (a) => a;"
    assert set(cx(parser, 'javascript', code)) == {'f', 'g'}            # no bogus function "x"
