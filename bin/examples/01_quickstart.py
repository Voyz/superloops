import time

from superloops import SuperLoop


class ProcessLoop(SuperLoop):
    def cycle(self):
        print(f'Processing...')
        time.sleep(1)
        # process stuff in a separate thread

loop = ProcessLoop()
loop.start()
# ProcessLoop0: Started

time.sleep(5)
# Processing...
# Processing...
# Processing...
# Processing...
# Processing...

loop.stop()
# ProcessLoop0: Exited gracefully