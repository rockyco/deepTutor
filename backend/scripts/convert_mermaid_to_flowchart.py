"""Convert mermaid flowchart strings in lesson JSON files to structured flowchart format.

Usage:
    uv run python scripts/convert_mermaid_to_flowchart.py
"""

import json
import re
from pathlib import Path

LESSONS_DIR = Path(__file__).parent.parent / "data" / "lessons"

# Color mapping from mermaid fill colors to node styles
FILL_TO_STYLE = {
    "#f96": "warning",
    "#f9f": "primary",
    "#fbb": "primary",
    "#6f9": "highlight",
    "#99f": "highlight",
    "#ff9": "highlight",
    "#daf": "primary",
    "#9f9": "highlight",
}

# Pattern to match mermaid node definitions inline:
# A["label"], A[label], A{"label"}, A{label}, A("label"), A((label))
NODE_DEF_RE = re.compile(
    r'(\w+)\s*'          # node ID
    r'([\[\({]+)'        # opening brackets
    r'"?'                # optional opening quote
    r'([^"\]\)]*?)'      # label content (non-greedy)
    r'"?'                # optional closing quote
    r'([\]\)}]+)'        # closing brackets
)


def _extract_and_strip_nodes(line: str, nodes: dict, current_subgraph: dict | None) -> str:
    """Extract node defs from a line and replace them with just their IDs."""
    def replacer(m):
        nid = m.group(1)
        label = m.group(3).replace("\\n", "\n")
        opening = m.group(2)
        if nid not in nodes:
            is_decision = "{" in opening
            nodes[nid] = {"id": nid, "label": label}
            if is_decision:
                nodes[nid]["_shape"] = "decision"
            if current_subgraph is not None:
                current_subgraph["nodeIds"].append(nid)
        return nid  # Replace full node def with just the ID

    return NODE_DEF_RE.sub(replacer, line)


def parse_mermaid(code: str) -> dict | None:
    """Parse mermaid flowchart syntax into structured flowchart data."""
    lines = code.strip().split("\n")
    if not lines:
        return None

    header = lines[0].strip()

    # Handle mindmap - convert to a simple radial flowchart
    if header.startswith("mindmap"):
        return parse_mindmap(lines)

    # Parse flowchart direction
    m = re.match(r"flowchart\s+(TD|LR|TB)", header)
    if not m:
        return None
    direction = m.group(1)
    if direction == "TB":
        direction = "TD"

    nodes: dict[str, dict] = {}  # id -> {label, style, ...}
    edges: list[dict] = []
    styles: dict[str, str] = {}  # node_id -> style
    subgraphs: list[dict] = []
    current_subgraph: dict | None = None

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # Skip direction directives inside subgraphs
        if line.startswith("direction "):
            continue

        # Subgraph start
        sg_match = re.match(r"subgraph\s+(.+)", line)
        if sg_match:
            current_subgraph = {"label": sg_match.group(1).strip(), "nodeIds": []}
            continue

        # Subgraph end
        if line == "end":
            if current_subgraph:
                sg_id = "sg_" + re.sub(r"\W+", "_", current_subgraph["label"].lower())
                current_subgraph["id"] = sg_id
                subgraphs.append(current_subgraph)
                current_subgraph = None
            continue

        # Style directives
        style_match = re.match(r"style\s+(\w+)\s+fill:(#[0-9a-fA-F]+)", line)
        if style_match:
            node_id = style_match.group(1)
            fill = style_match.group(2).lower()
            styles[node_id] = FILL_TO_STYLE.get(fill, "highlight")
            continue

        # Step 1: Extract inline node definitions, replacing them with just IDs
        simplified = _extract_and_strip_nodes(line, nodes, current_subgraph)

        # Step 2: Parse edges from the simplified line (now just IDs and arrows)
        edge_patterns = [
            # A -->|"label"| B  or  A -->|label| B
            r'(\w+)\s*-->\|"?([^"|]+)"?\|\s*(\w+)',
            # A -- "label" --> B
            r'(\w+)\s*--\s*"([^"]+)"\s*-->\s*(\w+)',
            # A --> B (simple arrow)
            r"(\w+)\s*-->\s*(\w+)",
            # A --- B (line, no arrow)
            r"(\w+)\s*---\s*(\w+)",
            # A -.- B (dotted)
            r"(\w+)\s*-\.-\s*(\w+)",
        ]

        for pat in edge_patterns:
            for em in re.finditer(pat, simplified):
                groups = em.groups()
                if len(groups) == 3:
                    src, label, tgt = groups
                    edges.append({"from": src, "to": tgt, "label": label})
                else:
                    src, tgt = groups[0], groups[1]
                    edges.append({"from": src, "to": tgt})
            # Only use first matching pattern to avoid double-matches
            if re.search(pat, simplified):
                break

    # Apply styles to nodes
    for nid, style in styles.items():
        if nid in nodes:
            nodes[nid]["style"] = style

    # Apply decision shape as style where no explicit style set
    for n in nodes.values():
        if n.get("_shape") == "decision" and "style" not in n:
            n["style"] = "decision"
        n.pop("_shape", None)

    # Ensure all edge endpoints are nodes
    for edge in edges:
        for key in ("from", "to"):
            nid = edge[key]
            if nid not in nodes:
                nodes[nid] = {"id": nid, "label": nid}

    # Assign default styles: first node = primary, others without style = step
    node_list = list(nodes.values())
    if node_list and "style" not in node_list[0]:
        node_list[0]["style"] = "primary"
    for n in node_list:
        if "style" not in n:
            n["style"] = "step"

    # Remove self-loops (e.g., D --> D)
    edges = [e for e in edges if e["from"] != e["to"]]

    # Remove duplicate edges
    seen_edges = set()
    unique_edges = []
    for e in edges:
        key = (e["from"], e["to"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)
    edges = unique_edges

    result = {
        "type": "flowchart",
        "direction": direction,
        "nodes": node_list,
        "edges": edges,
    }
    if subgraphs:
        result["subgraphs"] = subgraphs

    return result


def parse_mindmap(lines: list[str]) -> dict:
    """Convert a mindmap to a radial flowchart structure."""
    nodes = []
    edges = []

    # Parse indentation-based mindmap
    stack: list[tuple[int, str]] = []  # (indent, id)
    node_counter = 0

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue

        indent = len(line) - len(line.lstrip())

        # Extract label from root((label)) or plain text
        root_match = re.match(r"root\(\((.+)\)\)", stripped)
        if root_match:
            label = root_match.group(1)
        else:
            label = stripped

        nid = f"N{node_counter}"
        node_counter += 1

        style = "primary" if root_match else "step"
        nodes.append({"id": nid, "label": label, "style": style})

        # Pop stack to find parent
        while stack and stack[-1][0] >= indent:
            stack.pop()

        if stack:
            parent_id = stack[-1][1]
            edges.append({"from": parent_id, "to": nid})

        stack.append((indent, nid))

    return {
        "type": "flowchart",
        "direction": "TD",
        "nodes": nodes,
        "edges": edges,
    }


def convert_file(filepath: Path) -> int:
    """Convert all mermaid visuals in a lesson JSON file. Returns count of conversions."""
    with open(filepath) as f:
        lessons = json.load(f)

    count = 0
    for lesson in lessons:
        for section in lesson.get("sections", []):
            visual = section.get("visual")
            if not visual or visual.get("type") != "mermaid":
                continue

            result = parse_mermaid(visual["code"])
            if result:
                section["visual"] = result
                count += 1
            else:
                print(f"  WARNING: Could not parse mermaid in {lesson['questionType']}")

    with open(filepath, "w") as f:
        json.dump(lessons, f, indent=2, ensure_ascii=False)

    return count


def main():
    files = sorted(LESSONS_DIR.glob("*_lessons.json"))
    total = 0
    for f in files:
        print(f"Processing {f.name}...")
        n = convert_file(f)
        print(f"  Converted {n} visuals")
        total += n
    print(f"\nTotal: {total} visuals converted")


if __name__ == "__main__":
    main()
