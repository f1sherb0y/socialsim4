import secrets


def generate_simulation_name() -> str:
    suffix = secrets.token_hex(2).upper()
    return f"Simulation #{suffix}"
