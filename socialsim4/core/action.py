class Action:
    NAME = "base_action"
    INSTRUCTION = ""
    DESC = ""

    def handle(self, action_data, agent, simulator, scene):
        """
        Execute the action.

        Returns a triple: (success, result, summary)
        - success: bool indicating if the action executed successfully
        - result: dict capturing relevant outcomes so the frontend can replay
        - summary: one-line human-readable summary for timeline transcripts
        """
        raise NotImplementedError
