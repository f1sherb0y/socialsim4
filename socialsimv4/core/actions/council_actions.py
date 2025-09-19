from socialsimv4.core.action import Action
from socialsimv4.core.event import MessageEvent, PublicEvent


class StartVotingAction(Action):
    NAME = "start_voting"
    DESC = "Host starts a voting round."
    INSTRUCTION = """- To start voting: {"action": "start_voting"}"""

    def handle(self, action_data, agent, simulator, scene):
        if not scene.state.get("voting_started", False):
            scene.state["voting_started"] = True
            event = PublicEvent(
                "The Host has initiated the voting round. Please cast your votes now."
            )
            simulator.broadcast(event)
            scene.log(f"{agent.name} has started the voting.")
            return True
        return False


class GetVotingResultAction(Action):
    NAME = "get_voting_result"
    DESC = "Host checks and announces vote result."
    INSTRUCTION = """- To get voting result: {"action": "get_voting_result"}"""

    def handle(self, action_data, agent, simulator, scene):
        if scene.state.get("voting_started", False):
            num_members = sum(1 for a in simulator.agents.values() if a.name != "Host")
            if len(scene.state.get("votes", {})) >= num_members:
                yes = sum(v == "yes" for v in scene.state["votes"].values())
                no = sum(v == "no" for v in scene.state["votes"].values())
                abstain = num_members - yes - no
                result = "passed" if yes > num_members / 2 else "failed"
                event_content = f"Voting on the draft has concluded. It {result} with {yes} yes, {no} no, and {abstain} abstain."

                # simulator.broadcast(PublicEvent(event_content))
                agent.append_env_message(event_content)

                scene.complete = True
                scene.state["votes"] = {}
                scene.log("Voting has concluded.")
                return True
            else:
                pending = num_members - len(scene.state.get("votes", {}))
                info = PublicEvent(
                    f"Not all votes are in yet. {pending} votes pending."
                )
                agent.append_env_message(info.to_string())
                simulator.record_event(info, recipients=[agent.name])
                return True
        return False


class GetRoundsAction(Action):
    NAME = "get_rounds"
    DESC = "Get the current round number."
    INSTRUCTION = """- To get the current round number: {"action": "get_rounds"}"""

    def handle(self, action_data, agent, simulator, scene):
        rounds = simulator.round_num
        agent.append_env_message(f"Current round: {rounds}")
        return True


class GetMaterialAction(Action):
    NAME = "get_material"
    DESC = "Host fetches briefing material via LLM."
    INSTRUCTION = (
        """
- To fetch material (host only): {"action": "get_material", "desc": "[what material is needed]"}
"""
    )

    def handle(self, action_data, agent, simulator, scene):
        # Only the host can fetch materials
        if getattr(agent, "name", "") != "Host":
            agent.append_env_message("Only the Host can use get_material.")
            return False

        desc = action_data.get("desc") if isinstance(action_data, dict) else None
        if not desc or not isinstance(desc, str):
            agent.append_env_message(
                'Missing parameter: "desc" (description of material to retrieve).'
            )
            return False

        # Prepare a concise LLM prompt for generating briefing material
        system_prompt = (
            "You are a policy analyst assisting a legislative council debate. "
            "Generate neutral, factual, concise briefing material to unblock discussion. "
            "Output plain text only (no plans, no JSON, no role tags)."
        )
        user_prompt = (
            "Provide 4-7 concise bullets with concrete facts, examples, or historical precedents "
            "relevant to the following need. Include brief numbers if helpful and clearly label estimates.\n"
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
            # Fallback if LLM unavailable or returned empty
            material = (
                f"- Background context for: {desc}\n"
                "- Key stakeholders and likely positions\n"
                "- Benefits and trade-offs\n"
                "- Practical constraints (cost, enforcement, timeline)\n"
                "- Open questions for further discussion"
            )

        content = (
            f"Host provides additional material on '{desc}':\n{material.strip()}"
        )
        event = PublicEvent(content)
        simulator.broadcast(event)
        scene.log(f"{agent.name} fetched material for: {desc}")
        return True


class VoteAction(Action):
    NAME = "vote"
    DESC = "Member casts a vote with optional comment."
    INSTRUCTION = """- To vote (only after voting has started): {"action": "vote", "vote": "yes" or "no" or "abstain", "comment": "[your comment here (optional)]"}"""

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
            simulator.broadcast(event)
            scene.log(
                f"{agent.name} votes {vote}"
                + (f" with comment: {comment}" if comment else "")
            )
            return True
        return False
