import json
from typing import Dict, List

import streamlit as st

from socialsim4.core.simtree import SimTree
from socialsim4.core.simulator import Simulator
from socialsim4.scripts.run_basic_scenes import build_simple_chat_sim, make_clients


def _init_session():
    if "simtree" in st.session_state:
        return
    clients = make_clients()
    sim = build_simple_chat_sim()
    tree = SimTree.new(sim, clients)
    st.session_state["simtree"] = tree
    st.session_state["selected_node"] = int(tree.root)


def _dot_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _build_dot(tree: SimTree, selected: int) -> str:
    root = int(tree.root)
    frontier = set(tree.frontier(True))
    ids = sorted(list(tree.nodes.keys()))
    lines: List[str] = []
    lines.append("digraph G {")
    lines.append("  rankdir=TB;")
    lines.append(
        "  node [shape=circle, fontsize=10, fixedsize=true, width=0.5, height=0.5];"
    )

    for nid in ids:
        node = tree.nodes[nid]
        # Node label is only the id
        label = f"{nid}"
        color = "black"
        shape = "circle"
        if nid == root:
            color = "dodgerblue4"
        if nid in frontier:
            color = "seagreen"
        if nid == selected:
            color = "crimson"
        lines.append(
            f'  n{nid} [label="{_dot_escape(label)}", color={color}, shape={shape}];'
        )

    def edge_color(et: str) -> str:
        if et == "advance":
            return "black"
        if et == "agent_ctx":
            return "darkgreen"
        if et == "agent_plan":
            return "darkorange"
        if et == "agent_props":
            return "mediumpurple4"
        if et == "scene_state":
            return "saddlebrown"
        if et == "public_event":
            return "steelblue4"
        return "gray50"  # multi/others

    for pid in ids:
        for cid in tree.children.get(pid, []):
            et = tree.nodes[cid]["edge_type"]
            lines.append(f"  n{pid} -> n{cid} [color={edge_color(et)}];")

    lines.append("}")
    return "\n".join(lines)


def _node_selector(tree: SimTree) -> int:
    ids = sorted(list(tree.nodes.keys()))
    default = int(st.session_state.get("selected_node", int(tree.root)))
    if default not in ids:
        default = int(tree.root)
    label_ids = [str(i) for i in ids]
    choice = st.selectbox(
        "选择节点 (id)", label_ids, index=label_ids.index(str(default))
    )
    nid = int(choice)
    st.session_state["selected_node"] = nid
    return nid


def main():
    st.set_page_config(page_title="SimTree UI (Simple Chat)", layout="wide")
    _init_session()
    tree: SimTree = st.session_state["simtree"]

    left, right = st.columns([2, 1])

    with left:
        st.subheader("Simulation Tree")
        sel = int(st.session_state.get("selected_node", int(tree.root)))
        dot = _build_dot(tree, sel)
        st.graphviz_chart(dot, width="content")
        st.caption(
            f"Leaves: {tree.leaves()} | Frontier: {tree.frontier(True)} | Max depth: {tree.max_depth()}"
        )

        st.subheader("Summaries")
        items = tree.summaries()
        st.json(items)

    with right:
        st.subheader("操作")
        sel = _node_selector(tree)

        st.markdown("Advance")
        ac1, ac2 = st.columns([1, 1])
        if ac1.button("Advance selected 1 turn"):
            tree.advance(int(sel), turns=1)
        if ac2.button("Advance frontier 1 turn"):
            tree.advance_frontier(turns=1, only_max_depth=True)

        st.markdown("Branch: Public Broadcast")
        pb_text = st.text_input("text", value="(announcement)")
        if st.button("Apply public_broadcast"):
            tree.branch(int(sel), [{"op": "public_broadcast", "text": pb_text}])

        st.markdown("Branch: Agent Ctx Append")
        # Read agent names from this node's sim
        names = sorted(list(tree.nodes[sel]["sim"].agents.keys()))
        ag_name = st.selectbox("agent", names, index=0, key="ag_name")
        role = st.selectbox(
            "role", ["system", "user", "assistant"], index=1, key="ag_role"
        )
        msg = st.text_input("content", value="note")
        if st.button("Apply agent_ctx_append"):
            tree.branch(
                int(sel),
                [
                    {
                        "op": "agent_ctx_append",
                        "name": ag_name,
                        "role": role,
                        "content": msg,
                    }
                ],
            )

        st.markdown("Branch: Agent Props Patch")
        prop_key = st.text_input("key", value="flag")
        prop_val = st.text_input("value", value="1")
        if st.button("Apply agent_props_patch"):
            tree.branch(
                int(sel),
                [
                    {
                        "op": "agent_props_patch",
                        "name": ag_name,
                        "updates": {prop_key: prop_val},
                    }
                ],
            )

        st.markdown("Branch: Scene State Patch")
        st_key = st.text_input("state key", value="note")
        st_val = st.text_input("state value", value="hello")
        if st.button("Apply scene_state_patch"):
            tree.branch(
                int(sel), [{"op": "scene_state_patch", "updates": {st_key: st_val}}]
            )

        st.markdown("删除分支")
        if sel == tree.root:
            st.caption("根节点不可删除")
        else:
            if st.button("Delete subtree of selected"):
                tree.delete_subtree(int(sel))


if __name__ == "__main__":
    main()
