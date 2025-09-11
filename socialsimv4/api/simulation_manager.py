import threading
from concurrent.futures import ThreadPoolExecutor


class SimulationManager:
    def __init__(self, max_workers=10):
        self.simulations = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()

    def start_simulation(self, sim_code, simulator):
        with self.lock:
            if sim_code in self.simulations:
                return False  # Simulation already running
            self.simulations[sim_code] = simulator

        self.executor.submit(simulator.run)
        return True

    def get_simulation(self, sim_code):
        with self.lock:
            return self.simulations.get(sim_code)

    def stop_simulation(self, sim_code):
        with self.lock:
            if sim_code in self.simulations:
                # This is a simplified stop. In a real application, you would
                # need a more graceful way to stop the simulation loop.
                del self.simulations[sim_code]
                return True
        return False


simulation_manager = SimulationManager()
