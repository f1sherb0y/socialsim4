import asyncio
import json
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import WebSocket

from socialsim4.core.simulator import Simulator


class SimulationInstance:
    def __init__(self, simulator):
        self.simulator = simulator
        self.active_websockets = {}
        self.ws_lock = threading.Lock()
        self.message_queue = queue.Queue()
        self.running = False
        self.run_lock = threading.Lock()
        # The simulator's event handler is now set at its creation time.
        # This instance's job is to provide that handler.
        self.simulator.log_event = self.handle_event
        for agent in self.simulator.agents.values():
            agent.log_event = self.handle_event

        self.message_sender_thread = threading.Thread(
            target=self.message_sender_loop, daemon=True
        )
        self.message_sender_thread.start()

    def run(self, num_rounds):
        with self.run_lock:
            if self.running:
                print(f"Simulation {self.simulator} is already running.")
                return  # Already running
            self.running = True

        try:
            # Interpret num_rounds as number of turns for the simplified engine
            self.simulator.run(max_turns=num_rounds)
        finally:
            with self.run_lock:
                self.running = False

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

    def start_simulation(self, sim_code, agents, scene, clients, initial_rounds=1):
        with self.lock:
            if sim_code in self.simulations:
                return False  # Simulation already running

            simulator = Simulator(agents, scene, clients)
            instance = SimulationInstance(simulator)
            self.simulations[sim_code] = instance

        self.executor.submit(instance.run, num_rounds=initial_rounds)
        return True

    def run_simulation(self, sim_code, rounds):
        instance = self.get_simulation(sim_code)
        if not instance:
            return False, "Simulation not found"

        if instance.running:
            return False, "Simulation is already running"

        self.executor.submit(instance.run, num_rounds=rounds)
        return True, f"Ran simulation '{sim_code}' for {rounds} turn(s)."

    def load_simulation(self, sim_code, data, clients):
        with self.lock:
            if sim_code in self.simulations:
                self.stop_simulation(sim_code)

            simulator = Simulator.from_dict(data, clients)
            instance = SimulationInstance(simulator)
            self.simulations[sim_code] = instance

        # Do not start simulation on load
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
