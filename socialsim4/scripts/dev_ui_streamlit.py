import json
import os
from pathlib import Path
from typing import Dict, List

import streamlit as st

from socialsim4.core.event import StatusEvent
from socialsim4.core.simulator import Simulator
from socialsim4.scripts.run_basic_scenes import (
    build_council_sim,
    build_landlord_sim,
    build_simple_chat_sim,
    build_village_sim,
    build_werewolf_sim,
)


# Snapshot helpers available to _init_session and UI
def build_snapshot(
    sim: Simulator, bus: "DevEventBus", names: List[str], offsets: Dict
) -> tuple[Dict, Dict]:
    # Do NOT call sim.emit_remaining_events() here when invoked from
    # the log handler to avoid recursion. Snapshots now capture the
    # state incrementally per published event.
    # Deep copy helpers via JSON encoding to freeze state
    def _dc(x):
        return json.loads(json.dumps(x))

    # Compute deltas based on offsets.
    # Offsets schema (strict):
    #   offsets = {
    #     "events": int,
    #     "mem": { name: {"count": int, "last_len": int}, ... }
    #   }
    new_mem_offsets: Dict[str, Dict[str, int]] = {}
    agents = []
    for nm in names:
        ag = sim.agents[nm]
        mem_all = ag.short_memory.get_all()
        prev = offsets["mem"].get(nm, {"count": 0, "last_len": 0})
        cnt = len(mem_all)

        delta_msgs = []
        if cnt == 0:
            new_last_len = 0
        elif cnt > int(prev.get("count", 0)):
            # New entries appended; take them whole
            delta_msgs = mem_all[int(prev.get("count", 0)) :]
            new_last_len = len(mem_all[-1]["content"])
        else:
            # Same count: if last message grew (merge-on-same-role), emit the appended tail as a logical delta
            last_content = mem_all[-1]["content"]
            prev_last_len = int(prev.get("last_len", 0))
            if len(last_content) > prev_last_len:
                appended = last_content[prev_last_len:]
                delta_msgs = [
                    {"role": mem_all[-1]["role"], "content": appended}
                ]
            new_last_len = len(last_content)

        new_mem_offsets[nm] = {"count": cnt, "last_len": new_last_len}
        agents.append(
            {
                "name": nm,
                "role": ag.properties.get("role"),
                "plan_state": _dc(ag.plan_state),
                "context_delta": _dc(delta_msgs),
            }
        )
    last_event_idx = offsets["events"]
    events_delta = _dc(bus.history[last_event_idx:])
    new_offsets = {"events": len(bus.history), "mem": new_mem_offsets}
    return (
        {
            "turns": sim.turns,
            "names": list(names),
            "events_delta": events_delta,
            "agents": agents,
        },
        new_offsets,
    )


def build_static_html_from_template(snapshot: Dict) -> str:
    tpl_path = Path(__file__).parent / "static" / "snapshot_viewer.html"
    tpl = tpl_path.read_text(encoding="utf-8")
    return tpl.replace("__DATA__", json.dumps(snapshot))


class DevEventBus:
    def __init__(self, max_history: int = 5000):
        self.history: List[dict] = []
        self.max_history = max_history

    def publish(self, event_type: str, data: dict):
        self.history.append({"type": event_type, "data": data})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]


def _do_steps(n: int):
    sim: Simulator = st.session_state["sim"]
    for _ in range(n):
        if sim.scene.is_complete():
            break
        sim.run(max_turns=1)
        # Snapshotting is now handled by the log handler per publish


def run_dev_ui(sim: Simulator):
    st.set_page_config(page_title="SocialSim4 Dev UI", layout="wide")
    if "bus" not in st.session_state:
        st.session_state["bus"] = DevEventBus()
    bus = st.session_state["bus"]
    names = list(sim.agents.keys())
    if "sim" not in st.session_state:
        st.session_state["sim"] = sim
        st.session_state["names"] = names
        st.session_state["timeline"] = []
        st.session_state["offsets"] = {
            "events": 0,
            "mem": {nm: {"count": 0, "last_len": 0} for nm in names},
        }
        st.session_state["selected_agent"] = names[0]

        # Wire a wrapper log handler: publish to bus and append a snapshot
        def log_and_snapshot(event_type: str, data: dict):
            bus.publish(event_type, data)
            snap, new_off = build_snapshot(
                sim, bus, st.session_state["names"], st.session_state["offsets"]
            )
            st.session_state["timeline"].append(snap)
            st.session_state["offsets"] = new_off

        # Attach after session state is initialized to avoid None references
        sim.log_event = log_and_snapshot
        for a in sim.agents.values():
            a.log_event = log_and_snapshot

        # Initial snapshot (before any further events)
        snap, new_off = build_snapshot(sim, bus, names, st.session_state["offsets"])
        st.session_state["timeline"].append(snap)
        st.session_state["offsets"] = new_off
        sim.emit_remaining_events()

    sim = st.session_state["sim"]
    names = st.session_state["names"]

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Events & Actions")
        b1, b10, b50 = st.columns([1, 1, 1])
        if b1.button("Run 1 turn"):
            _do_steps(1)
        if b10.button("Run 10 turns"):
            _do_steps(10)
        if b50.button("Run 50 turns"):
            _do_steps(50)

        frames: List[Dict] = st.session_state.get("timeline", [])
        if not frames:
            snap, new_off = build_snapshot(
                sim,
                bus,
                names,
                st.session_state.get(
                    "offsets",
                    {
                        "events": 0,
                        "mem": {nm: {"count": 0, "last_len": 0} for nm in names},
                    },
                ),
            )
            frames = [snap]
            st.session_state["timeline"] = frames
            st.session_state["offsets"] = new_off
        max_idx = max(0, len(frames) - 1)
        default_idx = st.session_state.get("frame_idx", max_idx)
        if default_idx > max_idx:
            default_idx = max_idx
        if max_idx > 0:
            st.session_state["frame_idx"] = st.slider(
                "Frame", 0, max_idx, value=default_idx, key="frame_slider"
            )
        else:
            st.session_state["frame_idx"] = 0
            st.caption("Frame: 0")
        idx = st.session_state["frame_idx"]
        snap = frames[idx]

        feed_lines: List[str] = []
        items = []
        for i in range(idx + 1):
            items.extend(frames[i].get("events_delta", []))
        for item in items:
            t = item.get("type")
            d = item.get("data", {})
            if t == "system_broadcast":
                if d.get("sender") is None or d.get("sender") == "":
                    feed_lines.append(f"[Public Event] {d.get('text', '')}")
            elif t == "action_end":
                action_data = d.get("action", {})
                if action_data.get("action") != "yield":
                    feed_lines.append(
                        f"[{action_data.get('action')}] {d.get('summary')}"
                    )
        st.code("\n".join(feed_lines) if feed_lines else "(no events yet)")

        bundle = {"timeline": frames}
        html = build_static_html_from_template(bundle)
        st.download_button(
            label="Download static snapshot (HTML)",
            data=html,
            file_name="socialsim4_snapshot.html",
            mime="text/html",
        )

    with right:
        st.subheader("Agents")
        if "selected_agent" not in st.session_state:
            st.session_state["selected_agent"] = names[0]
        st.radio(
            "Select agent",
            names,
            key="selected_agent",
            label_visibility="collapsed",
        )
        sel_name = st.session_state["selected_agent"]
        snap_agents = {a["name"]: a for a in snap.get("agents", [])}
        a = snap_agents.get(sel_name)
        st.caption(f"Role: {a.get('role')}")
        st.markdown("Plan State")
        st.json(a.get("plan_state", {}))
        st.markdown("Full Context")
        full_msgs: List[Dict] = []
        for i in range(idx + 1):
            ags = {x["name"]: x for x in frames[i].get("agents", [])}
            if sel_name in ags:
                full_msgs.extend(ags[sel_name].get("context_delta", []))
        if full_msgs:
            for m in full_msgs:
                st.markdown(f"- [{m['role']}]")
                st.text(m["content"])  # preserve newlines
        else:
            st.caption("(empty)")

    return


def main():
    sim = build_landlord_sim()
    run_dev_ui(sim)


if __name__ == "__main__":
    main()
