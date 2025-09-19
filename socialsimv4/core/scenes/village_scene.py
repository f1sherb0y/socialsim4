import heapq
import math
from typing import Dict, Iterable, List, Optional, Tuple

from socialsimv4.core.actions.base_actions import SpeakAction
from socialsimv4.core.actions.map_actions import (
    GatherResourceAction,
    LookAroundAction,
    MoveToLocationAction,
    RestAction,
)
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


class Tile:
    """A single grid tile."""

    def __init__(
        self,
        passable: bool = True,
        movement_cost: int = 1,
        terrain: str = "plain",
        resources: Optional[Dict] = None,
    ):
        self.passable = passable
        self.movement_cost = movement_cost
        self.terrain = terrain
        self.resources = resources or {}

    def to_dict(self):
        return {
            "passable": self.passable,
            "movement_cost": self.movement_cost,
            "terrain": self.terrain,
            "resources": self.resources,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            passable=data.get("passable", True),
            movement_cost=data.get("movement_cost", 1),
            terrain=data.get("terrain", "plain"),
            resources=data.get("resources", {}),
        )


class GameMap:
    """游戏地图管理器"""

    def __init__(self, width: int = 20, height: int = 20):
        self.width = width
        self.height = height
        self.locations: Dict[str, MapLocation] = {}
        self.grid = {}  # 坐标到位置名称的映射
        # Sparse storage of tiles: only store non-default tiles explicitly
        self.tiles: Dict[Tuple[int, int], Tile] = {}

    def to_dict(self):
        """Serializes the map to a dictionary."""
        tiles = []
        for (x, y), tile in self.tiles.items():
            tiles.append({"x": x, "y": y, **tile.to_dict()})
        return {
            "width": self.width,
            "height": self.height,
            "tiles": tiles,
            "locations": [
                {
                    "name": loc.name,
                    "x": loc.x,
                    "y": loc.y,
                    "type": loc.location_type,
                    "description": loc.description,
                    "resources": loc.resources,
                    "capacity": loc.capacity,
                }
                for loc in self.locations.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Creates a map from a dictionary."""
        width = data.get("width", 20)
        height = data.get("height", 20)
        game_map = cls(width, height)

        for t in data.get("tiles", []):
            x, y = t["x"], t["y"]
            tile = Tile.from_dict(t)
            game_map.tiles[(x, y)] = tile

        for loc in data.get("locations", []):
            game_map.add_location(
                loc.get("name"),
                loc.get("x"),
                loc.get("y"),
                location_type=loc.get("type", "generic"),
                description=loc.get("description", ""),
                resources=loc.get("resources", {}),
                capacity=loc.get("capacity", -1),
            )
        return game_map

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
            distance = abs(location.x - x) + abs(location.y - y)
            if distance <= radius:
                nearby.append(location)
        return sorted(nearby, key=lambda loc: abs(loc.x - x) + abs(loc.y - y))

    def get_tile(self, x: int, y: int) -> Tile:
        """Return tile, defaulting to passable plain if unset."""
        return self.tiles.get((x, y), Tile())

    def set_tile(
        self,
        x: int,
        y: int,
        *,
        passable: Optional[bool] = None,
        movement_cost: Optional[int] = None,
        terrain: Optional[str] = None,
        resources: Optional[Dict] = None,
    ):
        tile = self.tiles.get((x, y), Tile())
        if passable is not None:
            tile.passable = passable
        if movement_cost is not None:
            tile.movement_cost = movement_cost
        if terrain is not None:
            tile.terrain = terrain
        if resources is not None:
            tile.resources = resources
        self.tiles[(x, y)] = tile

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_passable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.get_tile(x, y).passable

    def neighbors(self, x: int, y: int) -> Iterable[Tuple[int, int]]:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.is_passable(nx, ny):
                yield nx, ny

    def heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        ax, ay = a
        bx, by = b
        return abs(ax - bx) + abs(ay - by)

    def find_path(
        self, start: Tuple[int, int], goal: Tuple[int, int]
    ) -> Optional[List[Tuple[int, int]]]:
        """A* pathfinding from start to goal; returns list including goal.
        Returns None if no path.
        """
        if start == goal:
            return [goal]
        if not (self.is_passable(*start) and self.is_passable(*goal)):
            return None

        open_heap: List[Tuple[float, Tuple[int, int]]] = []
        heapq.heappush(open_heap, (0, start))
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        g_score: Dict[Tuple[int, int], float] = {start: 0}

        while open_heap:
            _, current = heapq.heappop(open_heap)
            if current == goal:
                # Reconstruct path
                path = []
                while current is not None:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            cx, cy = current
            for nx, ny in self.neighbors(cx, cy):
                tentative_g = g_score[current] + self.get_tile(nx, ny).movement_cost
                neighbor = (nx, ny)
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self.heuristic(neighbor, goal)
                    heapq.heappush(open_heap, (f_score, neighbor))

        return None

    def path_cost(self, path: List[Tuple[int, int]]) -> int:
        if not path:
            return 0
        # exclude start tile cost, count moving into each tile
        cost = 0
        for x, y in path[1:]:
            cost += max(1, int(self.get_tile(x, y).movement_cost))
        return cost

    def display_map(self, agents: Dict[str, Agent] = None) -> str:
        """Generate a textual map overview (English)."""
        map_display = []
        map_display.append("Village Map:")
        map_display.append("=" * 40)

        for location in self.locations.values():
            agents_here = []
            if agents:
                for agent_name, agent in agents.items():
                    # Prefer coordinates if available
                    xy = agent.properties.get("map_xy")
                    if xy and (location.x, location.y) == tuple(xy):
                        agents_here.append(agent_name)
                    elif (
                        hasattr(agent, "map_position")
                        and agent.properties.get("map_position") == location.name
                    ):
                        agents_here.append(agent_name)

            agent_info = f" ({', '.join(agents_here)})" if agents_here else ""
            map_display.append(
                f"- {location.name} ({location.x},{location.y}){agent_info}"
            )
            map_display.append(f"   {location.description}")
            if location.resources:
                resources_str = ", ".join(
                    [f"{k}:{v}" for k, v in location.resources.items()]
                )
            map_display.append(f"   Resources: {resources_str}")
            map_display.append("")

        return "\n".join(map_display)


class VillageScene(Scene):
    TYPE = "village_scene"
    """支持地图的场景"""

    def __init__(
        self,
        name: str,
        initial_event: str,
        game_map: GameMap,
        movement_cost: int = 1,
        chat_range: int = 5,
    ):
        super().__init__(name, initial_event)
        self.game_map = game_map
        self.movement_cost = movement_cost
        self.chat_range = chat_range
        self.state["time"] = 0

    def get_scenario_description(self):
        return f"""
You live in a grid-based virtual village (size: {self.game_map.width}x{self.game_map.height}).
You have coordinates, needs (hunger, energy), and an inventory. You can move across the map, gather resources, and interact with other agents.
- Use move_to to reach coordinates or named locations; movement cost depends on terrain and is multiplied by {self.movement_cost}.
- Use look_around to see nearby locations, resources, and agents; speaking range is {self.chat_range}.
"""

    def get_behavior_guidelines(self):
        return """
Map living guidelines:
- Move to different places to explore, find resources, and meet others.
- Gather resources at resource tiles or named locations.
- Use buildings to rest; manage energy and plan routes efficiently.
- Speak only to nearby agents (within range), and consider relevance.
- Time passes each round; hunger increases and energy decreases.

Movement strategy:
- Look around before choosing where to go.
- Consider distance and energy cost.
- Prioritize immediate needs (hunger, fatigue).
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
{"action": "move_to_location", "location": "farm"}

--- Thoughts ---
There are people nearby; I'll greet them.

--- Plan ---
1. Look around.
2. Speak to nearby agents.

--- Action ---
{"action": "speak", "message": "Hi everyone nearby!"}
"""

    def initialize_agent(self, agent: Agent):
        """Initializes an agent with scene-specific properties."""
        super().initialize_agent(agent)
        agent.properties["hunger"] = 0
        agent.properties["energy"] = 100
        agent.properties["inventory"] = {}
        # Default spawn at village_center if exists, else center of map
        spawn = self.game_map.get_location("village_center")
        if spawn:
            agent.properties["map_xy"] = [spawn.x, spawn.y]
            agent.properties["map_position"] = "village_center"
            spawn.add_agent(agent.name)
        else:
            cx, cy = self.game_map.width // 2, self.game_map.height // 2
            agent.properties["map_xy"] = [cx, cy]
            agent.properties["map_position"] = f"{cx},{cy}"

    def get_scene_actions(self, agent: Agent):
        """Return actions available in the village (map) scene for this agent."""
        return [
            SpeakAction(),
            MoveToLocationAction(),
            LookAroundAction(),
            GatherResourceAction(),
            RestAction(),
        ]

    def post_round(self, simulator: Simulator):
        """每轮结束后的处理"""
        self.state["time"] += 1

        # Update agent state
        for agent in simulator.agents.values():
            # Basic physiological changes
            agent.properties["hunger"] = min(100, agent.properties["hunger"] + 3)
            agent.properties["energy"] = max(0, agent.properties["energy"] - 2)

            # Position/occupancy sync for named locations
            xy = agent.properties.get("map_xy")
            if xy:
                loc = self.game_map.get_location_at(xy[0], xy[1])
                # 清理不在此处的占用
                for location in self.game_map.locations.values():
                    if agent.name in location.agents_here and (
                        location.x != xy[0] or location.y != xy[1]
                    ):
                        location.remove_agent(agent.name)
                if loc and agent.name not in loc.agents_here:
                    loc.add_agent(agent.name)

            # Status warnings (English, plain)
            if agent.properties["hunger"] >= 70:
                status = f"You are quite hungry (hunger: {agent.properties['hunger']}). Consider finding food."
                evt = StatusEvent(status)
                agent.append_env_message(evt.to_string(self.state.get("time")))
                simulator.record_event(evt, recipients=[agent.name])

            if agent.properties["energy"] <= 30:
                status = f"You are tired (energy: {agent.properties['energy']}). Consider resting or moving less."
                evt = StatusEvent(status)
                agent.append_env_message(evt.to_string(self.state.get("time")))
                simulator.record_event(evt, recipients=[agent.name])

    def get_agent_status_prompt(self, agent: Agent) -> str:
        time_of_day = "day" if self.state.get("time", 0) % 24 < 18 else "night"
        xy = agent.properties.get("map_xy") or [None, None]
        loc = self.game_map.get_location_at(xy[0], xy[1]) if xy[0] is not None else None
        loc_name = loc.name if loc else agent.properties.get("map_position", "?")
        return f"""
--- Status ---
Current position: {loc_name} at ({xy[0]},{xy[1]})
Hunger level: {agent.properties["hunger"]}
Energy level: {agent.properties["energy"]}
Inventory: {agent.properties["inventory"]}
Current time: {self.state.get("time", 0)} hours ({time_of_day})
"""

    def deliver_message(self, event: PublicEvent, sender: Agent, simulator: Simulator):
        """Limit chat delivery to agents within chat_range (Manhattan distance)."""
        time = self.state.get("time")
        formatted = event.to_string(time)
        sxy = sender.properties.get("map_xy")
        recipients = []
        for a in simulator.agents.values():
            if a.name == sender.name:
                continue
            axy = a.properties.get("map_xy")
            if not sxy or not axy:
                # Fallback: if coords missing, deliver as default
                a.append_env_message(formatted)
                recipients.append(a.name)
                continue
            dist = abs(sxy[0] - axy[0]) + abs(sxy[1] - axy[1])
            if dist <= self.chat_range:
                a.append_env_message(formatted)
                recipients.append(a.name)
        simulator.record_event(event, recipients=recipients)

    def to_dict(self):
        base = super().to_dict()
        base.update(
            {
                "movement_cost": self.movement_cost,
                "chat_range": self.chat_range,
                "map": self.game_map.to_dict(),
            }
        )
        return base

    @classmethod
    def from_dict(cls, data):
        name = data.get("name", "VillageScene")
        initial_event = data.get("initial_event", "")
        movement_cost = data.get("movement_cost", 1)
        chat_range = data.get("chat_range", 5)
        map_cfg = data.get("map", {})
        game_map = GameMap.from_dict(map_cfg)

        scene = cls(
            name,
            initial_event,
            game_map=game_map,
            movement_cost=movement_cost,
            chat_range=chat_range,
        )
        scene.state = data.get("state", {"time": 0})
        return scene
