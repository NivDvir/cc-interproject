# Prior art — the vocabulary behind the inter-project laws

Naming a concept with its published term costs less than inventing a private one. This is where
the laws' terms come from.

**Bounded context.** A project's domain, sovereign over its own model of the world, with explicit
seams to its neighbors. From Evans, *Domain-Driven Design* (2003). This is what a project boundary
in Law 1 is: not a folder, a domain.

**Holon / holarchy.** A holon is a whole that is also a part: complete in itself, and simultaneously
a member of something larger. A holarchy is a set of holons interacting as peers rather than as a
strict chain of command. From Koestler (1969). This is the forest: independent projects, none
ranking above another, still forming one system together.

**Platform team.** A team (or role) that provides a shared capability as a service, reducing the
cognitive load on the teams it serves, without owning their outcomes or directing their work. From
Skelton and Pais, *Team Topologies* (2019). This is the dispatcher role: infrastructure and conduct,
not command.

**FIPA agent platform.** The physical and procedural infrastructure in which independent agents
operate, distinguished from any agent's own goals. The older, thinner sense of "platform," useful for
the goal-less half of the dispatcher role.

**Directory Facilitator.** FIPA's own term for a shared registry: a "yellow pages" service where
agents publish what they do and look up what others do. This is the project registry: read before
any cross-project work, and never written on another's behalf.

**Confused deputy.** A program tricked into misusing its own legitimate authority on someone else's
behalf, because it cannot distinguish "asked to" from "authorized to." From Hardy (1988). This is the
shape Law 4's anti-laundering rule exists to prevent: a request carries need, never permission.

**Garbage collection, as an analogy.** A stale record is like unreachable memory: nobody using it,
nobody collecting it either, because only the owner of the live state can tell it has gone stale. The
laws exist because no runtime performs this collection between projects on its own — each head
has to.
