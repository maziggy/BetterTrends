import asyncio
import time

async def fetch_entity_states(entity_ids, get_interval, get_steps):
    """
    Fetch the states of entities at a dynamically defined interval.

    Args:
        entity_ids (list): List of entity IDs to fetch.
        get_interval (callable): Function to fetch the interval dynamically.
        get_steps (callable): Function to fetch the steps dynamically.
    """
    last_fetch_time = time.time()  # Track the last fetch time

    while True:
        # Dynamically fetch the interval and steps
        interval = get_interval()  # Get the interval value
        steps = get_steps()  # Get the steps value

        # Log the current interval and steps for debugging
        print(f"Using interval: {interval}s and steps: {steps}")

        # Fetch the states for `steps` entities
        print(f"Fetching states for entities: {entity_ids[:steps]}")
        for entity in entity_ids[:steps]:
            print(f"Fetching state for {entity}")
            await asyncio.sleep(0.1)  # Simulate network delay per entity

        # Calculate the time to sleep to respect the interval
        elapsed_time = time.time() - last_fetch_time
        sleep_time = max(0, interval - elapsed_time)

        # Log timing details for debugging
        print(f"Elapsed time: {elapsed_time:.2f}s, Sleeping for: {sleep_time:.2f}s")

        # Wait for the remaining time to complete the interval
        await asyncio.sleep(sleep_time)

        # Update the last fetch time
        last_fetch_time = time.time()


class EntityStateSimulator:
    def __init__(self, interval=60, steps=10):
        self._interval = interval
        self._steps = steps

    def get_interval(self):
        # Simulate getting the interval from an entity
        return self._interval

    def get_steps(self):
        # Simulate getting the steps from an entity
        return self._steps

    def update_interval(self, new_interval):
        # Update the interval dynamically
        self._interval = new_interval
        print(f"Updated interval to: {new_interval}s")

    def update_steps(self, new_steps):
        # Update the steps dynamically
        self._steps = new_steps
        print(f"Updated steps to: {new_steps}")


async def update_simulator(simulator):
    """
    Simulate dynamic updates to the simulator's interval and steps.
    """
    await asyncio.sleep(10)  # Wait 10 seconds
    simulator.update_interval(20)  # Change interval to 20s
    simulator.update_steps(3)  # Change steps to 3
    await asyncio.sleep(15)  # Wait 15 seconds
    simulator.update_interval(15)  # Change interval to 15s
    simulator.update_steps(2)  # Change steps to 2


async def main():
    # Simulate entity states with dynamic state management
    simulator = EntityStateSimulator(interval=30, steps=5)
    entity_ids = ["sensor.growbox_temperature", "sensor.growbox_humidty", "sensor.growbox_vpd"]

    # Run both fetch and update tasks concurrently
    fetch_task = asyncio.create_task(fetch_entity_states(
        entity_ids=entity_ids,
        get_interval=simulator.get_interval,
        get_steps=simulator.get_steps
    ))
    update_task = asyncio.create_task(update_simulator(simulator))

    await asyncio.gather(fetch_task, update_task)


if __name__ == "__main__":
    asyncio.run(main())
    