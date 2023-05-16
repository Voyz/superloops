*This library is currently being beta-tested. See something that's broken? Did we get something
wrong? [Create an issue and let us know!][issues]*

<p align="center">
    <a id="superloops" href="#superloops">
        <img src="https://github.com/Voyz/superloops/blob/master/media/superloops_logotype_A01.png" alt="SuperLoops logo" title="SuperLoops logo" width="400"/>
    </a>
</p>

<p align="center">
    <a href="https://opensource.org/licenses/Apache-2.0">
        <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"/> 
    </a>
    <a href="https://github.com/Voyz/superloops/releases">
        <img src="https://img.shields.io/pypi/v/superloops?label=version"/> 
    </a>
</p>

```posh
pip install superloops
```


SuperLoops package simplifies and augments usage of Python threads.

Features:

* Startup, shutdown, hard reset
* Thread events
* Co-dependant thread health propagation
* 0 dependencies
* 100% automated test coverage

```python
class ProcessLoop(SuperLoop):
    def cycle(self):
        # process stuff in a separate thread

loop = ProcessLoop()
loop.start()
# ProcessLoop_0: Started 

loop.stop()
# ProcessLoop_0: Exited gracefully

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
# LoopController_0: Started

loop_controller.maintain_loops()
# ProcessLoop_0: Started
# ApiFeedLoop_0: Started

api_feed_loop.failure() # oops!

# LoopController_0: Stopping loops.
# ProcessLoop_0: Exited gracefully
# ApiFeedLoop_0: Exited gracefully

# LoopController_0: Restarting loops.
# ProcessLoop_1: Started
# ApiFeedLoop_1: Started
```


In summary, SuperLoops provide support for thread maintenance, events, failure handling, health status propagation, and graceful termination.


## <a name="how-superloops-works"></a>How does SuperLoops work?

SuperLoop is a class that wraps around a Python `threading.Thread` object. It exposes an interface for thread starting, stopping, hard restarts, graceful termination and events: `on_start`, `on_stop`, `on_thread_start` and `on_thread_stop`.

Each time you restart a SuperLoop, it will create a new Thread, handling naming and graceful termination for you.

Aided by the LoopController class, the SuperLoops are able to communicate their health between each other. This ensures that should one SuperLoop fail and need restarting, all other connected SuperLoops would be restarted too.

## Documentation 


To use a SuperLoop, declare a class inheriting from SuperLoop and extend the `cycle` method
```python
from superloops import SuperLoop

class MyLoop(SuperLoop):
    def cycle(self):
        pass
        # process stuff

loop = MyLoop()
```

You can use the following methods of SuperLoop to control the thread lifecycle.

```python
loop.start()
loop.stop()
loop.hard_reset()
loop.failure()
```

#### `start()`
Start a new thread (unless one is already started) that will be used to operate the loop. This will start calling the overridden `cycle()` method indefinitely on the new thread. Any arguments passed to this method will be passed to the `on_start` callback.

#### `stop()`
Stop the existing thread (unless there isn't one started) and join the thread, waiting up to the amount of seconds specified by the `grace_period` argument of this class. Any arguments passed to this method will be passed to the `on_stop` callback.

#### `hard_reset()`
Stop the thread by calling `stop()` method and mark it as killed, attempting to gracefully finish as soon as the control is returned from the `cycle()` method. Independently of whether the current thread stops gracefully, a new thread will be instantly started.

#### `failure()`
Indicate that there has been a critical failure in the operation of the thread. If the amount of failures exceeds `max_loop_failures` specified as the argument of this class, the thread will stop and (if provided) unset its GreenLight. 

That indicates that the health status should be propagated across other threads managed through the LoopController that this loop belongs to, and that all specified threads should be restarted.

#### SuperLoop arguments

* `green_light` (`threading.Event`): A `threading.Event` object representing the health state of the loop. It gets set automatically when a loop is added to LoopController.
* `grace_period` (`int`): The number of seconds to wait when stopping the loop gracefully. Default is 5 seconds.
* `max_loop_failures` (`int`): The maximum number of failures allowed before reporting issues. Default is 10 failures.
* `stop_on_failure` (`bool`): A flag that indicates if this loop should be stopped when it exceeds its `max_loop_failures`. Default is `False`.
* `reset_globally` (`bool`): A flag that indicates if this loop should be reset when other loops report issues. Default is `True`.

### Events

SuperLoop provides lifecycle event callbacks that facilitate flexibility in managing the loop and its thread.

#### on_start

The `on_start` callback is invoked before a new thread is created and started. It can be used to perform any setup that is required before the loop starts running.

This method must return a boolean indicating whether the loop should continue starting.


#### on_stop

The `on_stop` callback is invoked after the loop's thread is stopped. This method can be used to perform any cleanup that is required after the loop has stopped running.

#### on_thread_start

The `on_thread_start` callback is invoked from within the loop's thread before the loop starts running. This method can be used to perform any setup that must be done within the context of the loop's thread.

#### on_thread_stop

The `on_thread_stop` callback is invoked from within the loop's thread after the loop has stopped running. This method can be used to perform any cleanup that must be done within the context of the loop's thread.

Example:

```python
def thread_name():
    return threading.current_thread().name

class MyLoop(SuperLoop):
    def on_start(self):
        print(f'on_start - {thread_name()}')
        # Perform any necessary setup here
        return True  # Return False to prevent the loop from starting
    
    def on_stop(self):
        print(f'on_stop - {thread_name()}')
        # Perform any necessary cleanup here

    def on_thread_start(self):
        print(f'on_thread_start - {thread_name()}')
        # Perform any necessary setup here

    def on_thread_stop(self):
        print(f'on_thread_stop - {thread_name()}')
        # Perform any necessary cleanup here
    
    def cycle(self):
        pass

loop = MyLoop()

loop.start()
# on_start - MainThread
# on_thread_start - MyLoop_0
loop.stop()
# on_stop - MainThread
# on_thread_stop - MyLoop_0
```

### Loop Controller

SuperLoops are built with the intent of being able to link multiple threads into a single co-dependant system. If one thread in such system fails, all threads can be restarted allowing for an easy way to ensure multiple sub-systems can recover from a failure.

This is executed by adding various SuperLoops to a LoopController class, calling the `LoopController.new_loop()` method, passing the SuperLoop as the argument.


LoopController needs to be started, which will launch a separate thread observing for the health status of all the threads.

```python
loop_controller = LoopController()

process_loop = loop_controller.new_loop(ProcessLoop())
api_feed_loop = loop_controller.new_loop(ApiFeedLoop())

loop_controller.start()
```

For convenience, LoopController can also ensure that all its SuperLoops are started, by calling `maintain_loops`, or stopped by calling `stop_loops`.

```python
loop_controller.maintain_loops()
loop_controller.stop_loops()
```

#### LoopController arguments
* `reset_callback` (`callable`): A callable to be executed when the `LoopController` resets loops.
* `green_light` (`threading.Event`): A `threading.Event` that will be used to control the health status of the loops. Creates one if not provided.

## Examples

See [Usage examples](https://github.com/Voyz/superloops/tree/master/bin/examples) for more.

## Licence

See [LICENSE](https://github.com/Voyz/superloops/blob/master/LICENSE)

## Disclaimer

SuperLoops is provided on an AS IS and AS AVAILABLE basis without any representation or endorsement made and without warranty of any kind whether express or implied, including but not limited to the implied warranties of satisfactory quality, fitness for a particular purpose, non-infringement, compatibility, security and accuracy. To the extent permitted by law, SuperLoops' authors will not be liable for any indirect or consequential loss or damage whatever (including without limitation loss of business, opportunity, data, profits) arising out of or in connection with the use of SuperLoops. SuperLoops' authors make no warranty that the functionality of SuperLoops will be uninterrupted or error free, that defects will be corrected or that SuperLoops or the server that makes it available are free of viruses or anything else which may be harmful
or destructive.


## Built by Voy

Hi! Thanks for checking out and using this library. If you are interested in discussing your project, require
mentorship, consider hiring me, or just wanna chat - I'm happy to talk.

You can send me an email to get in touch: hello@voyzan.com

Or if you'd just want to give something back, I've got a Buy Me A Coffee account:

<a href="https://www.buymeacoffee.com/voyzan" rel="nofollow">
    <img src="https://raw.githubusercontent.com/Voyz/voyz_public/master/vz_BMC.png" alt="Buy Me A Coffee" style="max-width:100%;" width="192">
</a>

Thanks and have an awesome day 👋


[issues]: https://github.com/Voyz/superloops/issues