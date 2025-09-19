from socialsimv4.core.action import Action
from socialsimv4.core.event import PublicEvent


class MoveToLocationAction(Action):
    NAME = "move_to_location"
    INSTRUCTION = """- To move to a location: {"action": "move_to_location", "location": "[location_name]"}
- Or move to coordinates: {"action": "move_to_location", "x": 12, "y": 34}"""

    def handle(self, action_data, agent, simulator, scene):
        """Move to a location or coordinates using grid pathfinding and terrain costs."""
        # Resolve start
        start_xy = agent.properties.get("map_xy")
        if not start_xy:
            # Fallback using named position
            pos_name = agent.properties.get("map_position")
            cur_loc = scene.game_map.get_location(pos_name) if pos_name else None
            if not cur_loc:
                agent.append_env_message("Current position unknown; cannot move.")
                return False
            start_xy = [cur_loc.x, cur_loc.y]

        # Resolve target
        target_xy = None
        target_location = action_data.get("location")
        if target_location:
            loc = scene.game_map.get_location(target_location)
            if not loc:
                agent.append_env_message(
                    f"Location '{target_location}' does not exist."
                )
                return False
            target_xy = [loc.x, loc.y]
        else:
            if "target" in action_data and isinstance(action_data["target"], dict):
                tx, ty = action_data["target"].get("x"), action_data["target"].get("y")
            else:
                tx, ty = action_data.get("x"), action_data.get("y")
            if tx is None or ty is None:
                agent.append_env_message(
                    "Provide a target 'location' or coordinates 'x' and 'y'."
                )
                return False
            target_xy = [int(tx), int(ty)]

        if start_xy[0] == target_xy[0] and start_xy[1] == target_xy[1]:
            agent.append_env_message("You are already at the target.")
            return False

        # Pathfinding
        path = scene.game_map.find_path(tuple(start_xy), tuple(target_xy))
        if not path:
            agent.append_env_message(
                "No reachable path; possibly blocked by obstacles."
            )
            return False

        # Compute energy cost: sum of tile movement_cost entering each tile, scaled
        base_cost = scene.game_map.path_cost(path)
        energy_cost = max(1, int(base_cost * scene.movement_cost))

        if agent.properties["energy"] < energy_cost:
            agent.append_env_message(
                f"Not enough energy. Moving to {tuple(target_xy)} costs {energy_cost}, you have {agent.properties['energy']}."
            )
            return False

        # Update location occupancy (named POIs)
        prev_loc = scene.game_map.get_location_at(start_xy[0], start_xy[1])
        if prev_loc:
            prev_loc.remove_agent(agent.name)

        agent.properties["map_xy"] = [target_xy[0], target_xy[1]]
        # Update map_position name if exactly on a named location
        new_loc = scene.game_map.get_location_at(target_xy[0], target_xy[1])
        agent.properties["map_position"] = (
            new_loc.name if new_loc else f"{target_xy[0]},{target_xy[1]}"
        )
        if new_loc:
            new_loc.add_agent(agent.name)

        agent.properties["energy"] -= energy_cost

        # Broadcast movement event (global)
        message = f"{agent.name} moved from {tuple(start_xy)} to {tuple(target_xy)}"
        simulator.broadcast(PublicEvent(message))

        # Inform the agent about the new position
        desc = (
            new_loc.description
            if new_loc
            else scene.game_map.get_tile(*target_xy).terrain
        )
        agent.append_env_message(f"You arrived at {tuple(target_xy)}. {desc}")

        # Nearby agents at destination
        nearby = []
        for other in simulator.agents.values():
            if other.name == agent.name:
                continue
            oxy = other.properties.get("map_xy")
            if oxy:
                dist = abs(oxy[0] - target_xy[0]) + abs(oxy[1] - target_xy[1])
                if dist <= scene.chat_range:
                    nearby.append(f"{other.name} (distance {dist})")
        if nearby:
            agent.append_env_message("Nearby agents: " + ", ".join(nearby))

        return True


class LookAroundAction(Action):
    NAME = "look_around"
    INSTRUCTION = """- To look around and see nearby locations and agents: {"action": "look_around", "radius": 5}"""

    def handle(self, action_data, agent, simulator, scene):
        """Look around: list nearby locations, resources, and agents."""
        xy = agent.properties.get("map_xy")
        if not xy:
            pos_name = agent.properties.get("map_position")
            loc = scene.game_map.get_location(pos_name) if pos_name else None
            if not loc:
                return False
            xy = [loc.x, loc.y]

        radius = int(action_data.get("radius", max(3, min(7, scene.chat_range))))

        current_loc = scene.game_map.get_location_at(xy[0], xy[1])
        tile = scene.game_map.get_tile(xy[0], xy[1])
        here_desc = (
            f"{current_loc.name}: {current_loc.description}"
            if current_loc
            else tile.terrain
        )

        info = [f"You are at ({xy[0]},{xy[1]}): {here_desc}"]

        # Resources on current tile
        if tile.resources:
            resources = ", ".join([f"{k}({v})" for k, v in tile.resources.items()])
            info.append(f"Resources here: {resources}")

        # Nearby named locations
        nearby_locations = scene.game_map.get_nearby_locations(
            xy[0], xy[1], radius=radius
        )
        if nearby_locations:
            info.append("Nearby locations:")
            for loc in nearby_locations[:8]:
                dist = abs(loc.x - xy[0]) + abs(loc.y - xy[1])
                if dist == 0:
                    continue
                info.append(f"  - {loc.name} (distance: {dist}) - {loc.description}")

        # Nearby agents
        nearby_agents = []
        for other in simulator.agents.values():
            if other.name == agent.name:
                continue
            oxy = other.properties.get("map_xy")
            if not oxy:
                continue
            dist = abs(oxy[0] - xy[0]) + abs(oxy[1] - xy[1])
            if dist <= radius:
                nearby_agents.append((dist, other.name))
        if nearby_agents:
            nearby_agents.sort(key=lambda x: x[0])
            agents_str = ", ".join(
                [f"{name}({dist})" for dist, name in nearby_agents[:10]]
            )
            info.append(f"Nearby agents: {agents_str}")

        agent.append_env_message("\n".join(info))
        return True


class GatherResourceAction(Action):
    NAME = "gather_resource"
    INSTRUCTION = """- To gather resources: {"action": "gather_resource", "resource": "[resource_name]", "amount": [number]}"""

    def handle(self, action_data, agent, simulator, scene):
        """Gather resources, preferring tile resources at current position."""
        resource_type = action_data.get("resource")
        amount = int(action_data.get("amount", 1))

        xy = agent.properties.get("map_xy")
        if not xy:
            pos_name = agent.properties.get("map_position")
            loc = scene.game_map.get_location(pos_name) if pos_name else None
            if loc:
                xy = [loc.x, loc.y]
        if not xy:
            agent.append_env_message("Current position unknown; cannot gather.")
            return False

        tile = scene.game_map.get_tile(xy[0], xy[1])
        available = 0
        source = "tile"
        if resource_type in tile.resources:
            available = tile.resources[resource_type]
        else:
            # Fallback: named location resources if present
            loc = scene.game_map.get_location_at(xy[0], xy[1])
            if loc and resource_type in loc.resources:
                available = loc.resources[resource_type]
                source = "location"

        if available <= 0:
            agent.append_env_message(f"No {resource_type} to gather here.")
            return False

        actual_amount = max(0, min(amount, available))
        if actual_amount == 0:
            agent.append_env_message(f"{resource_type} is depleted.")
            return False

        # 执行收集
        if source == "tile":
            tile.resources[resource_type] -= actual_amount
        else:
            loc.resources[resource_type] -= actual_amount

        agent.properties["inventory"][resource_type] = (
            agent.properties["inventory"].get(resource_type, 0) + actual_amount
        )

        message = f"{agent.name} gathered {actual_amount} {resource_type} at ({xy[0]},{xy[1]})"
        simulator.broadcast(PublicEvent(message))

        agent.append_env_message(
            f"You gathered {actual_amount} {resource_type}. Inventory: {agent.properties['inventory']}"
        )
        return True


class RestAction(Action):
    NAME = "rest"
    INSTRUCTION = """- To rest and recover energy: {"action": "rest"}"""

    def handle(self, action_data, agent, simulator, scene):
        """Rest to regain energy."""
        current_location = scene.game_map.get_location(agent.properties["map_position"])

        # Resting in a building is more effective
        if current_location and current_location.location_type == "building":
            energy_gain = 30
            agent.append_env_message(
                f"You rest comfortably in {current_location.name}."
            )
        else:
            energy_gain = 15
            agent.append_env_message(
                f"You take a short rest at {current_location.name if current_location else 'this spot'}."
            )

        agent.properties["energy"] = min(100, agent.properties["energy"] + energy_gain)

        message = f"{agent.name} took a rest"
        simulator.broadcast(PublicEvent(message))

        return True
