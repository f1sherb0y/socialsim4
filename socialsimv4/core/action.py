class Action:
    NAME = "base_action"
    INSTRUCTION = ""

    def handle(self, action_data, agent, simulator, scene):
        raise NotImplementedError
