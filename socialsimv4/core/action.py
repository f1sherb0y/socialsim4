class Action:
    NAME = "base_action"
    INSTRUCTION = ""
    DESC = ""

    def handle(self, action_data, agent, simulator, scene):
        raise NotImplementedError
