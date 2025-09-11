import threading
import queue
import time
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from fastapi import WebSocket
from socialsimv4.core.simulator import Simulator


class SimulationInstance:
    def __init__(self, simulator):
        self.simulator = simulator
        self.active_websockets = {}
        self.ws_lock = threading.Lock()
        self.message_queue = queue.Queue()
        # The simulator's event handler is now set at its creation time.
        # This instance's job is to provide that handler.
        self.simulator.log_event = self.handle_event
        for agent in self.simulator.agents.values():
            agent.log_event = self.handle_event

        self.message_sender_thread = threading.Thread(target=self.message_sender_loop, daemon=True)
        self.message_sender_thread.start()

    def handle_event(self, event_type, data):
        self.message_queue.put(json.dumps({"type": event_type, "data": data}))

    async def send_message_to_websockets(self, message):
        with self.ws_lock:
            if not self.active_websockets:
                return False

            disconnected_sockets = []
            for ws_id, websocket in self.active_websockets.items():
                try:
                    await websocket.send_text(message)
                except Exception:
                    disconnected_sockets.append(ws_id)

            for ws_id in disconnected_sockets:
                self.active_websockets.pop(ws_id, None)

            return bool(self.active_websockets)

    def message_sender_loop(self):
        while True:
            if not self.message_queue.empty() and self.active_websockets:
                message = self.message_queue.get()
                asyncio.run(self.send_message_to_websockets(message))
            else:
                time.sleep(0.1)

    def add_websocket(self, websocket: WebSocket):
        with self.ws_lock:
            self.active_websockets[id(websocket)] = websocket

    def remove_websocket(self, websocket: WebSocket):
        with self.ws_lock:
            self.active_websockets.pop(id(websocket), None)


class SimulationManager:
    def __init__(self, max_workers=10):
        self.simulations = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()

    def start_simulation(self, sim_code, agents, scenario, clients):
        with self.lock:
            if sim_code in self.simulations:
                return False  # Simulation already running
            
            simulator = Simulator(agents, scenario, clients)
            instance = SimulationInstance(simulator)
            self.simulations[sim_code] = instance

        self.executor.submit(instance.simulator.run)
        return True

    def load_simulation(self, sim_code, data, clients):
        with self.lock:
            if sim_code in self.simulations:
                self.stop_simulation(sim_code)

            simulator = Simulator.from_dict(data, clients)
            instance = SimulationInstance(simulator)
            self.simulations[sim_code] = instance
        
        self.executor.submit(instance.simulator.run)
        return True

    def get_simulation(self, sim_code):
        with self.lock:
            return self.simulations.get(sim_code)

    def stop_simulation(self, sim_code):
        with self.lock:
            if sim_code in self.simulations:
                del self.simulations[sim_code]
                return True
        return False


simulation_manager = SimulationManager()
