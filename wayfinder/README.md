# Wayfinder tracker (local-markdown)

This repo charts wayfinder efforts in markdown. The map, tickets, and research
findings live in this directory. fnack and fnack-plugins are treated as
read-only ground truth by every session that works this tracker.

## Map

`map.md` — the canonical low-res map: Destination, Notes, Decisions so far,
Not yet specified, Out of scope.

## Tickets

`tickets/NN-<slug>.md` — one file per decision ticket, numbered from `01`.
Each carries a `Type:` line (`research` | `prototype` | `grilling` | `task`)
and a `Status:` line (`open` | `claimed` | `resolved`). Blocking is written as
a `Blocked by: NN, NN` line in the ticket body.

A ticket is **claimed** by setting `Status: claimed` before work starts.
Resolving = append a `Resolution:` section, set `Status: resolved`, then move
a one-line gist into `map.md` → Decisions so far.

## Research findings

`research/<ticket-slug>.md` — the output of resolved research tickets; the
ticket links it.

## Frontier

Open tickets (with no unresolved `Blocked by:` deps) that aren't claimed.
