#!/usr/bin/env python3

import ast
import sys
from pathlib import Path


DJANGO_TRANSLATION_MODULE = "django.utils.translation"

SIMPLE_FUNCS = {
    "gettext",
    "gettext_lazy",
    "gettext_noop",
    "_",
}
CONTEXT_FUNCS = {
    "pgettext",
    "pgettext_lazy",
}
PLURAL_FUNCS = {
    "ngettext",
    "ngettext_lazy",
}
CONTEXT_PLURAL_FUNCS = {
    "npgettext",
    "npgettext_lazy",
}

DJANGO_FUNCS = SIMPLE_FUNCS | CONTEXT_FUNCS | PLURAL_FUNCS | CONTEXT_PLURAL_FUNCS

FUNC_ARG_INDICES = {
    **{name: [0] for name in SIMPLE_FUNCS},
    **{name: [1] for name in CONTEXT_FUNCS},
    **{name: [0, 1] for name in PLURAL_FUNCS},
    **{name: [1, 2] for name in CONTEXT_PLURAL_FUNCS},
}


class ModuleLevelCollector(ast.NodeVisitor):
    """Collect translation imports and module-level shadow events."""

    def __init__(self):
        self.translation_aliases = set()
        self.import_events = []
        self.shadow_events = []
        self._scope_depth = 0

    def visit_ImportFrom(self, node):
        if self._scope_depth == 0 and node.module == DJANGO_TRANSLATION_MODULE:
            for alias in node.names:
                name = alias.name
                asname = alias.asname or alias.name
                if name in DJANGO_FUNCS:
                    self.translation_aliases.add(asname)
                    self.import_events.append((asname, node.lineno))
        self.generic_visit(node)

    def visit_Assign(self, node):
        if self._scope_depth == 0 and node.targets:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                self.shadow_events.append((target.id, node.lineno))
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if self._scope_depth == 0:
            self.shadow_events.append((node.name, node.lineno))
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self._scope_depth += 1
        self.generic_visit(node)
        self._scope_depth -= 1


def _is_active_translation_name(name, call_lineno, import_events, shadow_events):
    relevant_imports = [
        lineno for alias, lineno in import_events if alias == name and lineno <= call_lineno
    ]
    if not relevant_imports:
        return False

    latest_import = max(relevant_imports)
    relevant_shadows = [
        lineno for shadowed, lineno in shadow_events if shadowed == name and lineno <= call_lineno
    ]
    if relevant_shadows and max(relevant_shadows) > latest_import:
        return False

    return True


class TranslationChecker(ast.NodeVisitor):
    def __init__(self, filename, translation_aliases, import_events, shadow_events):
        self.filename = filename
        self.translation_aliases = translation_aliases
        self.import_events = import_events
        self.shadow_events = shadow_events
        self.errors = []

    def visit_Call(self, node):
        func_name = self._get_func_name(node.func)

        if func_name and func_name in self.translation_aliases:
            if _is_active_translation_name(
                func_name, node.lineno, self.import_events, self.shadow_events
            ):
                self._check_strings(node, func_name)

        self.generic_visit(node)

    def _get_func_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        return None

    def _check_strings(self, node, func_name):
        for index in FUNC_ARG_INDICES.get(func_name, [0]):
            if index >= len(node.args):
                continue

            arg = node.args[index]
            if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                continue

            text = arg.value.strip()
            if not text:
                continue

            if text[0].isalpha() and text[0].isupper():
                self.errors.append(
                    f"{self.filename}:{node.lineno}: "
                    f"translation must start with lowercase -> '{text}'"
                )


def check_source(source, filename="<string>"):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        lineno = exc.lineno or 1
        return [f"{filename}:{lineno}: syntax error: {exc.msg}"]

    collector = ModuleLevelCollector()
    collector.visit(tree)

    checker = TranslationChecker(
        filename=filename,
        translation_aliases=collector.translation_aliases,
        import_events=collector.import_events,
        shadow_events=collector.shadow_events,
    )
    checker.visit(tree)

    return checker.errors


def check_file(filename):
    try:
        source = Path(filename).read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{filename}: could not read file: {exc}"]

    return check_source(source, filename)


def main():
    errors = []

    for filename in sys.argv[1:]:
        if filename.endswith(".py"):
            errors.extend(check_file(filename))

    if errors:
        for error in errors:
            print(error)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
