import json


def parse_json_lines(output: str) -> list[dict]:
    """Parse one JSON object per line and ignore invalid lines."""
    items: list[dict] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def _split_number_and_unit(value: str) -> tuple[float, str]:
    number = []
    unit = []

    for char in value.strip():
        if char.isdigit() or char == ".":
            number.append(char)
        elif not char.isspace():
            unit.append(char)

    if not number:
        return 0.0, ""

    return float("".join(number)), "".join(unit).lower()


def parse_size_mb(value: str) -> float:
    """Convert Docker sizes like KiB, MiB, or GiB to MB."""
    amount, suffix = _split_number_and_unit(value)

    if suffix.startswith("g"):
        return amount * 1024
    if suffix.startswith("k"):
        return amount / 1024
    if suffix.startswith("b"):
        return amount / (1024 * 1024)
    return amount


def extract_memory_usage(value: str) -> str:
    """Return only the used part from Docker's 'used / limit' memory format."""
    used = value.split("/", maxsplit=1)[0].strip()
    return f"{parse_size_mb(used):.1f} MB"