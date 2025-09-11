from socialsimv4.core.action import Action
from socialsimv4.core.event import PublicEvent


class MoveToLocationAction(Action):
    NAME = "move_to_location"
    INSTRUCTION = """- To move to a location: {"action": "move_to_location", "location": "[location_name]"}"""

    def handle(self, action_data, agent, simulator, scenario):
        # This action is handled by the MapScene
        return scenario._handle_move_to_location(action_data, agent, simulator)


class LookAroundAction(Action):
    NAME = "look_around"
    INSTRUCTION = """- To look around and see nearby locations: {"action": "look_around"}"""

    def handle(self, action_data, agent, simulator, scenario):
        return scenario._handle_look_around(action_data, agent, simulator)


class GatherResourceAction(Action):
    NAME = "gather_resource"
    INSTRUCTION = """- To gather resources: {"action": "gather_resource", "resource": "[resource_name]", "amount": [number]}"""

    def handle(self, action_data, agent, simulator, scenario):
        return scenario._handle_gather_resource(action_data, agent, simulator)


class RestAction(Action):
    NAME = "rest"
    INSTRUCTION = """- To rest and recover energy: {"action": "rest"}"""

    def handle(self, action_data, agent, simulator, scenario):
        return scenario._handle_rest(action_data, agent, simulator)


class QuickMoveAction(Action):
    NAME = "quick_move"
    INSTRUCTION = """- To move to adjacent location (low energy cost): {"action": "quick_move", "direction": "north/south/east/west"}"""

    def handle(self, action_data, agent, simulator, scenario):
        if not hasattr(agent, 'map_position'):
            agent.map_position = "village_center"
        
        direction = action_data.get("direction", "").lower()
        direction_map = {
            "north": (0, -1),
            "south": (0, 1),
            "east": (1, 0),
            "west": (-1, 0)
        }
        
        if direction not in direction_map:
            agent.append_env_message("请指定有效方向: north, south, east, west")
            return False
        
        current_location = scenario.game_map.get_location(agent.map_position)
        if not current_location:
            return False
        
        dx, dy = direction_map[direction]
        new_x = current_location.x + dx
        new_y = current_location.y + dy
        
        target_location = scenario.game_map.get_location_at(new_x, new_y)
        if not target_location:
            agent.append_env_message(f"向{direction}方向没有可到达的位置。")
            return False
        
        if agent.energy < 1:
            agent.append_env_message("能量不足，无法移动。")
            return False
        
        # 执行快速移动
        current_location.remove_agent(agent.name)
        target_location.add_agent(agent.name)
        
        agent.map_position = target_location.name
        agent.energy -= 1  # 快速移动只消耗1点能量
        
        message = f"{agent.name} 向{direction}快速移动到了 {target_location.name}"
        simulator.broadcast(PublicEvent(message))
        scenario.log(f"🏃 {message}")
        
        agent.append_env_message(f"你快速移动到了 {target_location.name}。{target_location.description}")
        return True


class ExploreAction(Action):
    NAME = "explore"
    INSTRUCTION = """- To explore and discover new areas: {"action": "explore"}"""

    def handle(self, action_data, agent, simulator, scenario):
        if not hasattr(agent, 'map_position'):
            agent.map_position = "village_center"
        
        if agent.energy < 5:
            agent.append_env_message("探索需要至少5点能量。")
            return False
        
        current_location = scenario.game_map.get_location(agent.map_position)
        if not current_location:
            return False
        
        # 探索会消耗更多能量但可能发现资源
        agent.energy -= 5
        
        # 随机发现一些信息或小奖励
        import random
        discoveries = [
            f"你在 {current_location.name} 周围发现了一些有趣的东西！",
            f"探索让你更了解 {current_location.name} 的环境。",
            f"你在这里找到了一个隐藏的小径。",
            f"你发现了一些关于这个地方历史的线索。"
        ]
        
        discovery = random.choice(discoveries)
        agent.append_env_message(discovery)
        
        # 小概率获得额外资源
        if random.random() < 0.3:  # 30%概率
            bonus_items = ["coin", "herb", "stone"]
            bonus_item = random.choice(bonus_items)
            agent.inventory[bonus_item] = agent.inventory.get(bonus_item, 0) + 1
            agent.append_env_message(f"探索中你发现了 1 个 {bonus_item}！")
        
        message = f"{agent.name} 在 {current_location.name} 进行了探索"
        simulator.broadcast(PublicEvent(message))
        scenario.log(f"🔍 {message}")
        
        return True
