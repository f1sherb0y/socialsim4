import math
from typing import Dict, List, Optional, Tuple

from socialsimv4.core.agent import Agent
from socialsimv4.core.event import PublicEvent, StatusEvent
from socialsimv4.core.scene import Scene
from socialsimv4.core.simulator import Simulator


class MapLocation:
    """地图上的一个位置点"""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        location_type: str = "generic",
        description: str = "",
        resources: Dict = None,
        capacity: int = -1,
    ):
        self.name = name
        self.x = x
        self.y = y
        self.location_type = (
            location_type  # "building", "resource", "landmark", "generic"
        )
        self.description = description
        self.resources = resources or {}  # 可采集的资源
        self.capacity = capacity  # 最大容纳人数，-1表示无限制
        self.agents_here = set()  # 当前在此位置的智能体

    def add_agent(self, agent_name: str) -> bool:
        """添加智能体到此位置"""
        if self.capacity == -1 or len(self.agents_here) < self.capacity:
            self.agents_here.add(agent_name)
            return True
        return False

    def remove_agent(self, agent_name: str):
        """从此位置移除智能体"""
        self.agents_here.discard(agent_name)

    def get_distance_to(self, other_x: int, other_y: int) -> float:
        """计算到另一个坐标的距离"""
        return math.sqrt((self.x - other_x) ** 2 + (self.y - other_y) ** 2)


class GameMap:
    """游戏地图管理器"""

    def __init__(self, width: int = 20, height: int = 20):
        self.width = width
        self.height = height
        self.locations: Dict[str, MapLocation] = {}
        self.grid = {}  # 坐标到位置名称的映射
        self._setup_default_map()

    def _setup_default_map(self):
        """设置默认地图布局"""
        # 中心村庄
        self.add_location(
            "village_center", 10, 10, "landmark", "村庄中心，所有人聚集的地方"
        )

        # 住宅区
        self.add_location("house_1", 8, 8, "building", "农民的房子", capacity=2)
        self.add_location("house_2", 12, 8, "building", "商人的房子", capacity=2)
        self.add_location("house_3", 8, 12, "building", "铁匠的房子", capacity=2)

        # 工作场所
        self.add_location(
            "farm",
            5,
            10,
            "resource",
            "农场，可以种植和收获作物",
            resources={"apple": 10, "wheat": 15},
        )
        self.add_location(
            "market", 15, 10, "building", "市场，进行交易的地方", capacity=10
        )
        self.add_location(
            "blacksmith", 10, 15, "building", "铁匠铺，制作工具", capacity=3
        )

        # 自然资源点
        self.add_location(
            "forest", 3, 5, "resource", "森林，可以采集木材", resources={"wood": 20}
        )
        self.add_location(
            "lake", 17, 5, "resource", "湖泊，可以钓鱼", resources={"fish": 8}
        )
        self.add_location(
            "mine",
            3,
            17,
            "resource",
            "矿山，可以挖掘矿物",
            resources={"iron": 12, "stone": 25},
        )

    def add_location(
        self,
        name: str,
        x: int,
        y: int,
        location_type: str = "generic",
        description: str = "",
        resources: Dict = None,
        capacity: int = -1,
    ):
        """添加新位置到地图"""
        if 0 <= x < self.width and 0 <= y < self.height:
            location = MapLocation(
                name, x, y, location_type, description, resources, capacity
            )
            self.locations[name] = location
            self.grid[(x, y)] = name
            return True
        return False

    def get_location(self, name: str) -> Optional[MapLocation]:
        """获取位置信息"""
        return self.locations.get(name)

    def get_location_at(self, x: int, y: int) -> Optional[MapLocation]:
        """获取指定坐标的位置"""
        location_name = self.grid.get((x, y))
        return self.locations.get(location_name) if location_name else None

    def get_nearby_locations(
        self, x: int, y: int, radius: int = 3
    ) -> List[MapLocation]:
        """获取附近的位置"""
        nearby = []
        for location in self.locations.values():
            distance = math.sqrt((location.x - x) ** 2 + (location.y - y) ** 2)
            if distance <= radius:
                nearby.append(location)
        return sorted(nearby, key=lambda loc: loc.get_distance_to(x, y))

    def get_path_distance(self, from_loc: str, to_loc: str) -> float:
        """计算两个位置之间的距离"""
        from_location = self.get_location(from_loc)
        to_location = self.get_location(to_loc)
        if from_location and to_location:
            return from_location.get_distance_to(to_location.x, to_location.y)
        return float("inf")

    def display_map(self, agents: Dict[str, Agent] = None) -> str:
        """生成地图的文本显示"""
        map_display = []
        map_display.append("🗺️ 村庄地图:")
        map_display.append("=" * 40)

        for location in self.locations.values():
            agents_here = []
            if agents:
                for agent_name, agent in agents.items():
                    if (
                        hasattr(agent, "map_position")
                        and agent.map_position == location.name
                    ):
                        agents_here.append(agent_name)

            agent_info = f" ({', '.join(agents_here)})" if agents_here else ""
            map_display.append(
                f"📍 {location.name} ({location.x},{location.y}){agent_info}"
            )
            map_display.append(f"   {location.description}")
            if location.resources:
                resources_str = ", ".join(
                    [f"{k}:{v}" for k, v in location.resources.items()]
                )
                map_display.append(f"   🎁 资源: {resources_str}")
            map_display.append("")

        return "\n".join(map_display)


class MapScene(Scene):
    """支持地图的场景"""

    def __init__(
        self,
        name: str,
        initial_event: str,
        map_width: int = 20,
        map_height: int = 20,
        movement_cost: int = 1,
    ):
        super().__init__(name, initial_event)
        self.game_map = GameMap(map_width, map_height)
        self.movement_cost = movement_cost  # 移动消耗的能量
        self.state["time"] = 0

    def get_scenario_description(self):
        return f"""
你生活在一个有地图的虚拟村庄中。村庄有多个位置，你可以在它们之间移动。

当前地图信息:
{self.game_map.display_map()}

你有位置坐标、生理需求(饥饿、能量)、物品库存，可以在地图上移动、收集资源、与其他智能体交互。
每次移动会消耗 {self.movement_cost} 点能量。
"""

    def get_behavior_guidelines(self):
        return """
地图生活指南:
- 🚶 移动到不同位置: 可以探索地图、寻找资源、与他人会面
- 🎁 收集资源: 在资源点可以收集材料(农场的苹果、森林的木材等)
- 🏠 利用建筑: 在房子休息、在市场交易、在铁匠铺制作工具
- 👥 社交互动: 与同在一个位置的其他智能体交流
- ⚡ 管理能量: 移动消耗能量，需要合理规划路线
- 🕒 时间意识: 随时间推移需求会变化，合理安排活动

移动策略:
- 查看附近位置再决定去哪里
- 考虑距离和能量消耗
- 优先完成重要需求(饥饿、疲劳)
"""

    def get_examples(self):
        return """
--- Thoughts ---
I'm getting hungry. I should go to the farm to get some food.

--- Plan ---
1. Move to the farm.
2. Gather some apples.

--- Action ---
--- Move To Location ---
{"location": "farm"}
"""

    def initialize_agent(self, agent: Agent):
        """Initializes an agent with scene-specific properties."""
        agent.properties["hunger"] = 0
        agent.properties["energy"] = 100
        agent.properties["inventory"] = {}
        agent.properties["map_position"] = "village_center"

    def post_round(self, simulator: Simulator):
        """每轮结束后的处理"""
        self.state["time"] += 1

        # 更新智能体状态
        for agent in simulator.agents.values():
            # 基础生理需求变化
            agent.properties["hunger"] = min(100, agent.properties["hunger"] + 3)
            agent.properties["energy"] = max(0, agent.properties["energy"] - 2)

            # 位置状态更新
            location = self.game_map.get_location(agent.properties["map_position"])
            if location and agent.name not in location.agents_here:
                location.add_agent(agent.name)

            # 发送状态警告
            if agent.properties["hunger"] >= 70:
                status = f"你很饿了 (饥饿: {agent.properties['hunger']})，应该寻找食物。"
                agent.append_env_message(
                    StatusEvent(status).to_string(self.state.get("time"))
                )

            if agent.properties["energy"] <= 30:
                status = f"你很疲惫了 (能量: {agent.properties['energy']})，应该休息或减少移动。"
                agent.append_env_message(
                    StatusEvent(status).to_string(self.state.get("time"))
                )

    def parse_and_handle_action(self, action_data, agent: Agent, simulator: Simulator):
        """解析和处理动作"""
        action_name = action_data.get("action")

        # 处理地图特有的动作
        if action_name == "move_to_location":
            return self._handle_move_to_location(action_data, agent, simulator)
        elif action_name == "look_around":
            return self._handle_look_around(action_data, agent, simulator)
        elif action_name == "gather_resource":
            return self._handle_gather_resource(action_data, agent, simulator)
        elif action_name == "rest":
            return self._handle_rest(action_data, agent, simulator)
        else:
            # 调用父类方法处理标准动作
            return super().parse_and_handle_action(action_data, agent, simulator)

    def _handle_move_to_location(self, action_data, agent: Agent, simulator: Simulator):
        """处理移动到位置的动作"""
        target_location = action_data.get("location")

        current_pos = agent.properties["map_position"]
        target_loc = self.game_map.get_location(target_location)
        current_loc = self.game_map.get_location(current_pos)

        if not target_loc:
            agent.append_env_message(f"位置 '{target_location}' 不存在。")
            return False

        if current_pos == target_location:
            agent.append_env_message(f"你已经在 {target_location} 了。")
            return False

        # 计算移动距离和消耗
        distance = self.game_map.get_path_distance(current_pos, target_location)
        energy_cost = max(1, int(distance * self.movement_cost))

        if agent.properties["energy"] < energy_cost:
            agent.append_env_message(
                f"能量不足！移动到 {target_location} 需要 {energy_cost} 能量，你只有 {agent.properties['energy']}。"
            )
            return False

        # 执行移动
        if current_loc:
            current_loc.remove_agent(agent.name)
        target_loc.add_agent(agent.name)

        agent.properties["map_position"] = target_location
        agent.properties["energy"] -= energy_cost

        # 广播移动事件
        message = f"{agent.name} 从 {current_pos} 移动到了 {target_location}"
        simulator.broadcast(PublicEvent(message))
        self.log(f"📍 {message} (消耗 {energy_cost} 能量)")

        # 告诉智能体新位置的信息
        agent.append_env_message(
            f"你到达了 {target_location}。{target_loc.description}"
        )
        if target_loc.agents_here:
            others = [name for name in target_loc.agents_here if name != agent.name]
            if others:
                agent.append_env_message(f"这里还有: {', '.join(others)}")

        return True

    def _handle_look_around(self, action_data, agent: Agent, simulator: Simulator):
        """处理查看周围的动作"""
        current_location = self.game_map.get_location(agent.properties["map_position"])
        if not current_location:
            return False

        # 获取附近位置
        nearby_locations = self.game_map.get_nearby_locations(
            current_location.x, current_location.y, radius=5
        )

        info = [f"🔍 你在 {current_location.name}: {current_location.description}"]

        if current_location.agents_here:
            others = [
                name for name in current_location.agents_here if name != agent.name
            ]
            if others:
                info.append(f"👥 这里还有: {', '.join(others)}")

        if current_location.resources:
            resources = ", ".join(
                [f"{k}({v})" for k, v in current_location.resources.items()]
            )
            info.append(f"🎁 可用资源: {resources}")

        info.append("📍 附近位置:")
        for loc in nearby_locations[:6]:  # 只显示最近的6个位置
            if loc.name != agent.properties["map_position"]:
                distance = current_location.get_distance_to(loc.x, loc.y)
                info.append(
                    f"  - {loc.name} (距离: {distance:.1f}) - {loc.description}"
                )

        agent.append_env_message("\n".join(info))
        return True

    def _handle_gather_resource(self, action_data, agent: Agent, simulator: Simulator):
        """处理收集资源的动作"""
        resource_type = action_data.get("resource")
        amount = action_data.get("amount", 1)

        current_location = self.game_map.get_location(agent.properties["map_position"])
        if not current_location or resource_type not in current_location.resources:
            agent.append_env_message(f"这里没有 {resource_type} 可以收集。")
            return False

        available = current_location.resources[resource_type]
        actual_amount = min(amount, available)

        if actual_amount <= 0:
            agent.append_env_message(f"{resource_type} 已经被采集完了。")
            return False

        # 执行收集
        current_location.resources[resource_type] -= actual_amount
        agent.properties["inventory"][resource_type] = (
            agent.properties["inventory"].get(resource_type, 0) + actual_amount
        )

        message = f"{agent.name} 在 {agent.properties['map_position']} 收集了 {actual_amount} 个 {resource_type}"
        simulator.broadcast(PublicEvent(message))
        self.log(f"🎁 {message}")

        agent.append_env_message(
            f"你收集了 {actual_amount} 个 {resource_type}。库存: {agent.properties['inventory']}"
        )
        return True

    def _handle_rest(self, action_data, agent: Agent, simulator: Simulator):
        """处理休息动作"""
        current_location = self.game_map.get_location(agent.properties["map_position"])

        # 在房子里休息效果更好
        if current_location and current_location.location_type == "building":
            energy_gain = 30
            agent.append_env_message(f"你在 {current_location.name} 里舒适地休息了。")
        else:
            energy_gain = 15
            agent.append_env_message(
                f"你在 {current_location.name if current_location else '这里'} 休息了一会。"
            )

        agent.properties["energy"] = min(100, agent.properties["energy"] + energy_gain)

        message = f"{agent.name} 休息了一下"
        simulator.broadcast(PublicEvent(message))
        self.log(f"😴 {message} (恢复 {energy_gain} 能量)")

        return True

    def get_agent_status_prompt(self, agent: Agent) -> str:
        time_of_day = "day" if self.state.get("time", 0) % 24 < 18 else "night"
        return f"""
--- Status ---
Current position: {agent.properties["map_position"]}
Hunger level: {agent.properties["hunger"]}
Energy level: {agent.properties["energy"]}
Inventory: {agent.properties["inventory"]}
Current time: {self.state.get("time", 0)} hours ({time_of_day})
"""
