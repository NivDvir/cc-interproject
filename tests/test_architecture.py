"""The import gate: walks every module under `src/six_laws_kit/`, parses its imports with `ast`,
and enforces the STYLE.md import rule (a category imports only the stdlib, `run_state`, `paths`,
and its own siblings) plus its named exceptions from `docs/DESIGN.md` section 2. Also checks that
every category has an `ARCHITECTURE.md` and that no source file has grown past the size limits.
"""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

PACKAGE = "six_laws_kit"
SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / PACKAGE
CATEGORY_DIRS = {"discover", "heads", "wizard", "write", "manifest", "hooks", "texts"}
ALWAYS_ALLOWED = {"run_state", "paths"}
FULL_ACCESS_MODULES = {"cli", "wizard.api"}
MODULE_EXCEPTIONS = {
    "write.apply": {"manifest.record"},
    "manifest.uninstall": {"write.blocks", "write.settings"},
}
CATEGORY_EXCEPTIONS = {("write", "texts")}
WARN_LINES = 400
MAX_LINES = 600


def _py_files() -> list[Path]:
    return sorted(p for p in SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def _module_name(path: Path) -> str:
    parts = [part for part in path.relative_to(SRC_ROOT).with_suffix("").parts if part != "__init__"]
    return ".".join(parts)


def _category_of(module_name: str) -> str:
    first = module_name.split(".")[0]
    return first if first in CATEGORY_DIRS else "root"


def _is_real_submodule(relative_dotted: str) -> bool:
    """True if `relative_dotted` (e.g. "write.blocks") names an actual file or subpackage under
    `SRC_ROOT` — as opposed to a plain symbol imported off a module, e.g. `Run` off `run_state`.
    """
    rel_path = Path(*relative_dotted.split("."))
    return (SRC_ROOT / f"{rel_path}.py").is_file() or (SRC_ROOT / rel_path / "__init__.py").is_file()


def _package_imports(path: Path) -> set[str]:
    """Return every module this file imports from the package, relative to it (e.g. "write.blocks",
    "run_state"). `from module import a, b` is resolved name by name: an `a`/`b` that is itself a
    real submodule is kept as `module.a`; when none of them are, the import is really of plain
    symbols off `module` (e.g. `Run` off `run_state`), so `module` itself is kept instead.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prefix = f"{PACKAGE}."
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(_relative(alias.name, prefix) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            result.update(_from_import(node.module, [a.name for a in node.names], prefix))
    result.discard("")
    return result


def _relative(name: str, prefix: str) -> str:
    return name[len(prefix) :] if name.startswith(prefix) else ""


def _from_import(module: str, names: list[str], prefix: str) -> set[str]:
    if module != PACKAGE and not module.startswith(prefix):
        return set()
    module_relative = _relative(module, prefix)
    submodules = set()
    for name in names:
        candidate = f"{module_relative}.{name}" if module_relative else name
        if _is_real_submodule(candidate):
            submodules.add(candidate)
    return submodules or ({module_relative} if module_relative else set())


def _allowed(file_module: str, imported: str) -> bool:
    if imported in ALWAYS_ALLOWED:
        return True
    if file_module in FULL_ACCESS_MODULES:
        return True
    if imported in MODULE_EXCEPTIONS.get(file_module, set()):
        return True
    file_cat, imported_cat = _category_of(file_module), _category_of(imported)
    if file_cat == imported_cat:
        return True
    return (file_cat, imported_cat) in CATEGORY_EXCEPTIONS


def test_import_rule_is_respected():
    violations = []
    for path in _py_files():
        module_name = _module_name(path)
        if not module_name or module_name == "__main__":
            continue
        imports = _package_imports(path)
        if _category_of(module_name) == "hooks":
            if imports:
                found = sorted(imports)
                violations.append(f"{path}: hooks/* must import nothing from the package, found {found}")
            continue
        for imported in imports:
            if not _allowed(module_name, imported):
                violations.append(f"{path}: '{module_name}' may not import '{imported}'")
    assert not violations, "\n".join(violations)


def test_every_category_has_an_architecture_doc():
    missing = [name for name in CATEGORY_DIRS if not (SRC_ROOT / name / "ARCHITECTURE.md").is_file()]
    assert not missing, f"missing ARCHITECTURE.md in: {missing}"
    assert (SRC_ROOT / "ARCHITECTURE.md").is_file(), "missing package-root ARCHITECTURE.md"


def test_no_source_file_exceeds_the_line_budget():
    too_long = []
    for path in _py_files():
        line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        if line_count > WARN_LINES:
            warnings.warn(f"{path} is {line_count} lines (warn threshold {WARN_LINES})", stacklevel=1)
        if line_count > MAX_LINES:
            too_long.append(f"{path}: {line_count} lines (limit {MAX_LINES})")
    assert not too_long, "\n".join(too_long)
