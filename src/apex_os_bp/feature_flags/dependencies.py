"""Dependency engine — manages flag dependency graph."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Set


class DependencyEngine:
    """Manages dependencies between feature flags.

    A flag can depend on other flags. A flag with dependencies
    is only enabled if all its dependencies are also enabled.
    """

    def __init__(self) -> None:
        self._graph: Dict[str, Set[str]] = {}
        self._reverse_graph: Dict[str, Set[str]] = {}

    def add_dependency(self, flag_name: str, depends_on: str) -> None:
        """Add a dependency edge: flag_name depends on depends_on."""
        if flag_name == depends_on:
            raise ValueError(f"Flag '{flag_name}' cannot depend on itself")

        self._graph.setdefault(flag_name, set()).add(depends_on)
        self._reverse_graph.setdefault(depends_on, set()).add(flag_name)

    def remove_dependency(self, flag_name: str, depends_on: str) -> None:
        """Remove a dependency edge."""
        if flag_name in self._graph:
            self._graph[flag_name].discard(depends_on)
        if depends_on in self._reverse_graph:
            self._reverse_graph[depends_on].discard(flag_name)

    def clear_dependencies(self, flag_name: str) -> None:
        """Remove all dependencies for a flag."""
        if flag_name in self._graph:
            for dep in self._graph[flag_name]:
                if dep in self._reverse_graph:
                    self._reverse_graph[dep].discard(flag_name)
            del self._graph[flag_name]

    def get_dependencies(self, flag_name: str) -> Set[str]:
        """Get all flags that flag_name depends on."""
        return set(self._graph.get(flag_name, set()))

    def get_dependents(self, flag_name: str) -> Set[str]:
        """Get all flags that depend on flag_name."""
        return set(self._reverse_graph.get(flag_name, set()))

    def are_satisfied(
        self,
        flag_name: str,
        evaluator: Callable[..., bool],
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Check if all dependencies for a flag are satisfied.

        Uses the provided evaluator function to check each dependency.
        Detects circular dependencies and returns False if found.
        """
        deps = self._graph.get(flag_name, set())
        if not deps:
            return True

        visited: Set[str] = set()
        return self._check_deps_recursive(
            flag_name, deps, evaluator, context, user_id, visited
        )

    def _check_deps_recursive(
        self,
        flag_name: str,
        deps: Set[str],
        evaluator: Callable[..., bool],
        context: Optional[Dict[str, Any]],
        user_id: Optional[str],
        visited: Set[str],
    ) -> bool:
        """Recursively check dependencies, detecting cycles."""
        if flag_name in visited:
            return False  # Circular dependency

        visited.add(flag_name)

        for dep in deps:
            if not evaluator(dep, context, user_id):
                return False
            # Check transitive dependencies
            transitive = self._graph.get(dep, set())
            if transitive:
                if not self._check_deps_recursive(
                    dep, transitive, evaluator, context, user_id, visited
                ):
                    return False

        visited.discard(flag_name)
        return True

    def has_circular_dependency(self) -> bool:
        """Detect if the dependency graph has any cycles."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in self._graph:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def get_topological_order(self) -> list:
        """Return flags in topological order (dependencies first)."""
        visited: Set[str] = set()
        order: list = []

        def dfs(node: str) -> None:
            visited.add(node)
            for dep in self._graph.get(node, set()):
                if dep not in visited:
                    dfs(dep)
            order.append(node)

        for node in self._graph:
            if node not in visited:
                dfs(node)

        return order
