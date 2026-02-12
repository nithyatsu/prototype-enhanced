# Workflow Specification

> Fill in the sections below to describe what the CI/CD workflow should do.
> Then ask Copilot: "Implement a GitHub Actions workflow based on workflow-spec.md"

## Trigger

The workflow should run every 2 hours. I should also be able to run it manually. 

## Requirements

1. When the workflow runs, it should generate a graph by parsing the app.bicep from the main branch using bicep compiler. 
2. It should make an image out of this and post it to the README.md Architecture section. Use github UI kind of look and feel for the graph. 
3. Each node should refer to the line number in app.bicep where the resource is defined as toop tip text. And When I click the node it should open the app.bicep with the line highlighted. 

