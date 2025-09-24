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


def _tree_lines(tree: SimTree) -> List[str]:
    lines: List[str] = []

    def walk(nid: int, prefix: str, is_last: bool):
        node = tree.nodes[nid]
        tag = "└─" if is_last else "├─"
        label = f"{tag} [#{nid}] depth={node['depth']} turns={node['sim'].turns} edge={node['edge_type']}"
        if node["ops"]:
            label += f" ops={json.dumps(node['ops'])}"
        lines.append(prefix + label)
        ch = tree.children.get(nid, [])
        for i, cid in enumerate(ch):
            last = i == len(ch) - 1
            walk(cid, prefix + ("   " if is_last else "│  "), last)

    root = int(tree.root)
    lines.append(f"[# {root}] depth=0 turns={tree.nodes[root]['sim'].turns} edge=root")
    for i, cid in enumerate(tree.children.get(root, [])):
        walk(cid, "", i == len(tree.children[root]) - 1)
    return lines


def _node_selector(tree: SimTree) -> int:
    ids = sorted(list(tree.nodes.keys()))
    default = int(st.session_state.get("selected_node", int(tree.root)))
    if default not in ids:
        default = int(tree.root)
    label_ids = [str(i) for i in ids]
    choice = st.selectbox("选择节点 (id)", label_ids, index=label_ids.index(str(default)))
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
        st.text("\n".join(_tree_lines(tree)))
        st.caption(f"Leaves: {tree.leaves()} | Frontier: {tree.frontier(True)} | Max depth: {tree.max_depth()}")

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
        role = st.selectbox("role", ["system", "user", "assistant"], index=1, key="ag_role")
        msg = st.text_input("content", value="note")
        if st.button("Apply agent_ctx_append"):
            tree.branch(int(sel), [{"op": "agent_ctx_append", "name": ag_name, "role": role, "content": msg}])

        st.markdown("Branch: Agent Props Patch")
        prop_key = st.text_input("key", value="flag")
        prop_val = st.text_input("value", value="1")
        if st.button("Apply agent_props_patch"):
            tree.branch(int(sel), [{"op": "agent_props_patch", "name": ag_name, "updates": {prop_key: prop_val}}])

        st.markdown("Branch: Scene State Patch")
        st_key = st.text_input("state key", value="note")
        st_val = st.text_input("state value", value="hello")
        if st.button("Apply scene_state_patch"):
            tree.branch(int(sel), [{"op": "scene_state_patch", "updates": {st_key: st_val}}])

        st.markdown("删除分支")
        if sel == tree.root:
            st.caption("根节点不可删除")
        else:
            if st.button("Delete subtree of selected"):
                tree.delete_subtree(int(sel))


if __name__ == "__main__":
    main()

