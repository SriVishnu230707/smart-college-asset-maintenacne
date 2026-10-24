"""Small helpers for comparing observed lab statements with predictions."""


def statements_by_phase(trace, phases):
    """Group requested phases in one pass, retaining empty phases and SQL order."""
    grouped = {phase: [] for phase in phases}
    for phase, kind in trace:
        if phase in grouped:
            grouped[phase].append(kind)
    return grouped
