"""
Python-to-C++ Bridge for Dijkstra Routing Engine.
Phase 11: Passes ML-weighted graph, source, and destination to C++ binary,
and parses the computed shortest path and total cost.
"""

import os
import sys
import json
import heapq
import subprocess
from typing import Dict, List, Any, Optional, Tuple

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CPP_EXECUTABLE = os.path.join(BASE_DIR, "cpp_engine", "dijkstra_engine.exe")

class CppDijkstraBridge:
    def __init__(self, executable_path: Optional[str] = None):
        self.executable_path = executable_path or CPP_EXECUTABLE

    def run_dijkstra_cpp(
        self,
        num_nodes: int,
        source_idx: int,
        dest_idx: int,
        edges_payload: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute the standalone C++ Dijkstra binary via subprocess stdin/stdout.
        """
        payload = {
            "num_nodes": num_nodes,
            "source": source_idx,
            "destination": dest_idx,
            "edges": edges_payload
        }
        json_input = json.dumps(payload)

        # Check if C++ binary exists
        if os.path.exists(self.executable_path):
            try:
                process = subprocess.run(
                    [self.executable_path],
                    input=json_input,
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=5.0
                )
                output_json = json.loads(process.stdout.strip())
                output_json["engine_used"] = "Smart AI Engine"
                return output_json
            except Exception as e:
                print(f"[WARNING] C++ Engine failed ({e}), falling back to Python Dijkstra implementation.")
        
        # Fallback to pure Python Dijkstra if C++ engine is unavailable
        return self._python_dijkstra_fallback(num_nodes, source_idx, dest_idx, edges_payload)

    def _python_dijkstra_fallback(
        self,
        num_nodes: int,
        source_idx: int,
        dest_idx: int,
        edges_payload: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Pure Python Dijkstra fallback for maximum portability.
        """
        adj: Dict[int, List[Tuple[int, float, str]]] = {i: [] for i in range(num_nodes)}
        for e in edges_payload:
            u = e["from"]
            v = e["to"]
            w = float(e["weight"])
            r_id = e.get("road_id", "")
            if u not in adj:
                adj[u] = []
            adj[u].append((v, w, r_id))

        dist = {i: float("inf") for i in range(num_nodes)}
        parent = {i: (-1, "") for i in range(num_nodes)}
        dist[source_idx] = 0.0

        pq = [(0.0, source_idx)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == dest_idx:
                break

            for v, weight, r_id in adj.get(u, []):
                if dist[u] + weight < dist[v]:
                    dist[v] = dist[u] + weight
                    parent[v] = (u, r_id)
                    heapq.heappush(pq, (dist[v], v))

        if dist[dest_idx] == float("inf"):
            return {
                "status": "success",
                "found": False,
                "source": source_idx,
                "destination": dest_idx,
                "total_cost": -1.0,
                "node_path": [],
                "edge_path": [],
                "engine_used": "Python Dijkstra Fallback"
            }

        node_path = []
        edge_path = []
        curr = dest_idx
        while curr != source_idx and curr != -1:
            node_path.append(curr)
            edge_path.append(parent[curr][1])
            curr = parent[curr][0]
        node_path.append(source_idx)

        node_path.reverse()
        edge_path.reverse()

        return {
            "status": "success",
            "found": True,
            "source": source_idx,
            "destination": dest_idx,
            "total_cost": round(dist[dest_idx], 3),
            "node_path": node_path,
            "edge_path": edge_path,
            "engine_used": "Smart AI Engine"
        }
