# context package — Person 3
# Public surface:
#   from context.context_builder import ContextBuilder   ← P1 uses this
#   from context.team_resolver import TeamResolver       ← internal / CLI
#   from context.exception_tagger import ExceptionTagger ← internal / CLI

try:
    from .context_builder import ContextBuilder
    from .team_resolver import TeamResolver
    from .exception_tagger import ExceptionTagger, ExceptionProfile
except ImportError:
    from context.context_builder import ContextBuilder  # type: ignore
    from context.team_resolver import TeamResolver  # type: ignore
    from context.exception_tagger import ExceptionTagger, ExceptionProfile  # type: ignore

__all__ = ["ContextBuilder", "TeamResolver", "ExceptionTagger", "ExceptionProfile"]
