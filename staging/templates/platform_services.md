# Platform Services

The service layer of the platform. Every service here is a Go binary, built with the shared
Makefile and shipped as a distroless container image.

Service boundaries are contracts: a service owns its own schema and exposes it over gRPC.
Anything shared between services belongs in `platform/modules/`, not in a service.

## Rules

- One service, one database. No cross-service joins.
- Every gRPC change ships with a compatibility note.
- Integration tests run against the ephemeral stack, not a shared environment.
