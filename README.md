# Prototype App

A simple **Frontend → Backend → Database** application built with [Radius](https://radapp.io/) and Bicep.

## Architecture


> *Auto-generated from `app.bicep` — click any node to jump to its definition in the source.*

```mermaid
%%{ init: { 'theme': 'dark', 'themeVariables': { 'primaryColor': '#161b22', 'primaryTextColor': '#e6edf3', 'primaryBorderColor': '#30363d', 'lineColor': '#58a6ff', 'secondaryColor': '#21262d', 'tertiaryColor': '#0d1117', 'fontSize': '14px', 'fontFamily': '-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif' } } }%%
graph LR
    classDef container fill:#161b22,stroke:#58a6ff,stroke-width:2px,color:#e6edf3,rx:12,ry:12
    classDef datastore fill:#161b22,stroke:#f78166,stroke-width:2px,color:#e6edf3,rx:12,ry:12
    classDef other fill:#161b22,stroke:#8b949e,stroke-width:2px,color:#e6edf3,rx:12,ry:12
    frontend(["<b>frontend</b><br/><i>nginx:alpine</i><br/>:80"]):::container
    backend(["<b>backend</b><br/><i>node:18-alpine</i><br/>:3000"]):::container
    database(["<b>database</b>"]):::datastore
    frontend ==> backend
    backend ==> database
    click frontend "https://github.com/nithyatsu/prototype/blob/main/app.bicep#L18" "frontend — app.bicep line 18"
    click backend "https://github.com/nithyatsu/prototype/blob/main/app.bicep#L45" "backend — app.bicep line 45"
    click database "https://github.com/nithyatsu/prototype/blob/main/app.bicep#L75" "database — app.bicep line 75"
    linkStyle 0 stroke:#58a6ff,stroke-width:2px
    linkStyle 1 stroke:#58a6ff,stroke-width:2px
```


## Prerequisites

- [Radius CLI](https://docs.radapp.io/getting-started/) installed
- A Radius environment configured (e.g., local Kubernetes)

## Deploy

```bash
rad deploy app.bicep
```

## Project Structure

```
.
├── app.bicep            # Radius application definition
├── workflow-spec.md     # Workflow specification (CI/CD requirements)
└── README.md            # This file
```

## Workflow

See [workflow-spec.md](workflow-spec.md) to define CI/CD workflow requirements. Once authored, a GitHub Actions (or other CI/CD) workflow can be generated from it.
