#!/usr/bin/env python3
"""
Parse app.bicep and generate an interactive architecture diagram (SVG) with
GitHub UI look-and-feel. Nodes are clickable and link to the exact line in
app.bicep on GitHub. Tooltips show the line number.

Outputs an SVG to docs/architecture.svg.
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
    """Parse a Bicep file and extract resources, connections, and line numbers."""
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

        # Calculate the 1-based line number where this resource is defined
        line_number = content[: match.start()].count("\n") + 1

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
            "line_number": line_number,
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
            conn = {"from": symbolic_name, "to": ref_name}
            if conn not in connections:
                connections.append(conn)

    return resources, connections


def get_github_file_url(repo_owner: str, repo_name: str, branch: str, file_path: str, line: int) -> str:
    """Build a GitHub URL that highlights a specific line."""
    return f"https://github.com/{repo_owner}/{repo_name}/blob/{branch}/{file_path}#L{line}"


def generate_graph(
    resources: list[dict],
    connections: list[dict],
    output_path: str,
    repo_owner: str,
    repo_name: str,
    branch: str,
    bicep_file: str,
):
    """Generate an interactive SVG architecture diagram with GitHub-inspired styling."""

    dot = graphviz.Digraph(
        "architecture",
        format="svg",
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
        label=f"Architecture · {bicep_file}",
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
        target="_blank",
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

        colors = category_colors.get(res["category"], category_colors["other"])

        # Build label
        lines = [f"{res['display_name']}"]
        if res["image"]:
            lines.append(f"{res['image']}")
        if res["port"]:
            lines.append(f":{res['port']}")

        label = "\\n".join(lines)

        # GitHub URL for this resource's line — clickable link
        url = get_github_file_url(repo_owner, repo_name, branch, bicep_file, res["line_number"])
        tooltip = f"{res['display_name']} — {bicep_file} line {res['line_number']}"

        dot.node(
            res["symbolic_name"],
            label=label,
            fillcolor=colors["fillcolor"],
            color=colors["color"],
            penwidth="2",
            URL=url,
            tooltip=tooltip,
            target="_blank",
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

    # Render (graphviz appends .svg automatically)
    output_base = output_path.removesuffix(".svg")
    dot.render(output_base, cleanup=True)
    print(f"Architecture diagram saved to {output_path}")


def update_readme(readme_path: str, image_rel_path: str):
    """Update the Architecture section in README.md with the generated SVG."""
    with open(readme_path, "r") as f:
        content = f.read()

    # Replace the Architecture section content
    # Match from "## Architecture" to the next "##" heading or end of file
    pattern = re.compile(
        r"(## Architecture\s*\n).*?(\n## |\Z)",
        re.DOTALL,
    )

    note = (
        "> *Auto-generated every 2 hours from `app.bicep`. "
        "Click a node to jump to its definition.*"
    )

    replacement_content = (
        f"\\1\n"
        f"![Architecture Diagram]({image_rel_path})\n\n"
        f"{note}\n"
        f"\n"
        f"\\2"
    )

    if pattern.search(content):
        new_content = pattern.sub(replacement_content, content)
    else:
        # Append if section doesn't exist
        new_content = content + (
            f"\n## Architecture\n\n"
            f"![Architecture Diagram]({image_rel_path})\n\n"
            f"{note}\n"
        )

    with open(readme_path, "w") as f:
        f.write(new_content)

    print(f"README.md updated with architecture SVG reference")


def main():
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bicep_file = "app.bicep"
    bicep_path = os.path.join(repo_root, bicep_file)
    output_path = os.path.join(repo_root, "docs", "architecture.svg")
    readme_path = os.path.join(repo_root, "README.md")

    # Repository info — used to build GitHub URLs for clickable nodes
    repo_owner = os.environ.get("REPO_OWNER", "nithyatsu")
    repo_name = os.environ.get("REPO_NAME", "prototype")
    branch = os.environ.get("REPO_BRANCH", "main")

    if not os.path.exists(bicep_path):
        print(f"Error: {bicep_path} not found")
        sys.exit(1)

    print(f"Parsing {bicep_path}...")
    resources, connections = parse_bicep(bicep_path)

    print(f"Found {len(resources)} resources and {len(connections)} connections")
    for r in resources:
        print(f"  - {r['display_name']} ({r['category']}) @ line {r['line_number']}")
    for c in connections:
        print(f"  - {c['from']} → {c['to']}")

    print(f"\nGenerating interactive SVG diagram...")
    generate_graph(resources, connections, output_path, repo_owner, repo_name, branch, bicep_file)

    print(f"Updating README...")
    update_readme(readme_path, "docs/architecture.svg")

    print("Done!")


if __name__ == "__main__":
    main()
