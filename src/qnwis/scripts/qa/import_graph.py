"""Build a lightweight import graph for the qnwis package."""

from __future__ import annotations

import argparse
import ast
import json
import logging
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("readiness_gate.import_graph")

ROOT = Path(__file__).parents[4].resolve()
SRC_ROOT = ROOT / "src"
PACKAGE_ROOT = SRC_ROOT / "qnwis"
OUTPUT_PATH = SRC_ROOT / "qnwis" / "docs" / "audit" / "import_graph.json"


def _module_name_from_path(path: Path) -> str:
    rel_path = path.relative_to(SRC_ROOT).with_suffix("")
    return ".".join(rel_path.parts)


def _resolve_from_import(module_name: str, node: ast.ImportFrom) -> str | None:
    package_parts = module_name.split(".")[:-1]
    if node.level and node.level - 1 > len(package_parts):
        return None

    base_parts = package_parts[: len(package_parts) - (node.level - 1)] if node.level else package_parts
    if node.module:
        base_parts = [*base_parts, *node.module.split(".")]
    if not base_parts:
        return None
    return ".".join(base_parts)


def _is_type_checking_guard(test: ast.AST) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute) and isinstance(test.value, ast.Name):
        return test.value.id == "typing" and test.attr == "TYPE_CHECKING"
    return False


class _ImportCollector(ast.NodeVisitor):
    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.edges: set[str] = set()
        self._type_checking_depth = 0
        self._nesting_level = 0

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        if self._type_checking_depth or self._nesting_level:
            return
        for alias in node.names:
            if alias.name.startswith("qnwis"):
                self.edges.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if self._type_checking_depth or self._nesting_level:
            return
        target = _resolve_from_import(self.module_name, node) if node.level else node.module
        if target and target.startswith("qnwis"):
            self.edges.add(target)

    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        if _is_type_checking_guard(node.test):
            self._type_checking_depth += 1
            for child in node.body:
                self.visit(child)
            self._type_checking_depth -= 1
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1


def build_import_graph(package_root: Path = PACKAGE_ROOT) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for file_path in sorted(package_root.rglob("*.py")):
        module_name = _module_name_from_path(file_path)
        graph.setdefault(module_name, set())
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(text, filename=str(file_path))
        except SyntaxError as exc:  # pragma: no cover
            raise RuntimeError(f"Unable to parse {file_path}: {exc}") from exc

        collector = _ImportCollector(module_name)
        collector.visit(tree)
        graph[module_name].update(collector.edges)
    return graph


def detect_cycles(graph: Mapping[str, set[str]]) -> list[list[str]]:
    state: dict[str, str] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []
    recorded: set[tuple[str, ...]] = set()

    def dfs(node: str) -> None:
        state[node] = "visiting"
        stack.append(node)
        for neighbor in graph.get(node, ()):
            if neighbor not in graph:
                continue
            neighbor_state = state.get(neighbor)
            if neighbor_state == "visiting":
                if neighbor in stack:
                    idx = stack.index(neighbor)
                    cycle = [*stack[idx:], neighbor]
                    key = tuple(cycle)
                    if key not in recorded:
                        cycles.append(cycle)
                        recorded.add(key)
            elif neighbor_state != "visited":
                dfs(neighbor)
        stack.pop()
        state[node] = "visited"

    for node in sorted(graph):
        if state.get(node) != "visited":
            dfs(node)
    return cycles


def write_graph(graph: Mapping[str, set[str]], output_path: Path, cycles: Iterable[list[str]]) -> None:
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "nodes": len(graph),
        "edges": sum(len(targets) for targets in graph.values()),
        "graph": {node: sorted(targets) for node, targets in graph.items()},
        "cycles": list(cycles),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate qnwis import graph")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Where to write JSON graph")
    parser.add_argument(
        "--package-root",
        type=Path,
        default=PACKAGE_ROOT,
        help="Root of qnwis package (defaults to src/qnwis)",
    )
    args = parser.parse_args(argv)

    graph = build_import_graph(args.package_root.resolve())
    cycles = detect_cycles(graph)
    write_graph(graph, args.output.resolve(), cycles)

    if cycles:
        for cycle in cycles:
            logger.error("Import cycle detected: %s", " -> ".join(cycle))
        return 1

    logger.info("Import graph generated for %d modules (%d edges)", len(graph), sum(len(v) for v in graph.values()))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    raise SystemExit(main())
