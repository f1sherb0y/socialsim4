# SocialSim4 Agent Guide

This document summarizes the coding requirements, conventions, and the project’s core philosophy and mechanics, to help future contributors (and coding agents) work consistently.

## Philosophy

- Prototype-first: prioritize clarity and iteration speed over robustness, performance, or backwards compatibility.
- Agents live in an isolated world: they never “know” the simulator exists. All decisions flow from their own context and scene feedback.
- Scenes define environment, constraints, and action semantics. Agents emit actions; scenes parse and execute them; simulator orchestrates turns.
- Ordering decides who acts next. Different policies lead to different social dynamics.

## Non‑Negotiable Coding Rules (Prototype Stage)

- Eliminate defensive coding: no try/except, no isinstance, no hasattr, no dynamic fallback branches.
- Use strict input formats and fail fast. Let exceptions surface.
- Be aggressive in refactors. Remove dead/old code freely. No backward compatibility concerns.
- Keep implementations minimal and direct; no generalized abstractions unless they’re used now.
- Avoid “smart” runtime checks; rely on the exact data shape we produce elsewhere in the codebase.

## Ordering (Scheduling) Model

- Interface (fixed, minimal):
  - `__init__(sim)` – attach the simulator instance.
  - `iter()` – an infinite generator yielding the next agent name to act.
  - `post_turn(agent_name)` – hook after each agent completes a turn.
  - `on_event(sim, event_type, data)` – optional observer (no request channel from agents).
- No concept of “rounds.” The simulator runs for a maximum number of turns; each pick is one turn.
- Built‑in strategies:
  - Sequential – infinite round‑robin over a fixed snapshot.
  - Random – independent random choice every pick.
  - Asynchronous – same as sequential (placeholder).
  - Controlled – `next_fn(sim) -> name | None`, else fallback to sequential.
  - LLMModerated – queue‑based, driven by a designated Moderator agent (see below).

### LLMModeratedOrdering (Moderator‑driven queue)

- Init resolves and stores:
  - `moderator`: Agent object (fixed type).
  - `names`: list[str] – the candidate names to schedule; frozen at init.
- Maintains a private `_queue` of upcoming names.
- Behavior:
  - If `_queue` is empty (in `iter()`, `post_turn()`, or `on_event()`), nudge the moderator once to emit exactly one action:
    `<Action name="schedule_order"><order>Alice, Bob, Charlie</order></Action>`.
  - This single interaction must return that action; anything else is an error.
  - The action handler pushes the parsed comma‑separated names into `_queue` (no filtering/validation here).
  - `iter()` yields from `_queue` in order; if nothing was produced, fall back to `names` once.
- No “turn_request” concept. Agents never ask the scheduler to speak again.

## Simulator Loop

- Construct with agents, scene, clients, and an ordering factory: `ordering(sim) -> Ordering`.
- Infinite pick loop (bounded by `max_turns`):
  1) Pull next agent name from `ordering.iter()`.
  2) Optional private status prompt via `scene.get_agent_status_prompt(agent)`.
  3) If `scene.should_skip_turn(agent, sim)`: call `scene.post_turn`, then `ordering.post_turn` and continue.
  4) Intra‑turn: allow up to `max_steps_per_turn` calls to `agent.process(...)`. If an action is `yield`, end the turn.
  5) After the turn: `scene.post_turn`, `ordering.post_turn`.
- Events are emitted via `sim.emit_event(type, data)` and forwarded to ordering and any external logger.

## Scenes

- Responsibilities:
  - `deliver_message(event, sender, simulator)` – deliver chat/announcements; sender also records their own speech.
  - `parse_and_handle_action(action_data, agent, simulator)` – find and run the matching Action handler.
  - `post_turn(agent, simulator)` – timekeeping and per‑turn environment updates.
  - `should_skip_turn(agent, simulator)` – return True to skip.
  - `is_complete()` – signal simulation completion.
- No round‑based logic. If scene needs a “phase,” keep it as state on `scene.state` and update in `post_turn` or via actions.

## Agents

- `process(clients, initiative, scene)` does exactly one LLM call.
- Message format to LLM is strict: each message is `{role: "system|user|assistant", content: str}`.
- Output parsing is strict:
  - One Thoughts/Plan/Action block, with a single `<Action ...>` XML element.
  - `_parse_actions` expects a single Action XML; no fallback scanning heuristics.
  - Plan Update: parse JSON embedded in the `--- Plan Update ---` block if present; otherwise ignore.
- Plan updates:
  - `replace`: replace entire `plan_state`.
  - `patch`: assign fields directly (no deep merges or list concatenation).
- Memory:
  - `ShortTermMemory` stores `[ {role, content}, ... ]`.
  - `searilize("default")` returns `[ {role, content}, ... ]`.

## LLM Client (openai | gemini | mock)

- Strict mapping; inputs are `[ {role, content}, ... ]` only.
- openai: pass messages to Chat Completions API as is.
- gemini: convert each message to a single part with `{text: content}`.
- mock: deterministic stub that returns one valid Action per call.
- No images/parts/mixed content handling.

## Actions

- Keep each Action minimal and strict:
  - Required fields are accessed directly by key (e.g., `action_data["x"]`).
  - No multiple formats or fallback branches.
  - Fail fast: missing fields raise exceptions.
- Selected conventions:
  - `schedule_order` (moderator only): `<order>` is a comma‑separated string of names.
  - `move_to_location`: either `<location>` or coordinates `<x>`, `<y>` (the code paths may be scene‑specific).
  - Web actions: required fields only; network errors propagate.

## Do / Don’t

- Do:
  - Prefer simple, explicit code paths.
  - Remove unused code aggressively.
  - Keep interfaces minimal and concrete.
- Don’t:
  - Add error handling or fallbacks; avoid try/except.
  - Use isinstance/hasattr for runtime discovery.
  - Accept multiple input formats.

## Example: Werewolf Moderator Scheduling

- Moderator has action space: `open_voting`, `close_voting`, `schedule_order`.
- Ordering: `LLMModeratedOrdering(sim, moderator_agent, names=[...])`.
- When `_queue` is empty:
  - Simulator privately nudges Moderator to schedule the next few agents.
  - Moderator must emit exactly one `<Action name="schedule_order"><order>Elena, Bram, Pia</order></Action>`.
  - Ordering enqueues these names and resumes yielding them in order.

## Notes

- API layer still wraps some exceptions for HTTP semantics; core is strict.
- If expanding features later, maintain the strict style unless explicitly decided otherwise.

