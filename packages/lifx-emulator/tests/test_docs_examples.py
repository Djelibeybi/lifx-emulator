"""Check the Python code examples in docs/ against the current public API.

Every fenced ``python`` block under ``docs/`` is extracted and:

* compiled (top-level ``await`` is allowed, as the examples are written for
  an async REPL or test body);
* checked so that every ``lifx_emulator``/``lifx_emulator_app`` import
  resolves to a real module and attribute;
* checked so that calls and attribute lookups on imported names match the
  real signatures and class members;
* checked so that ``EmulatedLifxServer(...)`` is given a device manager as
  its second argument;
* checked so that ``<obj>.state.<name>`` only uses attributes that
  ``DeviceState`` actually provides.

The blocks are not executed: many need a running emulator or a client
library that is not a dependency of this workspace.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import inspect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from lifx_emulator.devices.states import DeviceState
from lifx_emulator.server import EmulatedLifxServer

DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"
CHECKED_PACKAGES = ("lifx_emulator", "lifx_emulator_app")
# Historical implementation plans and specs quote diffs and partial snippets
# of code as it was at the time; they are not examples for users to run.
EXCLUDED_DIRS = ("superpowers",)

_FENCE_OPEN = re.compile(r"^(?P<indent>[ \t]*)```(?:python|py)\b")


@dataclass(frozen=True)
class CodeBlock:
    """A fenced Python block extracted from a Markdown file."""

    path: Path
    line: int
    source: str

    @property
    def id(self) -> str:
        return f"{self.path.relative_to(DOCS_DIR)}:{self.line}"


def _extract_blocks(path: Path) -> list[CodeBlock]:
    """Return every fenced Python block in a Markdown file, dedented."""
    blocks: list[CodeBlock] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        match = _FENCE_OPEN.match(lines[index])
        index += 1
        if match is None:
            continue
        indent = match.group("indent")
        start = index
        while index < len(lines) and lines[index].strip() != "```":
            index += 1
        body = [line.removeprefix(indent) for line in lines[start:index]]
        blocks.append(CodeBlock(path, start, "\n".join(body) + "\n"))
        index += 1
    return blocks


def _all_blocks() -> list[CodeBlock]:
    blocks: list[CodeBlock] = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        if path.relative_to(DOCS_DIR).parts[0] in EXCLUDED_DIRS:
            continue
        blocks.extend(_extract_blocks(path))
    return blocks


ALL_BLOCKS = _all_blocks()


def _is_checked_module(module: str | None) -> bool:
    return module is not None and module.split(".")[0] in CHECKED_PACKAGES


def _resolve_imports(tree: ast.Module) -> tuple[dict[str, Any], list[str]]:
    """Import every checked name and return the resulting namespace and errors."""
    namespace: dict[str, Any] = {}
    errors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _is_checked_module(alias.name):
                    continue
                try:
                    module = importlib.import_module(alias.name)
                except ImportError as e:
                    errors.append(f"line {node.lineno}: import {alias.name}: {e}")
                    continue
                if alias.asname:
                    namespace[alias.asname] = module
                else:
                    root = alias.name.split(".")[0]
                    namespace[root] = importlib.import_module(root)
        elif isinstance(node, ast.ImportFrom) and _is_checked_module(node.module):
            _resolve_from_import(node, namespace, errors)
    return namespace, errors


def _resolve_from_import(
    node: ast.ImportFrom, namespace: dict[str, Any], errors: list[str]
) -> None:
    module_name = node.module or ""
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        errors.append(f"line {node.lineno}: from {module_name}: {e}")
        return
    for alias in node.names:
        if alias.name == "*":
            continue
        if hasattr(module, alias.name):
            namespace[alias.asname or alias.name] = getattr(module, alias.name)
            continue
        try:
            submodule = importlib.import_module(f"{module_name}.{alias.name}")
        except ImportError:
            errors.append(
                f"line {node.lineno}: cannot import {alias.name!r} from {module_name}"
            )
            continue
        namespace[alias.asname or alias.name] = submodule


def _resolve_expr(node: ast.expr, namespace: dict[str, Any]) -> Any:
    """Resolve a Name/Attribute chain rooted at an imported name.

    Returns ``None`` when the chain is not rooted at an imported name.

    Raises:
        AttributeError: If an attribute in the chain does not exist.
    """
    if isinstance(node, ast.Name):
        return namespace.get(node.id)
    if isinstance(node, ast.Attribute):
        base = _resolve_expr(node.value, namespace)
        if base is None:
            return None
        return getattr(base, node.attr)
    return None


def _check_attributes(
    tree: ast.Module, namespace: dict[str, Any], errors: list[str]
) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        try:
            _resolve_expr(node, namespace)
        except AttributeError as e:
            errors.append(f"line {node.lineno}: {ast.unparse(node)}: {e}")


def _placeholder_call(call: ast.Call) -> tuple[list[object], dict[str, object]]:
    args = [object() for _ in call.args]
    kwargs = {kw.arg: object() for kw in call.keywords if kw.arg is not None}
    return args, kwargs


def _has_unpacking(call: ast.Call) -> bool:
    return any(isinstance(arg, ast.Starred) for arg in call.args) or any(
        kw.arg is None for kw in call.keywords
    )


def _check_call_signature(call: ast.Call, target: Any, errors: list[str]) -> None:
    if not callable(target) or _has_unpacking(call):
        return
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return
    args, kwargs = _placeholder_call(call)
    try:
        signature.bind(*args, **kwargs)
    except TypeError as e:
        errors.append(f"line {call.lineno}: {ast.unparse(call.func)}(...): {e}")


def _check_server_call(call: ast.Call, errors: list[str]) -> None:
    """EmulatedLifxServer needs a device manager, not an address, second."""
    keywords = {kw.arg: kw.value for kw in call.keywords}
    if len(call.args) >= 2:
        manager = call.args[1]
    elif "device_manager" in keywords:
        manager = keywords["device_manager"]
    else:
        errors.append(f"line {call.lineno}: EmulatedLifxServer needs device_manager")
        return
    if isinstance(manager, ast.Constant | ast.List | ast.JoinedStr):
        errors.append(
            f"line {call.lineno}: EmulatedLifxServer device_manager is "
            f"{ast.unparse(manager)!r}, expected a DeviceManager"
        )


def _check_calls(
    tree: ast.Module, namespace: dict[str, Any], errors: list[str]
) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        try:
            target = _resolve_expr(node.func, namespace)
        except AttributeError:
            continue  # Reported by _check_attributes
        is_server = target is EmulatedLifxServer or (
            isinstance(node.func, ast.Name) and node.func.id == "EmulatedLifxServer"
        )
        if is_server:
            _check_server_call(node, errors)
        if target is not None:
            _check_call_signature(node, target, errors)


def _device_state_attributes() -> set[str]:
    names = {f.name for f in dataclasses.fields(DeviceState)}
    names.update(DeviceState._ATTRIBUTE_ROUTES)
    names.update(name for name in dir(DeviceState) if not name.startswith("_"))
    return names


DEVICE_STATE_ATTRIBUTES = _device_state_attributes()


def _check_device_state_attributes(tree: ast.Module, errors: list[str]) -> None:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "state"
            and node.attr not in DEVICE_STATE_ATTRIBUTES
        ):
            errors.append(
                f"line {node.lineno}: {ast.unparse(node)}: "
                f"DeviceState has no attribute {node.attr!r}"
            )


def test_docs_contain_python_examples() -> None:
    """Guard against the extractor silently finding nothing."""
    assert len(ALL_BLOCKS) > 100


@pytest.mark.parametrize("block", ALL_BLOCKS, ids=lambda block: block.id)
def test_docs_example(block: CodeBlock) -> None:
    """Each docs example compiles and matches the current public API."""
    try:
        compile(
            block.source,
            block.id,
            "exec",
            flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
            dont_inherit=True,
        )
    except SyntaxError as e:
        line = block.line + (e.lineno or 0)
        pytest.fail(f"{block.id}: does not compile (line {line}): {e.msg}")

    tree = ast.increment_lineno(ast.parse(block.source), block.line)
    namespace, errors = _resolve_imports(tree)
    _check_attributes(tree, namespace, errors)
    _check_calls(tree, namespace, errors)
    _check_device_state_attributes(tree, errors)

    if errors:
        details = "\n".join(f"  {error}" for error in errors)
        pytest.fail(f"{block.id}:\n{details}")
