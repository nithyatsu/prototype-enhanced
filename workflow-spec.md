# Workflow Specification

> Fill in the sections below to describe what the CI/CD workflow should do.
> Then ask Copilot: "Implement a GitHub Actions workflow based on workflow-spec.md"

## Trigger

- **Schedule:** Every 2 hours (`cron: '0 */2 * * *'`)
- **Manual:** `workflow_dispatch`
  - Input: `detailed` (boolean, default `false`) — when `true`, graph nodes display image:tag metadata (see Section 7)

## Requirements

### 1. Spin up a Kind cluster

Create an ephemeral Kubernetes cluster using [Kind](https://kind.sigs.k8s.io/).

### 2. Install Radius

Install Radius into the Kind cluster using custom images:

```bash
rad install kubernetes \
    --set rp.image=ghcr.io/nithyatsu/applications-rp,rp.tag=latest \
    --set dynamicrp.image=ghcr.io/nithyatsu/dynamic-rp,dynamicrp.tag=latest \
    --set controller.image=ghcr.io/nithyatsu/controller,controller.tag=latest \
    --set ucp.image=ghcr.io/nithyatsu/ucpd,ucp.tag=latest \
    --set bicep.image=ghcr.io/nithyatsu/bicep,bicep.tag=latest
```

### 3. Verify Radius is ready

Run `rad group create test` and confirm it succeeds. This validates that all Radius pods are healthy and the control plane is operational.

### 4. Generate the application graph

Run `rad app graph <fully-qualified-path-to-app.bicep>`.

- The command requires an **absolute file path** (e.g., `${{ github.workspace }}/app.bicep`).
- The command outputs a structured representation of the application's resources and their connections.
- The command gets updated all the time. Try it out, update the workflow to work with the latest behavior. 

### 5. Build a visual graph from the output

Parse the output from step 4 and construct a renderable graph (e.g., using Graphviz or Mermaid). Extract:

- **Nodes** — each resource (name, type, source file, line number)
- **Edges** — connections between resources

### 6. Render the graph and update the README

Generate a **Mermaid diagram** and embed it directly in the `README.md` Architecture section as a fenced `mermaid` code block. GitHub renders Mermaid natively, so the diagram is interactive right in the README — no separate image files or HTML pages needed.

#### Format

Use a Mermaid `graph LR` with:
- `%%{ init }%%` directive for theme configuration
- `classDef` for node styling
- `click` directives for making each node a hyperlink with tooltip

#### Visual style

| Property        | Value                                          |
|-----------------|-------------------------------------------------|
| Theme           | `base` (light)                                 |
| Background      | White (`#ffffff`)                               |
| Font color      | Dark (`#1f2328`)                               |
| Node shape      | Rounded-corner rectangles (`rx:6, ry:6`)        |
| Container border| Green (`#2da44e`)                               |
| Datastore border| Amber (`#d4a72c`)                               |
| Node fill       | White (`#ffffff`)                               |
| Edge color      | Green (`#2da44e`)                               |
| Font            | `-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif` |

#### Interactivity (via Mermaid `click` directive)

| Feature         | Behavior                                        |
|-----------------|-------------------------------------------------|
| **Tooltip**     | Hovering a node shows: `"<name> — app.bicep line <N>"` |
| **Click**       | Clicking a node opens `https://github.com/<owner>/<repo>/blob/<branch>/app.bicep#L<N>` with the line highlighted |

#### README update

Replace the Architecture section's Mermaid code block with the newly generated one. The diagram should be the only content between the `## Architecture` heading and the next `##` heading.

### 7. Detailed mode — Image dependency graph

The workflow accepts a `detailed` input variable (boolean, default `false` for the main workflow).

When `detailed` is `true`, graph nodes display **extended metadata** beyond the resource name:

#### Node label format (detailed mode)

Each container node renders as a multi-line label:

```
<resource-name>
<image>:<tag>
```

For example:
```
frontend
ghcr.io/image-registry/magpie:latest
```

#### Image and tag resolution

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | Explicit `image` property in `app.bicep` (including via parameter default values) | `image: 'ghcr.io/image-registry/magpie:latest'` → image = `ghcr.io/image-registry/magpie`, tag = `latest` |
| 2 (fallback) | Derive from resource name | resource named `frontend` → image = `frontend`, tag = `latest` |

- If the `image` property contains a colon, split on the **last** colon to separate image and tag.
- If the `image` property has no colon, the tag defaults to `latest`.
- If no `image` property is found (e.g., non-container resources like datastores), show only the resource name (no image/tag line).

#### Visual style (detailed mode)

- Node labels use `<br/>` for line breaks in Mermaid.
- The image:tag line is rendered in a smaller or secondary style (lighter color `#656d76`) to distinguish it from the resource name.
- All other styling (borders, colors, edges) remains the same as the standard graph.

#### Image dependency graph

In detailed mode, the resulting diagram effectively becomes an **image dependency graph** — it shows which container images depend on (connect to) which other container images. This is useful for understanding the supply chain of container images in the application.

### 8. Commit and push

Auto-commit changes to `docs/` and `README.md` only if the graph has changed.

---

## User Story 4 — PR Graph Diff (P2)

**Goal:** Show a visual diff of the app graph in PR comments so reviewers can see architectural impact without deploying.

**Depends on:** User Stories 1–3 being stable.

### Operational model

The GitHub Action reads committed `.radius/app-graph.json` files from git history — it does **not** generate graphs on-demand. No Bicep/Radius tooling is needed, keeping the Action lightweight and fast.

### Trigger events

| Event | Behavior |
|-------|----------|
| `pull_request` (every push) | Posts or updates a diff comment on the PR |
| `push` to `main` | Updates the baseline for historical comparison |

The comment is posted on **every push** to the PR, not just the first one. If no Bicep/graph changes exist, the comment says "No app graph changes detected."

### Detailed mode in PRs

The PR workflow runs in **detailed mode by default** (`detailed: true`). This means all graph nodes in the PR comment (side-by-side graphs and the consolidated diff graph) display the extended image:tag metadata described in Section 7 of the main workflow spec. This gives reviewers immediate visibility into which container images changed and how the image dependency chain is affected.

### Clickable nodes in the consolidated diff graph

In the PR comment's consolidated diff graph, **every node must be clickable**. Clicking a node opens the PR's **Files changed** view (`/files`) with the browser scrolled to the resource definition corresponding to that node.

#### Link format

```
https://github.com/<owner>/<repo>/pull/<pr_number>/files#diff-<file_hash>R<line_number>
```

Where:
- `<file_hash>` is the SHA-256 hash of the file path (e.g., `app.bicep`) — this matches GitHub's anchor format for PR diff files.
- `R<line_number>` is the right-side line number in the diff corresponding to the resource definition's start line in the PR head.

#### Mermaid `click` directive

```mermaid
click frontend href "https://github.com/<owner>/<repo>/pull/<pr>/files#diff-<hash>R<line>" "frontend — app.bicep line <N>" _blank
```

Each node in the diff graph (added, removed, modified, or unchanged) should have a `click` directive. For removed resources, link to the base side of the diff (`L<line>` instead of `R<line>`).

### Monorepo support

Auto-detect all `**/.radius/app-graph.json` files. Each graph is diffed independently with separate comment sections per application.

### PR comment format

The comment includes:

1. **Side-by-side Mermaid graphs** — `main` graph on the left, PR graph on the right, for visual comparison. Both rendered in **detailed mode** (showing image:tag on each container node).
2. **Diff graph** — a single consolidated Mermaid graph using color-coded nodes:
   - 🟢 Green border — added resources
   - 🟡 Amber border — modified resources
   - 🔴 Red border — removed resources
   - Gray border — unchanged resources
   - All container nodes display image:tag metadata (detailed mode).
3. **Clickable nodes in diff graph** — every node in the consolidated diff graph is clickable. Clicking opens the PR's **Files changed** page (`/files`) scrolled to the resource definition. Added/modified/unchanged resources link to the right-side diff line (`R<line>`); removed resources link to the left-side diff line (`L<line>`).
4. **Resources & connections table** — lists added/removed/modified resources and connections.
5. **Footer** — "Powered by [Radius](https://radapp.io/)"

### Acceptance criteria

1. PR includes changes to `.radius/app-graph.json` → Action posts a comment with side-by-side graphs + diff graph.
2. PR has no Bicep or graph changes → Comment says "No app graph changes detected."
3. PR adds a new connection → Diff graph shows the new edge; new resource node is green.
4. PR removes a resource → Diff graph shows the removed node in red (dashed border).
5. PR modifies a resource → Diff graph shows the modified node in amber.
6. PR comment already exists from a previous push → Existing comment is updated, not duplicated.
7. Clicking any node in the consolidated diff graph opens the PR's Files changed page with the resource definition in focus (right-side line for added/modified/unchanged; left-side line for removed).
8. Bicep files changed but `.radius/app-graph.json` was not updated → CI validation fails with instructions.
9. Monorepo with multiple apps → Unified comment with separate sections per application.
10. Comment footer says "Powered by [Radius](https://radapp.io/)".
11. PR workflow runs in detailed mode by default — all container nodes in side-by-side and diff graphs show image:tag metadata.
12. Main workflow with `detailed: true` input → README diagram shows image:tag on each container node.
13. Main workflow with `detailed: false` (default) → README diagram shows only resource names (original behavior).