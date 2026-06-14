import tempfile
from pathlib import Path

from django_translation_lint.cli import check_file, check_source


def assert_errors(source, expected_substrings):
    errors = check_source(source)
    assert len(errors) == len(expected_substrings)
    for error, expected in zip(errors, expected_substrings):
        assert expected in error


def test_valid_lowercase_translation():
    source = """
from django.utils.translation import gettext as _

_("user not found")
"""
    assert check_source(source) == []


def test_invalid_uppercase_gettext():
    source = """
from django.utils.translation import gettext as _

_("User not found")
"""
    assert_errors(source, ["User not found"])


def test_pgettext_checks_message_not_context():
    source = """
from django.utils.translation import pgettext

pgettext("context", "User not found")
"""
    assert_errors(source, ["User not found"])


def test_pgettext_ignores_uppercase_context_when_message_is_valid():
    source = """
from django.utils.translation import pgettext

pgettext("Context", "user not found")
"""
    assert check_source(source) == []


def test_ngettext_checks_singular_and_plural():
    source = """
from django.utils.translation import ngettext

ngettext("Item", "items", 1)
ngettext("item", "Items", 2)
"""
    assert_errors(source, ["Item", "Items"])


def test_shadowing_only_affects_calls_after_assignment():
    source = """
from django.utils.translation import gettext as _

_("User before")

_ = lambda x: x
_("User after")
"""
    assert_errors(source, ["User before"])


def test_function_def_shadows_translation_name():
    source = """
from django.utils.translation import gettext as _

def _(value):
    return value

_("User not found")
"""
    assert check_source(source) == []


def test_no_import_is_ignored():
    source = """
_("User not found")
"""
    assert check_source(source) == []


def test_syntax_error_is_reported():
    source = """
from django.utils.translation import gettext as _
_("broken"
"""
    errors = check_source(source, filename="broken.py")
    assert len(errors) == 1
    assert "broken.py:3: syntax error:" in errors[0]


def test_gettext_noop_is_checked():
    source = """
from django.utils.translation import gettext_noop

gettext_noop("User not found")
"""
    assert_errors(source, ["User not found"])


def test_npgettext_checks_singular_and_plural():
    source = """
from django.utils.translation import npgettext

npgettext("pizza", "One Pizza", "two pizzas", 1)
npgettext("pizza", "one pizza", "Two pizzas", 2)
"""
    assert_errors(source, ["One Pizza", "Two pizzas"])


def test_reimport_after_shadowing_reenables_checks():
    source = """
from django.utils.translation import gettext as _

_ = lambda x: x
from django.utils.translation import gettext as _
_("User not found")
"""
    assert_errors(source, ["User not found"])


def test_check_file_reads_from_disk():
    source = """
from django.utils.translation import gettext as _
_("User not found")
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "example.py"
        path.write_text(source, encoding="utf-8")
        errors = check_file(str(path))
        assert len(errors) == 1
        assert str(path) in errors[0]
        assert "User not found" in errors[0]
