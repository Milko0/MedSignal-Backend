"""Label sections arrive as arrays of strings. The label-gap search uses the union of the warning sections."""

WARNING_SECTIONS = ("warnings_and_cautions", "warnings", "precautions")


def section_text(value) -> str:
    """str | list[str] | None -> one string joined with newlines."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return "\n".join(str(v).strip() for v in value if str(v).strip())


def warnings_union(raw_label: dict) -> str:
    """Union of warnings_and_cautions, warnings and precautions (Rx labels use either generation of fields)."""
    return "\n".join(t for t in (section_text(raw_label.get(k)) for k in WARNING_SECTIONS) if t)
