import json
from backend.core.config import extract_json

def test_extract_json_success():
    # 1. Standard correct JSON
    valid_json = '{"lecture": "Hello", "key_points": ["a", "b"]}'
    assert json.loads(extract_json(valid_json)) == {"lecture": "Hello", "key_points": ["a", "b"]}

    # 2. Markdown fenced JSON
    fenced_json = '```json\n{"lecture": "Hello", "key_points": ["a", "b"]}\n```'
    assert json.loads(extract_json(fenced_json)) == {"lecture": "Hello", "key_points": ["a", "b"]}

def test_extract_json_repairs_trailing_commas():
    # Trailing comma in dict and list
    dirty_json = '{"lecture": "Hello", "key_points": ["a", "b",],}'
    res = extract_json(dirty_json)
    assert json.loads(res) == {"lecture": "Hello", "key_points": ["a", "b"]}

def test_extract_json_repairs_unescaped_quotes():
    # Unescaped quotes inside strings
    dirty_json = '{"lecture": "Hello "world" lecture", "key_points": ["a \\"b\\" c"]}'
    res = extract_json(dirty_json)
    assert json.loads(res) == {"lecture": 'Hello "world" lecture', "key_points": ["a \"b\" c"]}

    # Multiple quotes
    dirty_json2 = '{"lecture": "This is a "quote" and it is "fine""}'
    res2 = extract_json(dirty_json2)
    assert json.loads(res2) == {"lecture": 'This is a "quote" and it is "fine"'}

def test_extract_json_repairs_latex_escapes():
    # Single backslash in latex math commands using a raw string literal
    dirty_json = r'{"lecture": "Đa thức $P(x) = a_n x^n + \frac{1}{2} x + \sum_{i=1}^n x_i$"}'
    res = extract_json(dirty_json)
    # The backslashes should get double escaped: \\frac and \\sum
    assert "\\\\frac" in res
    assert "\\\\sum" in res
    assert json.loads(res) == {"lecture": "Đa thức $P(x) = a_n x^n + \\frac{1}{2} x + \\sum_{i=1}^n x_i$"}
