# Platform

The internal platform: shared infrastructure, deployment tooling, and the services that
every product team depends on. Terraform for infrastructure, Helm charts per service.

Each service under `services/` is its own project with its own CLAUDE.md. This file covers
the platform as a whole, not any one service.

## Rules

- A service is deployed by its own chart, never by a hand-edited manifest.
- Shared Terraform modules live in `modules/` and are versioned by tag.
- No service talks to another service's database directly.
