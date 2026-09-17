import pytest

from yp import YPError, preprocess


def test_transforms_function_and_preserves_body():
    source = '''def get_students:\n    """Return active students."""\n    users = course.get_users()\n    return {str(get_value(user, "id")): user for user in users}\nneeds (course)\n'''

    assert preprocess(source) == '''def get_students(course):\n    """Return active students."""\n    users = course.get_users()\n    return {str(get_value(user, "id")): user for user in users}\n\n'''


def test_transforms_nested_and_multiple_functions():
    source = '''value = 1\ndef outer:\n    def inner:\n        return suffix\n    needs (suffix)\n    return inner("!")\nneeds ()\n\ndef other:\n    return value\nneeds (value)\n'''

    generated = preprocess(source)

    assert "def outer():" in generated
    assert "    def inner(suffix):" in generated
    assert "def other(value):" in generated


def test_reports_missing_needs():
    with pytest.raises(YPError, match="line 3: missing needs clause for function f"):
        preprocess("def f:\n    return 1\nvalue = 2\n")


def test_reports_misplaced_needs():
    with pytest.raises(YPError, match="needs clause must be at the same indentation"):
        preprocess("def f:\n    return 1\n    needs ()\n")


def test_reports_empty_needs():
    with pytest.raises(YPError, match="line 3: empty needs clause"):
        preprocess("def f:\n    return 1\nneeds\n")


def test_reports_malformed_header():
    with pytest.raises(YPError, match="expected function header"):
        preprocess("def f(x):\n    return x\nneeds (x)\n")


def test_reports_invalid_generated_python():
    with pytest.raises(YPError, match="generated Python is invalid"):
        preprocess("def f:\n    return (\nneeds ()\n", "bad.yp")


def test_accepts_equivalent_tab_and_space_indentation():
    source = "def outer:\n\tdef inner:\n\t\treturn value\n        needs (value)\nneeds (inner)\n"

    generated = preprocess(source)

    assert "\tdef inner(value):" in generated
    assert "def outer(inner):" in generated


def test_accepts_python_unicode_identifier():
    assert preprocess("def λ:\n    return 1\nneeds ()\n").startswith("def λ():")


def test_rejects_non_identifier_and_keyword_names():
    for header in ("def not-valid:", "def class:"):
        with pytest.raises(YPError, match="expected function header"):
            preprocess(f"{header}\n    return 1\nneeds (value)\n")


def test_needs_removal_preserves_line_count():
    source = "def f:\n    return 1\nneeds (value)\n\n"

    generated = preprocess(source)

    assert generated.count("\n") == source.count("\n")
