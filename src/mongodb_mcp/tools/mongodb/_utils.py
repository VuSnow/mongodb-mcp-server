def _format_not_found(result: dict) -> str:
    """Format a not_found response with suggestions for user to confirm."""
    label = result["label"]
    name = result["name"]
    suggestions = result.get("suggestions", [])
    msg = f'{label} "{name}" not found.'
    if suggestions:
        msg += "\nDid you mean one of these?\n"
        msg += "\n".join(f"  - {s}" for s in suggestions)
        msg += "\nPlease confirm the correct name and try again."
    return msg
