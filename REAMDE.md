# SuperLoops

SuperLoops package simplifies and augments usage of Python threads. 

```python
class ProcessLoop(SuperLoop):
    def cycle(self):
        # process stuff

loop = ProcessLoop()
loop.start()
# ProcessLoop0: Started 

loop.stop()
# ProcessLoop0: Exited gracefully

loop.hard_reset() # when nothing else helps 😬 
```

Thread events?

```python
class ApiFeedLoop(SuperLoop):
    def on_start(self):
        self.api = Api(key=my_key)
        
    def on_stop(self):
        self.api.disconnect()
        
    def cycle(self):
        self.api.get_feed()

    # on_thread_start, on_thread_stop...
```

Multiple threads that need to stay healthy?

```python
loop_controller = LoopController()

process_loop = loop_controller.new_loop(ProcessLoop())
api_feed_loop = loop_controller.new_loop(ApiFeedLoop())

loop_controller.start()
# LoopController0: Started

loop_controller.maintain_loops()
# ProcessLoop0: Started
# ApiFeedLoop0: Started

api_feed_loop.failure() # oops!

# LoopController0: Stopping loops.
# ProcessLoop0: Exited gracefully
# ApiFeedLoop0: Exited gracefully

# LoopController0: Restarting loops.
# ProcessLoop1: Started
# ApiFeedLoop1: Started
```


In summary, SuperLoops provide support for maintenance, events, failure handling, health status propagation, and graceful termination.

## Installation

To install SuperLoops, run the following command:

```posh
pip install superloops
```


## Usage

Here is a simple example demonstrating how to use SuperLoops:

```python
from superloops import SuperLoop, GreenLight, LoopController

class CustomLoop(SuperLoop):
    def cycle(self):
        # Implement custom loop functionality
        pass


loop_controller = LoopController(reset_callback=None)
green_light = loop_controller.green_light
loop1 = CustomLoop(green_light=green_light)
loop2 = CustomLoop(green_light=green_light)

loop_controller.new_loop(loop1)
loop_controller.new_loop(loop2)

loop_controller.start()
```


# License
This project is licensed under the MIT License.

# Disclaimer

This software is provided "as-is" without warranty of any kind. Use at your own risk. The authors are not responsible for any damage or data loss caused by using this software.