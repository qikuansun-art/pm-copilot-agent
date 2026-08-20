"""Deterministic ProductFlow-to-Mermaid conversion."""

import re

from models.flow import ProductFlow


_LABEL_TRANSLATION = str.maketrans(
    {
        '"': "'",
        "\n": " ",
        "\r": " ",
        "[": "［",
        "]": "］",
        "{": "｛",
        "}": "｝",
        "(": "（",
        ")": "）",
        "|": "｜",
        "<": "＜",
        ">": "＞",
        "&": "＆",
        "#": "＃",
    }
)


def _safe_label(value: str) -> str:
    """Flatten and neutralize Mermaid delimiter characters in labels."""
    return " ".join(value.translate(_LABEL_TRANSLATION).split())


def _node_ids(flow: ProductFlow) -> dict[str, str]:
    """Create stable Mermaid-safe aliases while preserving valid IDs."""
    aliases: dict[str, str] = {}
    used: set[str] = set()
    for index, node in enumerate(flow.nodes, start=1):
        base = re.sub(r"[^A-Za-z0-9_]", "_", node.id)
        if not base or base[0].isdigit():
            base = f"n_{base or index}"
        alias = base
        suffix = 2
        while alias in used:
            alias = f"{base}_{suffix}"
            suffix += 1
        aliases[node.id] = alias
        used.add(alias)
    return aliases


def product_flow_to_mermaid(flow: ProductFlow) -> str:
    """Convert ProductFlow into deterministic top-to-bottom Mermaid text."""
    aliases = _node_ids(flow)
    lines = ["flowchart TD"]
    for node in flow.nodes:
        node_id = aliases[node.id]
        label = _safe_label(node.label)
        if node.node_type in {"start", "end"}:
            lines.append(f"{node_id}([{label}])")
        elif node.node_type == "decision":
            lines.append(f"{node_id}{{{label}}}")
        else:
            lines.append(f"{node_id}[{label}]")
    for edge in flow.edges:
        source = aliases[edge.source]
        target = aliases[edge.target]
        label = _safe_label(edge.label)
        lines.append(
            f"{source} -->|{label}| {target}"
            if label
            else f"{source} --> {target}"
        )
    return "\n".join(lines)
