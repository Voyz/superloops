import logging
import random
import time
from unittest.mock import MagicMock

from superloops import SuperLoop

logging.basicConfig(level = logging.INFO)

Api = MagicMock()
Api.return_value.get_feed = MagicMock(side_effect=lambda: random.randint(1,100))
my_key = 'SECRET_KEY'

class ApiFeedLoop(SuperLoop):
    def on_start(self):
        self.api = Api(key=my_key)
        return True

    def on_stop(self):
        self.api.disconnect()

    def cycle(self):
        feed = self.api.get_feed()
        print(f'Api feed: {feed}')
        time.sleep(1)


api_feed_loop = ApiFeedLoop()

api_feed_loop.start()
# ApiFeedLoop_0: Started

time.sleep(5)
# Api feed: 18
# Api feed: 41
# Api feed: 98
# Api feed: 7
# Api feed: 39

api_feed_loop.stop()
# ApiFeedLoop_0: Stopping
# ApiFeedLoop_0: Exited gracefully, running=False, killed=False