# Inter-project protocol — mechanics

Companion to `INTERPROJECT_LAWS.md`, which states the rules. This file is how to carry them out, and what
tends to break.

## Entering another project

Address only its head, never a sub-node you suspect holds the answer. Inside that project the
request moves one hop at a time, and so does the answer: each node on the path may amend, answer, or
refuse it — it is a participant, not a relay. Name the subject in your own terms; do not name an
internal path and ask the head to skip to it, since that strips the intermediate node of its role and
any cross-cutting conflict only it could see ships silently.

Do not read another project's files yourself — its `CLAUDE.md`, its code, anything under its
directory — even to save a round trip or to double-check what you were told. That is verifying its
domain yourself, which Law 3 rules out regardless of how the file was reached (a direct path, a
glob, a shell `cat`). Asking its head is the only route in. What the registry says about a project
is theirs to have written; what you learn by asking its head is evidence you gathered correctly.

## The three request kinds

Name the kind explicitly, every time.

1. **Ruling** — is this true, is this yours to decide.
2. **Evidence** — give me your material; the holder decides what leaves its scope.
3. **Capability** — operate your own tool on my behalf; gated by what the tool does, never by who asks.

## The packet

The receiver has none of your context: not your conversation, not your reasoning. A packet that
works is self-contained and numbered:

1. Who is asking, and from where.
2. The request kind (above), and the consequence tier it falls under.
3. What is needed, inlined — paths, quotes, dates, claims — never "see the file at...".
4. The exact question, phrased so a yes/no/not-stated answer resolves it.
5. Done-criteria: what a complete answer looks like.
6. The return path: name the project the answer should reach, not a session, since sessions end and
   domains do not.

A worker who cannot answer says so — "not stated" or "not mine" is a valid, useful reply. A guess is
not.

## Known failure modes

**No open session at the target.** A project with no running session is not unreachable: run the
CLI non-interactively inside its directory, with the packet as the input and only read tools
pre-approved. This needs no prior session and returns an answer directly.

**Permission prompts stall unattended sessions.** Reading or acting outside your own project's
directory, or a shell command the permission system cannot statically verify, raises a prompt.
Nobody answers it unattended, and the session hangs silently. Pre-approve read-only tools at launch
for a ruling or evidence request, and avoid shell expansion; grant the tools the work actually needs
only for a capability request the owner itself must carry out.

**Safety-filter refusals are reported, never routed around.** A request refused by the receiving
side is itself an answer: record it and hand it up. Do not reword it to slip past the same filter,
and do not send the identical request to a different peer on the theory that it has no history of
refusing — that is laundering under Law 4.
