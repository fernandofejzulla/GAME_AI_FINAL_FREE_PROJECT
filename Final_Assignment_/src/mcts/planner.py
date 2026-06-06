"""
MCTS-based village layout planner (Layer 3)
"""
import math
import random
from collections import Counter
from typing import List, Tuple

from src.pcg.placement import evaluate_footprint


#Building types 
CHAPEL = "chapel"
CHURCH = "church"
HOUSE = "house"

#A placement is (x, z, building_type, ground_y)
Placement = Tuple[int, int, str, int]


def get_candidate_positions(heightmap, rect, build_area, step: int = 5, footprint: int = 9,
                             min_ground_y: int = None):
    """Find buildable positions, if min_ground_y is None auto-detect from terrain"""
    import numpy as np

    #Auto-detect
    if min_ground_y is None:
        valid = heightmap[heightmap > 0]
        min_ground_y = int(np.percentile(valid, 30)) if len(valid) > 0 else 66

    candidates = []
    sx = build_area.offset.x + 4
    sz = build_area.offset.z + 4
    ex = build_area.offset.x + build_area.size.x - footprint - 4
    ez = build_area.offset.z + build_area.size.z - footprint - 4
    for x in range(sx, ex, step):
        for z in range(sz, ez, step):
            result = evaluate_footprint(heightmap, rect, x, z, footprint, footprint)
            if result is None:
                continue
            ground_y, fill_below = result
            if ground_y < min_ground_y:
                continue

            check_points = [
                (x, z),
                (x + footprint - 1, z),
                (x, z + footprint - 1),
                (x + footprint - 1, z + footprint - 1),
                (x + footprint // 2, z + footprint // 2),
            ]
            valid = True
            for cx, cz in check_points:
                cr = evaluate_footprint(heightmap, rect, cx, cz, 1, 1)
                if cr is None or cr[0] < min_ground_y - 2:
                    valid = False
                    break
            if not valid:
                continue

            candidates.append((x, z, ground_y, fill_below))
    return candidates

def next_building_type(placements: List[Placement]) -> str:
    """Determine which building type comes next"""
    types = [p[2] for p in placements]
    if CHAPEL not in types:
        return CHAPEL
    if CHURCH not in types:
        return CHURCH
    return HOUSE


def is_too_close(x: int, z: int, placements: List[Placement], min_dist: int = 9) -> bool:
    for px, pz, _, _ in placements:
        if abs(x - px) < min_dist and abs(z - pz) < min_dist:
            return True
    return False


def score_layout(placements, weights: dict = None) -> float:
    """Score a village layout, higher is better"""
    if weights is None:
        weights = {
            "flatness": 0.10,
            "spacing": 0.25,
            "compactness": 0.15,
            "centrality": 0.25,
            "variety": 0.15,
            "connectivity": 0.10,
        }
    if not placements:
        return 0.0

    #Flatness
    ys = [p[3] for p in placements]
    if len(ys) > 1:
        mean_y = sum(ys) / len(ys)
        var = sum((y - mean_y) ** 2 for y in ys) / len(ys)
        flatness = max(0.0, 1.0 - math.sqrt(var) / 5.0)
    else:
        flatness = 1.0

    #Spacing + track max pair dist for compactness
    n_pairs = 0
    spacing_total = 0.0
    max_pair_dist = 0.0
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            xi, zi, _, _ = placements[i]
            xj, zj, _, _ = placements[j]
            dist = math.sqrt((xi - xj) ** 2 + (zi - zj) ** 2)
            max_pair_dist = max(max_pair_dist, dist)
            if dist < 8:
                spacing_total -= 1.0
            elif 12 <= dist <= 25:
                spacing_total += 1.0
            elif dist > 35:
                spacing_total += 0.2
            else:
                spacing_total += 0.5
            n_pairs += 1
    spacing = max(0.0, spacing_total / max(1, n_pairs))

    #Compactness
    if max_pair_dist <= 40:
        compactness = 1.0
    elif max_pair_dist <= 65:
        compactness = 1.0 - (max_pair_dist - 40) / 25.0
    else:
        compactness = 0.0

    #Centrality: chapel should sit near the village centroid
    chapel = next((p for p in placements if p[2] == 'chapel'), None)
    if chapel is not None and len(placements) > 1:
        cx = sum(p[0] for p in placements) / len(placements)
        cz = sum(p[1] for p in placements) / len(placements)
        dist_to_center = math.sqrt((chapel[0] - cx) ** 2 + (chapel[1] - cz) ** 2)
        if dist_to_center <= 5:
            centrality = 1.0
        elif dist_to_center <= 15:
            centrality = 1.0 - (dist_to_center - 5) / 10.0
        else:
            centrality = 0.0
    else:
        centrality = 0.5

    #Variety
    type_count = len(set(p[2] for p in placements))
    variety = min(1.0, type_count / 3.0)

    #Connectivity
    if len(placements) <= 1:
        connectivity = 1.0
    else:
        visited = {0}
        frontier = [0]
        while frontier:
            i = frontier.pop()
            for j in range(len(placements)):
                if j in visited:
                    continue
                xi, zi, _, _ = placements[i]
                xj, zj, _, _ = placements[j]
                if math.sqrt((xi - xj) ** 2 + (zi - zj) ** 2) < 25:
                    visited.add(j)
                    frontier.append(j)
        connectivity = len(visited) / len(placements)

    return (
        weights["flatness"] * flatness
        + weights["spacing"] * spacing
        + weights["compactness"] * compactness
        + weights["centrality"] * centrality
        + weights["variety"] * variety
        + weights["connectivity"] * connectivity
    )

class MCTSNode:
    """A single node in the MCTS search tree"""
    def __init__(self, placements, candidates, target_size, parent=None, action=None):
        self.placements = placements
        self.candidates = candidates
        self.target_size = target_size
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.total_score = 0.0
        self._untried = self._available_actions()

    def _available_actions(self):
        if len(self.placements) >= self.target_size:
            return []
        return [
            i for i, (x, z, _, _) in enumerate(self.candidates)
            if not is_too_close(x, z, self.placements)
        ]

    def is_terminal(self):
        return len(self.placements) >= self.target_size

    def is_fully_expanded(self):
        return len(self._untried) == 0

    def expand(self):
        action_idx = self._untried.pop()
        x, z, gy, _ = self.candidates[action_idx]
        new_placements = self.placements + [(x, z, next_building_type(self.placements), gy)]
        child = MCTSNode(new_placements, self.candidates, self.target_size,
                         parent=self, action=action_idx)
        self.children.append(child)
        return child

    def best_child(self, c: float = math.sqrt(2)):
        return max(
            self.children,
            key=lambda n: (n.total_score / n.visits)
                          + c * math.sqrt(math.log(self.visits) / n.visits),
        )

    def rollout(self, rng: random.Random) -> float:
        """Random simulation from this node to a complete layout"""
        placements = list(self.placements)
        while len(placements) < self.target_size:
            avail = [
                i for i, (x, z, _, _) in enumerate(self.candidates)
                if not is_too_close(x, z, placements)
            ]
            if not avail:
                break
            idx = rng.choice(avail)
            x, z, gy, _ = self.candidates[idx]
            placements.append((x, z, next_building_type(placements), gy))
        return score_layout(placements)

    def backpropagate(self, score: float):
        node = self
        while node is not None:
            node.visits += 1
            node.total_score += score
            node = node.parent


def mcts_search(candidates, target_size: int = 12, iterations: int = 500, seed: int = 42) -> List[Placement]:
    """Run MCTS and return the best-found layout"""
    rng = random.Random(seed)
    root = MCTSNode([], candidates, target_size)

    for _ in range(iterations):
        node = root
        while not node.is_terminal() and node.is_fully_expanded() and node.children:
            node = node.best_child()
        if not node.is_terminal() and node._untried:
            node = node.expand()
        score = node.rollout(rng)
        node.backpropagate(score)

    #Extract best path: greedy down the tree by visit count, then rollout if needed
    placements = []
    node = root
    while node.children:
        node = max(node.children, key=lambda n: n.visits)
        x, z, gy, _ = candidates[node.action]
        placements.append((x, z, next_building_type(placements), gy))
    while len(placements) < target_size:
        avail = [i for i, (x, z, _, _) in enumerate(candidates) if not is_too_close(x, z, placements)]
        if not avail:
            break
        idx = rng.choice(avail)
        x, z, gy, _ = candidates[idx]
        placements.append((x, z, next_building_type(placements), gy))
    return placements


def random_layout(candidates, target_size: int = 12, seed: int = 42) -> List[Placement]:
    """Generate a random valid layout (baseline for the experiment)"""
    rng = random.Random(seed)
    placements = []
    while len(placements) < target_size:
        avail = [i for i, (x, z, _, _) in enumerate(candidates) if not is_too_close(x, z, placements)]
        if not avail:
            break
        idx = rng.choice(avail)
        x, z, gy, _ = candidates[idx]
        placements.append((x, z, next_building_type(placements), gy))
    return placements