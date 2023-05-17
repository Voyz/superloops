import logging
import time

from superloops import SuperLoop, LoopController

logging.basicConfig(level=logging.INFO)

_LOGGER = logging.getLogger("multiple_threads")


class GoodLoop(SuperLoop):
    def cycle(self):
        time.sleep(1)
        _LOGGER.info(f"{self.thread_name} - processing")


class BadLoop(SuperLoop):
    def cycle(self):
        time.sleep(1)
        _LOGGER.info(f"{self.thread_name} - processing, failures={self._failures}")
        self.failure()


loop_controller = LoopController()
good_loop = loop_controller.new_loop(GoodLoop())
bad_loop = loop_controller.new_loop(BadLoop(max_loop_failures=3))  # will propagate its health after 3 failures

loop_controller.start()
loop_controller.maintain_loops()

_LOGGER.info("WAITING FOR FAILURE PROPAGATION")

# wait until the first failure propagation
while loop_controller.green_light.is_set():
    time.sleep(0.1)
    loop_controller.maintain_loops()

while not loop_controller.green_light.is_set():
    time.sleep(0.1)

_LOGGER.info("RESTART COMPLETE, SHUTTING DOWN")

loop_controller.stop()
loop_controller.stop_loops()
