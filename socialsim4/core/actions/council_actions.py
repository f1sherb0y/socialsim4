from socialsim4.core.action import Action
from socialsim4.core.event import MessageEvent, PublicEvent


class StartVotingAction(Action):
    NAME = "start_voting"
    DESC = "Host should use start_voting action to initiate the voting round."
    INSTRUCTION = """- To start voting:
<Action name=\"start_voting\" />
"""

    def handle(self, action_data, agent, simulator, scene):
        if not scene.state.get("voting_started", False):
            scene.state["voting_started"] = True
            event = PublicEvent(
                "The Host has initiated the voting round. Please cast your votes now."
            )
            simulator.broadcast(event)
            # Record a private confirmation for the host
            agent.append_env_message("You started the voting.")
            scene.log(f"{agent.name} has started the voting.")
            return True
        return False


class VotingStatusAction(Action):
    NAME = "voting_status"
    DESC = "Show current voting progress: counts and pending voters."
    INSTRUCTION = """- To check voting status:
<Action name=\"voting_status\" />
"""

    def handle(self, action_data, agent, simulator, scene):
        started = scene.state.get("voting_started", False)
        votes = scene.state.get("votes", {})
        num_members = sum(1 for a in simulator.agents.values() if a.name != "Host")
        if not started:
            agent.append_env_message("Voting has not started.")
            return True

        yes = sum(v == "yes" for v in votes.values())
        no = sum(v == "no" for v in votes.values())
        abstain = sum(v == "abstain" for v in votes.values())
        pending_names = [
            name
            for name in simulator.agents.keys()
            if name != "Host" and name not in votes
        ]
        pending = len(pending_names)
        lines = [
            "Voting status:",
            f"- Members: {num_members}",
            f"- Yes: {yes}, No: {no}, Abstain: {abstain}",
            f"- Pending: {pending}"
            + (f" ({', '.join(pending_names)})" if pending_names else ""),
        ]
        agent.append_env_message("\n".join(lines))
        return True


class GetRoundsAction(Action):
    NAME = "get_rounds"
    DESC = "Get the current round number."
    INSTRUCTION = """- To get the current round number:
<Action name=\"get_rounds\" />
"""

    def handle(self, action_data, agent, simulator, scene):
        rounds = simulator.round_num
        agent.append_env_message(f"Current round: {rounds}")
        return True


class RequestBriefAction(Action):
    NAME = "request_brief"
    DESC = (
        "Host: fetch a concise, neutral brief via LLM when debate stalls, facts are missing, "
        "or members request data; provide a clear 'desc' (topic + focus)."
    )
    INSTRUCTION = """
- To request a brief (host only):
<Action name=\"request_brief\"><desc>[topic + focus]</desc></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        # Only the host can fetch briefs
        if getattr(agent, "name", "") != "Host":
            agent.append_env_message("Only the Host can use request_brief.")
            return False

        desc = action_data.get("desc") if isinstance(action_data, dict) else None
        if not desc or not isinstance(desc, str):
            agent.append_env_message(
                'Missing parameter: "desc" (description of material to retrieve).'
            )
            return False

        # Prepare a concise LLM prompt for a short, actionable briefing
        system_prompt = (
            "You are a policy analyst assisting a legislative council debate. "
            "Generate a neutral, factual, concise briefing to unblock discussion. "
            "Output plain text only (no JSON, no role tags)."
        )
        user_prompt = (
            "Provide 5–7 crisp bullets with concrete facts, examples, or precedents. "
            "Include numbers if helpful and clearly label estimates. Keep under ~180 words.\n"
            f"Need: {desc}\n"
        )

        material = None
        try:
            # Try using the configured LLM
            material = agent.call_llm(
                simulator.clients,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            if not isinstance(material, str):
                material = ""
        except Exception:
            material = ""

        if not material.strip():
            # Fallback: short list of prompts to guide discussion
            material = (
                f"- Scope: {desc}\n"
                "- Key fact/definition\n"
                "- Comparable example (outcome)\n"
                "- Stakeholders: who benefits / pays\n"
                "- Rough cost or impact (estimate)\n"
                "- Top risk and mitigation\n"
                "- Open question for the chamber"
            )

        content = f"Brief (private) on '{desc}':\n{material.strip()}"
        # Deliver privately to host and record the event (private)
        agent.append_env_message(content)
        # Add a concise transcript note (non-world log)
        try:
            simulator.record_log(
                f"{agent.name} requested brief: {desc}",
                sender=agent.name,
                recipients=[agent.name],
                kind="request_brief",
            )
        except Exception:
            pass
        scene.log(f"{agent.name} requested brief for: {desc} (private)")
        return True


class VoteAction(Action):
    NAME = "vote"
    DESC = "Member casts a vote with optional comment."
    INSTRUCTION = """- To vote (only after voting has started):
<Action name=\"vote\"><vote>yes|no|abstain</vote><comment>[optional]</comment></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        if not scene.state.get("voting_started", False):
            agent.append_env_message("Voting has not started yet.")
            return False

        if agent.name in scene.state.get("votes", {}):
            agent.append_env_message("You have already voted.")
            return False

        vote = action_data.get("vote")
        if vote in ["yes", "no", "abstain"] and agent.name != "Host":
            scene.state.setdefault("votes", {})[agent.name] = vote
            comment = action_data.get("comment", "")
            vote_message = f"I vote {vote} on the draft."
            if comment:
                vote_message += f" Comment: {comment}"
            event = MessageEvent(agent.name, vote_message)
            # Route through scene delivery so voter also retains their own message
            scene.deliver_message(event, agent, simulator)
            scene.log(
                f"{agent.name} votes {vote}"
                + (f" with comment: {comment}" if comment else "")
            )
            return True
        return False
