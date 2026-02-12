# Workflow Specification

> Fill in the sections below to describe what the CI/CD workflow should do.
> Then ask Copilot: "Implement a GitHub Actions workflow based on workflow-spec.md"

## Trigger

The workflow should run every 2 hours. I should also be able to run it manually. 


- 

## Steps

When the workflow runs, it should generate a graph by parsing the app.bicep from the main branch using bicep compiler. 
It should make an image out of this and post it to the README.md Architecture section. Use github UI kind of look and feel for the graph.

