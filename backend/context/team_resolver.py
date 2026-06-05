"""
team_resolver.py  —  Person 3 (Context Builder)
-------------------------------------------------
Given a user-supplied team name (e.g. "infra security" or "infra_security"),
resolves the full ancestor path through the YAML hierarchy.

Returns a TeamPath with all ancestor IDs and names from company → leaf.

Usage (standalone):
    python team_resolver.py "infra security"
    python team_resolver.py "data platform"
"""

import sys
import yaml
from pathlib import Path
from typing import Optional

# Import shared interfaces (P1's contract)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from interfaces import TeamPath

# ── Config path ─────────────────────────────────────────────────────────────
TEAMS_YAML = Path(__file__).resolve().parents[2] / "config" / "teams.yaml"


# ── Internal tree node ────────────────────────────────────────────────────────

class _TeamNode:
    """Internal representation of one node in the team tree."""
    def __init__(self, id_: str, name: str, type_: str,
                 accesses: list, notes: str, parent: Optional["_TeamNode"] = None):
        self.id = id_
        self.name = name
        self.type = type_
        self.accesses: list[str] = accesses or []
        self.notes: str = notes or ""
        self.parent = parent
        self.children: list["_TeamNode"] = []

    def ancestor_path(self) -> list["_TeamNode"]:
        """Return list from root → self (inclusive)."""
        path = []
        node = self
        while node:
            path.append(node)
            node = node.parent
        return list(reversed(path))


# ── YAML loader ───────────────────────────────────────────────────────────────

def _load_tree(yaml_path: Path = TEAMS_YAML) -> _TeamNode:
    """
    Parse teams.yaml into a tree of _TeamNode objects.
    Returns the root (company) node.
    """
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    company_data = data["company"]
    root = _TeamNode(
        id_=company_data["id"],
        name=company_data["name"],
        type_=company_data["type"],
        accesses=company_data.get("accesses", []),
        notes=company_data.get("notes", ""),
    )

    _parse_children(root, company_data)
    return root


def _parse_children(parent_node: _TeamNode, parent_data: dict):
    """Recursively attach children (divisions → teams → sub_teams)."""
    for key in ("divisions", "teams", "sub_teams"):
        for child_data in parent_data.get(key, []):
            child = _TeamNode(
                id_=child_data["id"],
                name=child_data["name"],
                type_=child_data["type"],
                accesses=child_data.get("accesses", []),
                notes=child_data.get("notes", ""),
                parent=parent_node,
            )
            parent_node.children.append(child)
            _parse_children(child, child_data)


# ── Resolver ──────────────────────────────────────────────────────────────────

class TeamResolver:
    """
    Resolves a fuzzy team name into a full TeamPath.

    Fuzzy matching: normalises input + stored IDs/names to lowercase,
    strips spaces/underscores/hyphens. So "Infra Security", "infra_security",
    "infra-security", "infrasecurity" all resolve to the same node.
    """

    def __init__(self, yaml_path: Path = TEAMS_YAML):
        self._root = _load_tree(yaml_path)
        # Build a flat index: normalised_key → _TeamNode
        self._index: dict[str, _TeamNode] = {}
        self._build_index(self._root)

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve(self, team_name: str) -> TeamPath:
        """
        Given a team name, return a TeamPath from company root → that team.
        Raises ValueError if the team cannot be found.
        """
        key = self._normalise(team_name)
        node = self._index.get(key)
        if node is None:
            suggestions = self._suggest(key)
            raise ValueError(
                f"Team '{team_name}' not found in hierarchy.\n"
                f"Did you mean one of: {suggestions}"
            )

        ancestors = node.ancestor_path()
        return TeamPath(
            ids=[n.id for n in ancestors],
            names=[n.name for n in ancestors],
        )

    def resolve_with_nodes(self, team_name: str) -> list[_TeamNode]:
        """
        Same as resolve() but returns the raw _TeamNode list (ancestor → leaf).
        Used internally by context_builder.py for access list merging.
        """
        key = self._normalise(team_name)
        node = self._index.get(key)
        if node is None:
            raise ValueError(f"Team '{team_name}' not found.")
        return node.ancestor_path()

    def list_all_teams(self) -> list[dict]:
        """Return a flat list of all teams with id, name, type — useful for UI dropdowns."""
        results = []
        self._collect_teams(self._root, results)
        return results

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_index(self, node: _TeamNode):
        # Index by normalised ID and by normalised name (both)
        self._index[self._normalise(node.id)] = node
        self._index[self._normalise(node.name)] = node
        for child in node.children:
            self._build_index(child)

    @staticmethod
    def _normalise(s: str) -> str:
        """Lowercase + remove spaces, underscores, hyphens."""
        return s.lower().replace(" ", "").replace("_", "").replace("-", "")

    def _suggest(self, normalised_query: str) -> list[str]:
        """Return up to 3 closest key names for helpful error messages."""
        all_names = [n.name for n in self._index.values()]
        # Simple substring match as suggestions
        matches = [
            name for name in all_names
            if normalised_query[:4] in self._normalise(name)
        ]
        return matches[:3] or list({n.name for n in self._index.values()})[:5]

    def _collect_teams(self, node: _TeamNode, out: list):
        out.append({"id": node.id, "name": node.name, "type": node.type})
        for child in node.children:
            self._collect_teams(child, out)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python team_resolver.py <team_name>")
        print("\nAll known teams:")
        resolver = TeamResolver()
        for t in resolver.list_all_teams():
            indent = "  " * (["company", "division", "org", "team", "sub_team"]
                             .index(t["type"]) if t["type"] in
                             ["company", "division", "org", "team", "sub_team"] else 1)
            print(f"  {indent}{t['name']}  [{t['id']}]")
        sys.exit(0)

    team_input = " ".join(sys.argv[1:])
    resolver = TeamResolver()

    try:
        path = resolver.resolve(team_input)
        print(f"\n✓  Resolved: {path}")
        print(f"\n   Path IDs: {path.ids}")
    except ValueError as e:
        print(f"\n✗  {e}")
        sys.exit(1)