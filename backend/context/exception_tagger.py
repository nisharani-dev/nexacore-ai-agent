"""
exception_tagger.py  —  Person 3 (Context Builder)
----------------------------------------------------
Reads the exception_flows section of teams.yaml and returns
structured exception metadata for a given employment_type.

Also generates Hindsight memory tags for the exception layer,
so P2's memory writer can tag exception-type memories correctly.

Usage (standalone):
    python exception_tagger.py contractor
    python exception_tagger.py intern
"""

import sys
import yaml
from dataclasses import dataclass, field
from pathlib import Path

TEAMS_YAML = Path(__file__).resolve().parents[2] / "config" / "teams.yaml"

VALID_TYPES = {"fte", "contractor", "intern"}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ExceptionProfile:
    """
    Structured exception data for a specific employment type.
    Passed into the ContextBlock and surfaced to P1's prompt assembler.
    """
    employment_type: str
    jira_license: str
    github_org_team: str
    aws_account: str
    restricted_spaces: list[str] = field(default_factory=list)
    extra_steps: list[str] = field(default_factory=list)
    notes: str = ""
    memory_tags: list[str] = field(default_factory=list)

    def has_restrictions(self) -> bool:
        return bool(self.restricted_spaces or self.extra_steps)

    def summary_lines(self) -> list[str]:
        """
        Human-readable bullet points for inclusion in the assembled prompt.
        P1 can call this directly when building the final LLM context.
        """
        lines = []
        if self.employment_type != "fte":
            lines.append(
                f"⚠️  You are a {self.employment_type.upper()} — your provisioning path differs from standard employees."
            )
        lines.append(f"Jira license type: {self.jira_license}")
        lines.append(f"GitHub team: {self.github_org_team}")
        lines.append(f"AWS account: {self.aws_account}")
        if self.restricted_spaces:
            lines.append("Restricted Confluence spaces (no access):")
            for s in self.restricted_spaces:
                lines.append(f"  • {s}")
        if self.extra_steps:
            lines.append("Extra steps required before standard provisioning:")
            for step in self.extra_steps:
                lines.append(f"  • {step}")
        if self.notes:
            lines.append(f"Note: {self.notes.strip()}")
        return lines


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_exception_flows(yaml_path: Path = TEAMS_YAML) -> dict:
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("exception_flows", {})


# ── Main class ────────────────────────────────────────────────────────────────

class ExceptionTagger:
    """
    Returns an ExceptionProfile for a given employment_type string.
    Also produces Hindsight-compatible memory tags for the exception layer.
    """

    def __init__(self, yaml_path: Path = TEAMS_YAML):
        self._flows = _load_exception_flows(yaml_path)

    def tag(self, employment_type: str) -> ExceptionProfile:
        """
        Returns an ExceptionProfile for the given employment_type.
        Falls back to "fte" if the type is unrecognised.
        """
        emp_type = employment_type.lower().strip()
        if emp_type not in VALID_TYPES:
            print(
                f"[ExceptionTagger] Warning: unknown employment_type '{emp_type}'. "
                f"Falling back to 'fte'."
            )
            emp_type = "fte"

        flow = self._flows.get(emp_type, self._flows.get("fte", {}))

        # Generate memory tags for Hindsight (P2 uses these when writing exceptions)
        memory_tags = self._build_memory_tags(emp_type)

        return ExceptionProfile(
            employment_type=emp_type,
            jira_license=flow.get("jira_license", "JIRA-SOFTWARE"),
            github_org_team=flow.get("github_org_team", "employees"),
            aws_account=flow.get("aws_account", "acmecorp-main"),
            restricted_spaces=flow.get("restricted_spaces", []),
            extra_steps=flow.get("extra_steps", []),
            notes=flow.get("notes", ""),
            memory_tags=memory_tags,
        )

    def get_memory_namespace_tag(self, employment_type: str) -> str:
        """
        Returns the Hindsight namespace tag string for this employment type.
        P2's writer.py uses this when tagging exception memories.

        e.g. "exception:contractor", "exception:intern"
        """
        emp_type = employment_type.lower().strip()
        if emp_type not in VALID_TYPES:
            emp_type = "fte"
        return f"exception:{emp_type}"

    # ── Internal ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_memory_tags(employment_type: str) -> list[str]:
        """
        Builds a list of Hindsight tags for memory retrieval.
        All exception memories are tagged with both the type-specific
        tag and a generic "exception" tag.
        """
        return [
            f"exception:{employment_type}",
            "exception:all",          # catch-all for memories relevant to all non-standard types
        ]


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    employment_type = sys.argv[1] if len(sys.argv) > 1 else "fte"
    tagger = ExceptionTagger()

    profile = tagger.tag(employment_type)

    print(f"\n── Exception Profile: {profile.employment_type.upper()} ──")
    print(f"  Jira license:      {profile.jira_license}")
    print(f"  GitHub team:       {profile.github_org_team}")
    print(f"  AWS account:       {profile.aws_account}")
    print(f"  Memory tags:       {profile.memory_tags}")
    print(f"  Has restrictions:  {profile.has_restrictions()}")
    print()
    print("  Summary (as it would appear in LLM prompt):")
    for line in profile.summary_lines():
        print(f"    {line}")