# Meridian Logbook

Meridian Logbook is a small tool that keeps a running diary of shipping decisions for a fictional
cargo-routing team. It reads schedule exports, flags conflicting port windows, and writes a plain-text
summary that the team reviews each morning.

The project favors boring, auditable code over cleverness: no hidden state, no background jobs, and
every output file is safe to diff by hand.
