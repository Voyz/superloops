# SuperLoops

SuperLoops is a package that provides a foundation for implementing threaded cyclic functionality with built-in support for failure handling, health propagation, and graceful termination.

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