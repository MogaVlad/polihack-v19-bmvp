"""
Pathfinding module — BFS/Dijkstra on room-corridor-exit graph.

Builds an adjacency graph from FloorPlan data and computes shortest
evacuation paths from any room to the nearest exit.
"""

from typing import Dict, List, Tuple, Optional, Set
import heapq
import math

from models.floor_plan import FloorPlan


def _centroid(polygon: list) -> Tuple[float, float]:
    """Compute the centroid of a polygon given as list of (x, y) tuples/lists."""
    if not polygon:
        return (0.0, 0.0)
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _distance_between(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _build_graph(plan_data: dict) -> Dict[str, Dict[str, float]]:
    """
    Build a weighted adjacency graph from floor plan data.

    Nodes = room IDs + corridor IDs.
    Edges from doors (door.connects links two nodes) and corridor.connects.
    Weight = Euclidean distance between polygon centroids of connected nodes.
    """
    graph: Dict[str, Dict[str, float]] = {}

    # Collect centroids for all rooms and corridors
    centroids: Dict[str, Tuple[float, float]] = {}

    for room in plan_data.get("rooms", []):
        rid = room["id"]
        graph.setdefault(rid, {})
        centroids[rid] = _centroid(room.get("polygon", []))

    for corridor in plan_data.get("corridors", []):
        cid = corridor["id"]
        graph.setdefault(cid, {})
        centroids[cid] = _centroid(corridor.get("polygon", []))

    # Add edges from doors — each door connects exactly two nodes.
    # Doors are the ONLY way to connect rooms to corridors (physical passageways).
    for door in plan_data.get("doors", []):
        connects = door.get("connects", [])
        if len(connects) == 2:
            a, b = connects[0], connects[1]
            if a in centroids and b in centroids:
                dist = _distance_between(centroids[a], centroids[b])
                graph.setdefault(a, {})[b] = dist
                graph.setdefault(b, {})[a] = dist

    # Connect corridors to each other via corridor.connects (open passages).
    # Room-to-corridor edges are NOT created here — those require doors above.
    corridor_ids = {c["id"] for c in plan_data.get("corridors", [])}
    for corridor in plan_data.get("corridors", []):
        cid = corridor["id"]
        for node_id in corridor.get("connects", []):
            if node_id in corridor_ids and node_id != cid:
                if node_id in centroids and cid in centroids:
                    if node_id not in graph.get(cid, {}):
                        dist = _distance_between(centroids[cid], centroids[node_id])
                        graph.setdefault(cid, {})[node_id] = dist
                        graph.setdefault(node_id, {})[cid] = dist

    return graph


def _find_exit_nodes(plan_data: dict) -> Set[str]:
    """
    Identify nodes (rooms or corridors) that have exits attached.
    An exit's room_id tells us which node leads outside.
    """
    exit_nodes: Set[str] = set()
    for ex in plan_data.get("exits", []):
        room_id = ex.get("room_id", "")
        if room_id:
            exit_nodes.add(room_id)
    return exit_nodes


def _dijkstra(
    graph: Dict[str, Dict[str, float]],
    start: str,
    targets: Set[str],
) -> Tuple[float, List[str]]:
    """
    Dijkstra's algorithm from start to the nearest target node.
    Returns (distance, path) or (float('inf'), []) if unreachable.
    """
    if start in targets:
        return (0.0, [start])

    dist: Dict[str, float] = {start: 0.0}
    prev: Dict[str, Optional[str]] = {start: None}
    heap = [(0.0, start)]
    visited: Set[str] = set()

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        if u in targets:
            # Reconstruct path
            path = []
            node: Optional[str] = u
            while node is not None:
                path.append(node)
                node = prev.get(node)
            path.reverse()
            return (d, path)

        for v, w in graph.get(u, {}).items():
            if v not in visited:
                new_dist = d + w
                if new_dist < dist.get(v, float("inf")):
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(heap, (new_dist, v))

    return (float("inf"), [])


def _extract_plan_data(inputs: Dict) -> dict:
    """Extract floor plan dict from inputs — supports both raw dict and nested."""
    if "floor_plan" in inputs:
        fp = inputs["floor_plan"]
        if isinstance(fp, dict):
            return fp
    # If inputs itself looks like a floor plan
    if "rooms" in inputs:
        return inputs
    return inputs


def find_shortest_exit_path(
    inputs: Dict, room_id: str = ""
) -> Tuple[float, List[str]]:
    """
    Find shortest path from a room to the nearest exit.

    Args:
        inputs: Dict containing floor plan data (or {"floor_plan": {...}})
        room_id: The room to start from

    Returns:
        (distance, path_list) — distance in meters (approximate via centroids),
        path as list of node IDs from room to exit node.
        Returns (float('inf'), []) if no path exists.
    """
    plan_data = _extract_plan_data(inputs)
    graph = _build_graph(plan_data)
    exit_nodes = _find_exit_nodes(plan_data)

    if not exit_nodes:
        return (float("inf"), [])

    if room_id not in graph:
        return (float("inf"), [])

    return _dijkstra(graph, room_id, exit_nodes)


def find_all_travel_distances(inputs: Dict) -> Dict[str, float]:
    """
    Compute shortest exit distance for every room in the plan.

    Returns:
        {room_id: distance} dict. Rooms with no path get float('inf').
    """
    plan_data = _extract_plan_data(inputs)
    graph = _build_graph(plan_data)
    exit_nodes = _find_exit_nodes(plan_data)

    distances: Dict[str, float] = {}

    for room in plan_data.get("rooms", []):
        rid = room["id"]
        dist, _ = _dijkstra(graph, rid, exit_nodes)
        distances[rid] = round(dist, 2)

    return distances
