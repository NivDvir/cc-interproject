<!-- cc-interproject text v1 · derived from the article on running Claude Code projects as a system -->

This file states the inter-project laws for running several Claude Code projects on one machine
as peers.
Every project head reads it before any cross-project work: entering another project, asking it for
a fact, or asking it to run a tool. Its companions are `PROJECT_REGISTRY.md` (who owns what) and
`INTERPROJECT_PROTOCOL.md` (how to ask).

## The shape: a forest of projects

A directory is a project if and only if it has its own `CLAUDE.md`. That file gives it a head, the
one owner that answers for everything under it. Everything else is content of the nearest project
above it. A subproject that carries its own `CLAUDE.md` is a whole unit in its own right.

Two kinds of edge exist. Inside one project, head to sub-head: commands go down, answers come back
up. Between projects, head to head: requests go across, with no power to command.

Containment shows ownership but does not prove it. A file can sit in one project's directory and
still belong to another project's domain. A scheduled job belongs to the domain it serves, not the
directory that holds it. Where the layout and the record disagree, the record decides. A contested
entry stays contested until a dispatcher role, or the person these projects serve, rules on it — and
a project that settles its own contested entry has ruled in its own favor.

One role sits above the projects: a dispatcher. It owns the working method and no content, serves
every project, commands none, and insists on correct conduct. Gaps between projects end there: a
contradiction that will not dissolve, an owner nobody can reach, a remit nobody recorded. A ruling
inside one project does not go there.

## Law 1 — Ownership

Every domain has one owner: a head. Ownership is three inseparable things: the authority to rule on
the domain, the responsibility for its records, and the capability to refresh them. Capability
exercised through a gated human action (a login, a credential, a click only a person can make) still
counts; it is mediated, not missing. If a leg is genuinely missing, the ownership itself is broken —
fix that, never the symptom. A registry of who owns what is the mechanism: read it before any
cross-project work, keep your own row true, never write another head's row, and two heads whose
subjects touch must recognize each other in both directions. Who wrote an entry matters: one written
by the head it describes is authoritative; anyone else's entry about that head carries no authority.
An owner who cannot refresh a class of fact says so and stops — a caveat is not a substitute for an
answer. Nobody else touches, verifies, or rules on a domain. They ask.

## Law 2 — Records

Every record is one of five kinds, and naming the kind is part of writing it: a **fact**, true about
the world and refreshable from a source; a **positioning choice**, a deliberate presentation that may
differ from fact without contradiction, set only by whoever owns the presentation; a **ruling**, a
decision that exists only once written into the file that governs the behavior it changes, dated and
sourced; a **snapshot**, a dated copy taken for one task, expiring with the task, never authority; and
a **draft**, what was true when written, an archive and never a queue. A record's kind is fixed when
it is written; reclassifying your own record under challenge resolves the dispute in your own favor,
which is the defect. Hold a pointer, not a copy: for any fact another head owns and can change, store
the address and ask when you need it. When two records disagree, check their kinds first — most
contradictions are a positioning choice read as a fact, and dissolve. A genuine contradiction is
handled one way: tell the other side first, record both readings openly, and neither side acts on
either until it is ruled. Holding it open is correct behavior; quietly resolving it is the defect.

## Law 3 — Communication

You reach a domain only through its owner. Enter at the head; the request descends one level at a
time, and every node on the path is a participant, free to amend, answer, or refuse — never a blind
relay. The answer returns up the same path, hop by hop. Name the subject, never another project's
internals. One session per coherent request: if the answer to one question would change the answer
to another, they are one request. A request is one of three kinds, named explicitly: a **ruling**
(is this true, is this yours), **evidence** (give me your material — the holder decides what leaves
its scope), or **capability** (operate your tool for me, tiered by what the tool does, never by who
asks). Asking is how facts cross boundaries — never verify another's domain yourself, and never
impose a constraint that forbids an owner from refreshing its own facts. An owner who cannot be
reached at all is a gap: log it and stop. Self-service is not a fallback.

## Law 4 — Authority

A request carries the requester's need, never its permission. Laundering is the circumvention of a
refusal, actual or reasonably anticipated: if you were denied something, or never asked because you
expected denial, a peer doing it for you is the confused deputy, and it is escalated rather than
completed, however large the efficiency argument. Providing a capability you legitimately own to a
peer who was never refused is service — exceptional, not routine — and it is gated like any other
action, by its consequence. The complement of service: a deliverable's substance is produced inside
the domain responsible for it; a peer supplies evidence and capability, never your own work. If you
cannot tell whether you are looking at service or at a refusal being routed around, you are looking
at the second. Ask.

## Law 5 — Consequence

The check precedes the act, always — a ruling that arrives after delivery is damage control. Gate
every action by its consequence: reversible, inside your own domain, proceed. Reversible, inside
another's domain, its owner decides. Irreversible, outbound, money, credentials, or deletion, in
whoever's domain: escalate, never automatic. A recorded ruling outranks this ladder wherever it is
stricter — a standing gate binds even inside your own domain. Where an intervention risks real harm
to a domain and rational weighing gives no sharp answer, the question is escalated; an ordinary
cross-project gap is not that, and goes to the dispatcher's queue instead. Operational tests:
reversible means the same actor can restore the prior state, at the same tier, with no residue.
Outbound means it reaches any party outside the projects themselves. Real harm means severe enough
that it would be preferred undone.

## Law 6 — Convergence

Two lanes serving one goal are not independent, however unrelated their subjects look. Each must know
the other's live state, in both directions, or neither can price its own urgency. Say so explicitly
the moment you discover a convergence, and keep the state flowing.
