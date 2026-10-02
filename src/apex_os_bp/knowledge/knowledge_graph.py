"""Knowledge graph engine."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Set

from apex_os_bp.knowledge.models import KnowledgeEdge, KnowledgeNode


class KnowledgeGraph:
    """Knowledge graph with nodes and edges."""

    def __init__(self):
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: Dict[str, KnowledgeEdge] = {}
        self._adjacency: Dict[str, List[str]] = {}

    def add_node(
        self,
        label: str,
        node_type: str,
        properties: Optional[Dict] = None,
        **kwargs,
    ) -> KnowledgeNode:
        """Add a node to the graph."""
        node = KnowledgeNode(
            id=str(uuid.uuid4()),
            label=label,
            node_type=node_type,
            properties=properties or {},
            **kwargs,
        )
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        return node

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Get node by ID."""
        return self._nodes.get(node_id)

    def update_node(self, node_id: str, **kwargs) -> Optional[KnowledgeNode]:
        """Update node fields."""
        node = self._nodes.get(node_id)
        if not node:
            return None
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        return node

    def delete_node(self, node_id: str) -> bool:
        """Delete node and all connected edges."""
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        # Remove connected edges
        edges_to_remove = [
            eid for eid, edge in self._edges.items()
            if edge.source_id == node_id or edge.target_id == node_id
        ]
        for eid in edges_to_remove:
            del self._edges[eid]
        # Update adjacency
        if node_id in self._adjacency:
            del self._adjacency[node_id]
        for adj_list in self._adjacency.values():
            if node_id in adj_list:
                adj_list.remove(node_id)
        return True

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        weight: float = 1.0,
        properties: Optional[Dict] = None,
        **kwargs,
    ) -> KnowledgeEdge:
        """Add an edge between two nodes."""
        if source_id not in self._nodes:
            raise ValueError(f"Source node not found: {source_id}")
        if target_id not in self._nodes:
            raise ValueError(f"Target node not found: {target_id}")

        edge = KnowledgeEdge(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
            properties=properties or {},
            **kwargs,
        )
        self._edges[edge.id] = edge
        if source_id not in self._adjacency:
            self._adjacency[source_id] = []
        self._adjacency[source_id].append(target_id)
        return edge

    def get_edge(self, edge_id: str) -> Optional[KnowledgeEdge]:
        """Get edge by ID."""
        return self._edges.get(edge_id)

    def delete_edge(self, edge_id: str) -> bool:
        """Delete edge by ID."""
        edge = self._edges.get(edge_id)
        if not edge:
            return False
        del self._edges[edge_id]
        if edge.source_id in self._adjacency:
            if edge.target_id in self._adjacency[edge.source_id]:
                self._adjacency[edge.source_id].remove(edge.target_id)
        return True

    def get_neighbors(self, node_id: str) -> List[KnowledgeNode]:
        """Get all neighbor nodes."""
        neighbor_ids = self._adjacency.get(node_id, [])
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def get_edges_from(self, node_id: str) -> List[KnowledgeEdge]:
        """Get all edges from a node."""
        return [e for e in self._edges.values() if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> List[KnowledgeEdge]:
        """Get all edges to a node."""
        return [e for e in self._edges.values() if e.target_id == node_id]

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> Optional[List[KnowledgeNode]]:
        """Find path between two nodes using BFS."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        if source_id == target_id:
            return [self._nodes[source_id]]

        visited: Set[str] = set()
        queue: List[tuple] = [(source_id, [source_id])]
        visited.add(source_id)

        while queue:
            current_id, path = queue.pop(0)
            if len(path) > max_depth:
                continue
            for neighbor_id in self._adjacency.get(current_id, []):
                if neighbor_id == target_id:
                    path_ids = path + [neighbor_id]
                    return [self._nodes[nid] for nid in path_ids]
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        return None

    def search_nodes(self, query: str, node_type: Optional[str] = None) -> List[KnowledgeNode]:
        """Search nodes by label."""
        query_lower = query.lower()
        results = []
        for node in self._nodes.values():
            if node_type and node.node_type != node_type:
                continue
            if query_lower in node.label.lower():
                results.append(node)
        return results

    def get_nodes_by_type(self, node_type: str) -> List[KnowledgeNode]:
        """Get all nodes of a specific type."""
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_all_nodes(self) -> List[KnowledgeNode]:
        """Get all nodes."""
        return list(self._nodes.values())

    def get_all_edges(self) -> List[KnowledgeEdge]:
        """Get all edges."""
        return list(self._edges.values())

    def node_count(self) -> int:
        """Get node count."""
        return len(self._nodes)

    def edge_count(self) -> int:
        """Get edge count."""
        return len(self._edges)

    def get_relation_types(self) -> List[str]:
        """Get all unique relation types."""
        return list(set(e.relation for e in self._edges.values()))
