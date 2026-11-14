import pickle
from pathlib import Path

import networkx as nx


class MemoryGraph:
    def __init__(self, graph_path: str | None = None):
        self._path = graph_path
        if graph_path and Path(graph_path).exists():
            with open(graph_path, "rb") as f:
                self._g: nx.DiGraph = pickle.load(f)  # nosec B301 — file written by engram itself, not from external input
        else:
            self._g = nx.DiGraph()

    def add_memory(self, memory_id: str, dataset: str, entities: list[str]):
        self._g.add_node(memory_id, kind="memory", dataset=dataset)
        for entity in entities:
            entity_id = f"entity:{entity.lower()}"
            self._g.add_node(entity_id, kind="entity", text=entity)
            self._g.add_edge(memory_id, entity_id)
        self._save()

    def get_related(self, memory_id: str) -> list[str]:
        if memory_id not in self._g:
            return []
        related: set[str] = set()
        for entity_id in self._g.successors(memory_id):
            for pred in self._g.predecessors(entity_id):
                if pred != memory_id and self._g.nodes[pred].get("kind") == "memory":
                    related.add(pred)
        return list(related)

    def remove_by_dataset(self, dataset: str):
        to_remove = [
            n for n, d in self._g.nodes(data=True) if d.get("dataset") == dataset
        ]
        self._g.remove_nodes_from(to_remove)
        self._save()

    def remove_by_ids(self, ids: list[str]):
        self._g.remove_nodes_from([i for i in ids if i in self._g])
        self._save()

    def _save(self):
        if self._path:
            with open(self._path, "wb") as f:
                pickle.dump(self._g, f)
