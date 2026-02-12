#!/usr/bin/env python3
"""
Parse app.bicep and generate an architecture diagram with a GitHub UI look-and-feel.
Outputs a PNG image to docs/architecture.png.
"""

import re
import os
import sys
from pathlib import Path

try:
    import graphviz
except ImportError:
    print("Installing graphviz python package...")
    os.system(f"{sys.executable} -m pip install graphviz")
    import graphviz


def parse_bicep(bicep_path: str) -> tuple[list[dict], list[dict]]:
    """Parse a Bicep file and extract resources and connections."""
    with open(bicep_path, "r") as f:
        content = f.read()

    resources = []
    connections = []

    # Match resource blocks: resource <symbolic_name> '<type>' = {
    resource_pattern = re.compile(
        r"resource\s+(\w+)\s+'([^']+)'\s*=\s*\{(.*?)\n\}",
        re.DOTALL,
    )

    for match in resource_pattern.finditer(content):
        symbolic_name = match.group(1)
        resource_type = match.group(2)
        body = match.group(3)

        # Extract the 'name' property
        name_match = re.search(r"name:\s*'([^']+)'", body)
        display_name = name_match.group(1) if name_match else symbolic_name

        # Extract image if present
        image_match = re.search(r"image:\s*'([^']+)'", body)
        image = image_match.group(1) if image_match else None

        # Extract container port
        port_match = re.search(r"containerPort:\s*(\d+)", body)
        port = port_match.group(1) if port_match else None

        # Determine resource category
        if "containers" in resource_type.lower():
            category = "container"
        elif "rediscaches" in resource_type.lower():
            category = "datastore"
        elif "sqldatabases" in resource_type.lower():
            category = "datastore"
        elif "mongodatabases" in resource_type.lower():
            category = "datastore"
        elif "applications" in resource_type.lower() and "containers" not in resource_type.lower():
            category = "application"
        else:
            category = "other"

        resources.append({
            "symbolic_name": symbolic_name,
            "display_name": display_name,
            "resource_type": resource_type,
            "image": image,
            "port": port,
            "category": category,
        })

        # Extract connections from the body
        conn_pattern = re.compile(r"connections:\s*\{(.*?)\n\s*\}", re.DOTALL)
        conn_match = conn_pattern.search(body)
        if conn_match:
            conn_body = conn_match.group(1)
            conn_entries = re.findall(r"(\w+):\s*\{", conn_body)
            for target in conn_entries:
                connections.append({
                    "from": symbolic_name,
                    "to": target,
                })

        # Extract connections via source references like database.id
        source_refs = re.findall(r"source:\s*(\w+)\.(id|connectionString)", body)
        for ref_name, _ in source_refs:
            # Avoid duplicates
            conn = {"from": symbolic_name, "to": ref_name}
            if conn not in connections:
                connections.append(conn)

    return resources, connections


def get_icon(category: str) -> str:
    """Return an emoji-style label prefix based on category."""
    icons = {
        "container": "📦",
        "datastore": "🗄️",
        "application": "🔷",
        "other": "⚙️",
    }
    return icons.get(category, "⚙️")


def generate_graph(resources: list[dict], connections: list[dict], output_path: str):
    """Generate an architecture diagram with GitHub-inspired styling."""

    dot = graphviz.Digraph(
        "architecture",
        format="png",
        engine="dot",
    )

    # GitHub-inspired global styling
    dot.attr(
        rankdir="LR",
        bgcolor="#0d1117",
        fontname="Segoe UI, Helvetica, Arial, sans-serif",
        fontcolor="#e6edf3",
        pad="0.5",
        nodesep="1",
        ranksep="1.5",
        label="Architecture · app.bicep",
        labelloc="t",
        fontsize="18",
        style="rounded",
    )

    # Default node styling (GitHub dark theme)
    dot.attr(
        "node",
        shape="box",
        style="filled,rounded",
        fillcolor="#161b22",
        color="#30363d",
        fontcolor="#e6edf3",
        fontname="Segoe UI, Helvetica, Arial, sans-serif",
        fontsize="12",
        margin="0.3,0.2",
        penwidth="1.5",
    )

    # Default edge styling
    dot.attr(
        "edge",
        color="#58a6ff",
        fontcolor="#8b949e",
        fontname="Segoe UI, Helvetica, Arial, sans-serif",
        fontsize="10",
        arrowsize="0.8",
        penwidth="1.5",
    )

    # Color scheme per category (GitHub palette)
    category_colors = {
        "container": {"fillcolor": "#161b22", "color": "#58a6ff"},   # Blue border
        "datastore": {"fillcolor": "#161b22", "color": "#f78166"},   # Orange border
        "application": {"fillcolor": "#161b22", "color": "#3fb950"}, # Green border
        "other": {"fillcolor": "#161b22", "color": "#8b949e"},       # Gray border
    }

    # Build a lookup from symbolic_name -> resource
    resource_map = {r["symbolic_name"]: r for r in resources}

    # Add nodes (skip the top-level application resource)
    for res in resources:
        if res["category"] == "application":
            continue

        icon = get_icon(res["category"])
        colors = category_colors.get(res["category"], category_colors["other"])

        # Build label
        lines = [f"{icon}  {res['display_name']}"]
        if res["image"]:
            lines.append(f"{res['image']}")
        if res["port"]:
            lines.append(f":{res['port']}")

        label = "\\n".join(lines)

        dot.node(
            res["symbolic_name"],
            label=label,
            fillcolor=colors["fillcolor"],
            color=colors["color"],
            penwidth="2",
        )

    # Add edges
    for conn in connections:
        if conn["from"] in resource_map and conn["to"] in resource_map:
            from_res = resource_map[conn["from"]]
            to_res = resource_map[conn["to"]]
            # Skip edges from/to the application node
            if from_res["category"] == "application" or to_res["category"] == "application":
                continue
            dot.edge(conn["from"], conn["to"])

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Render (graphviz appends .png automatically)
    output_base = output_path.removesuffix(".png")
    dot.render(output_base, cleanup=True)
    print(f"Architecture diagram saved to {output_path}")


def update_readme(readme_path: str, image_rel_path: str):
    """Update the Architecture section in README.md with the generated image."""
    with open(readme_path, "r") as f:
        content = f.read()

    # Replace the Architecture section content
    # Match from "## Architecture" to the next "##" heading or end of file
    pattern = re.compile(
        r"(## Architecture\s*\n).*?(\n## |\Z)",
        re.DOTALL,
    )

    replacement_content = (
        f"\\1\n"
        f"![Architecture Diagram]({image_rel_path})\n"
        f"\n"
        f"\\2"
    )

    if pattern.search(content):
        new_content = pattern.sub(replacement_content, content)
    else:
        # Append if section doesn't exist
        new_content = content + f"\n## Architecture\n\n![Architecture Diagram]({image_rel_path})\n"

    with open(readme_path, "w") as f:
        f.write(new_content)

    print(f"README.md updated with architecture image reference")


def main():
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bicep_path = os.path.join(repo_root, "app.bicep")
    output_path = os.path.join(repo_root, "docs", "architecture.png")
    readme_path = os.path.join(repo_root, "README.md")

    if not os.path.exists(bicep_path):
        print(f"Error: {bicep_path} not found")
        sys.exit(1)

    print(f"Parsing {bicep_path}...")
    resources, connections = parse_bicep(bicep_path)

    print(f"Found {len(resources)} resources and {len(connections)} connections")
    for r in resources:
        print(f"  - {r['display_name']} ({r['category']})")
    for c in connections:
        print(f"  - {c['from']} → {c['to']}")

    print(f"\nGenerating diagram...")
    generate_graph(resources, connections, output_path)

    print(f"Updating README...")
    update_readme(readme_path, "docs/architecture.png")

    print("Done!")


if __name__ == "__main__":
    main()
