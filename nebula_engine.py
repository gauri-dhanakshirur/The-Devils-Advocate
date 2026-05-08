"""
Devil's Advocate — Knowledge Nebula Engine
Transforms session browsing history into a multi-dimensional graph
that visualizes the 'gravitational pull' of bias.

Uses NetworkX for graph computation and outputs data for
force-directed rendering on the frontend.
"""

import math
import json
import logging
from typing import List, Dict, Optional

import networkx as nx

logger = logging.getLogger("nebula_engine")


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x ** 2 for x in a))
    mag_b = math.sqrt(sum(x ** 2 for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _cosine_distance(a: List[float], b: List[float]) -> float:
    """Cosine distance = 1 - cosine_similarity."""
    return 1.0 - _cosine_similarity(a, b)


def _euclidean_distance(a: List[float], b: List[float]) -> float:
    """Euclidean distance between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def compute_nebula(
    pages: List[Dict],
    counter_perspectives: List[Dict],
    session_bias_score: float = 5.0
) -> Dict:
    """
    Build the Knowledge Nebula graph from session data.

    Returns a dict with:
      - nodes: list of node objects
      - links: list of edge objects
      - metrics: graph-level metrics (diameter, density, etc.)
    """
    G = nx.Graph()
    nodes = []
    links = []

    # ── 1. Build Nodes from Pages (Celestial Bodies) ──────────────────
    page_nodes = []
    for i, page in enumerate(pages):
        # Parse stance_vector
        sv = page.get("stance_vector", [])
        if isinstance(sv, str):
            try:
                sv = json.loads(sv)
            except:
                sv = []
        if not sv or not isinstance(sv, list):
            sv = [0.0, 0.0, 0.0]

        # Mass based on bias_score proximity to session average (more extreme = heavier)
        bias = page.get("bias_score", 5.0) or 5.0
        mass = max(3, min(20, abs(bias - 5.0) * 3 + 5))

        node_id = f"page_{page.get('id', i)}"
        node = {
            "id": node_id,
            "label": (page.get("title") or page.get("url") or "Untitled")[:50],
            "type": "page",
            "url": page.get("url", ""),
            "bias_score": bias,
            "stance_vector": sv,
            "mass": mass,
            "val": mass,  # react-force-graph uses 'val' for node size
            "color": _bias_color(bias),
        }
        page_nodes.append(node)
        nodes.append(node)
        G.add_node(node_id, **node)

    # ── 2. Build Edges from Semantic Gravity (Vector Similarity) ──────
    for i in range(len(page_nodes)):
        for j in range(i + 1, len(page_nodes)):
            a = page_nodes[i]
            b = page_nodes[j]
            sim = _cosine_similarity(a["stance_vector"], b["stance_vector"])

            # Only connect if similarity > threshold (gravitational pull)
            if sim > 0.3:
                link = {
                    "source": a["id"],
                    "target": b["id"],
                    "similarity": round(sim, 3),
                    "width": max(0.5, sim * 4),  # Visual edge thickness
                    "color": f"rgba(139, 92, 246, {min(0.8, sim * 0.9):.2f})",
                }
                links.append(link)
                G.add_edge(a["id"], b["id"], weight=sim)

    # ── 3. Compute Centrality (Bridge Nodes) ──────────────────────────
    bridge_nodes = []
    if len(G.nodes) >= 3 and len(G.edges) >= 2:
        try:
            betweenness = nx.betweenness_centrality(G)
            # Sort by centrality, mark top nodes as bridges
            sorted_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
            threshold = 0.1  # Minimum centrality to be considered a bridge
            for node_id, centrality in sorted_nodes:
                if centrality > threshold:
                    bridge_nodes.append(node_id)
                    # Update the node in our nodes list
                    for n in nodes:
                        if n["id"] == node_id:
                            n["is_bridge"] = True
                            n["centrality"] = round(centrality, 3)
                            n["color"] = "#10b981"  # Green for bridge nodes
                            n["val"] = n["val"] * 1.5
                            break
        except Exception as e:
            logger.warning("Centrality calculation failed: %s", e)

    # ── 4. Ghost Nodes (Counter-Opinion Outer Rim) ────────────────────
    # Calculate centroid of all page vectors (the "Bias Cluster" center)
    all_vectors = [n["stance_vector"] for n in page_nodes if n["stance_vector"]]
    centroid = [0.0, 0.0, 0.0]
    if all_vectors:
        dims = len(all_vectors[0])
        centroid = [sum(v[d] for v in all_vectors) / len(all_vectors) for d in range(dims)]

    ghost_nodes = []
    for idx, cp in enumerate(counter_perspectives):
        # Create a synthetic vector that's distant from the centroid
        # Invert the centroid direction and add jitter for visual spread
        ghost_vector = [
            max(-1.0, min(1.0, -centroid[d] + (0.2 * (idx % 3 - 1))))
            for d in range(len(centroid))
        ]

        distance_from_cluster = _cosine_distance(ghost_vector, centroid)

        ghost_id = f"ghost_{cp.get('id', idx)}"
        ghost = {
            "id": ghost_id,
            "label": (cp.get("topic") or "Counter-perspective")[:50],
            "type": "ghost",
            "viewpoint": cp.get("viewpoint", ""),
            "stance_vector": ghost_vector,
            "distance_from_cluster": round(distance_from_cluster, 3),
            "mass": 6,
            "val": 8,
            "color": "rgba(239, 68, 68, 0.7)",  # Red ghost nodes
            "sources": cp.get("sources", []),
        }
        ghost_nodes.append(ghost)
        nodes.append(ghost)
        G.add_node(ghost_id, **ghost)

        # Connect ghost to the nearest page node (thin, long edge)
        if page_nodes:
            closest = min(
                page_nodes,
                key=lambda p: _cosine_distance(p["stance_vector"], ghost_vector)
            )
            link = {
                "source": ghost_id,
                "target": closest["id"],
                "similarity": round(1.0 - distance_from_cluster, 3),
                "width": 0.5,
                "color": "rgba(239, 68, 68, 0.25)",
                "dashed": True,
            }
            links.append(link)
            G.add_edge(ghost_id, closest["id"], weight=0.1)

    # ── 5. Graph Metrics ──────────────────────────────────────────────
    diameter = 0
    density = 0.0
    num_clusters = 0

    if len(G.nodes) >= 2:
        density = round(nx.density(G), 3)

        # Connected components = clusters
        components = list(nx.connected_components(G))
        num_clusters = len(components)

        # Diameter of largest connected component
        try:
            largest_cc = max(components, key=len)
            subgraph = G.subgraph(largest_cc)
            if nx.is_connected(subgraph) and len(subgraph.nodes) >= 2:
                diameter = nx.diameter(subgraph)
        except Exception:
            diameter = 0

    # Exposure score: wider graph = better bias elimination
    # Map diameter to 0-100 scale
    max_expected_diameter = max(len(page_nodes), 3)
    exposure_score = min(100, int((diameter / max(max_expected_diameter, 1)) * 100))

    # Cluster tightness: density close to 1.0 = echo chamber
    echo_chamber_risk = min(100, int(density * 100))

    metrics = {
        "diameter": diameter,
        "density": density,
        "num_clusters": num_clusters,
        "total_nodes": len(nodes),
        "total_edges": len(links),
        "bridge_nodes": len(bridge_nodes),
        "ghost_nodes": len(ghost_nodes),
        "exposure_score": exposure_score,
        "echo_chamber_risk": echo_chamber_risk,
        "session_bias_score": session_bias_score,
    }

    return {
        "nodes": nodes,
        "links": links,
        "metrics": metrics,
    }


def _bias_color(score: float) -> str:
    """Map bias score to a color gradient."""
    if score >= 7:
        return "#ef4444"   # Red — echo chamber
    elif score >= 4:
        return "#f59e0b"   # Amber — moderate
    else:
        return "#10b981"   # Green — balanced
