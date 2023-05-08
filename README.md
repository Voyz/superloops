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

```python
class ProcessLoop(SuperLoop):
    def cycle(self):
        # process stuff in a separate thread

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


In summary, SuperLoops provide support for thread maintenance, events, failure handling, health status propagation, and graceful termination.


## <a name="how-superloops-works"></a>How does SuperLoops work?

SuperLoop is a class that wraps around a Python `threading.Thread` object. It exposes an interface for thread starting, stopping, hard restarts, graceful termination and events: `on_start`, `on_stop`, `on_thread_start` and `on_thread_stop`.

Each time you restart a SuperLoop, it will create a new Thread, handling naming and graceful termination for you.

Aided by the LoopController class, the SuperLoops are able to communicate their health between each other. This ensures that should one SuperLoop fail and need restarting, all other connected SuperLoops would be restarted too.


## Licence

See [LICENSE](https://github.com/Voyz/superloops/blob/master/LICENSE)

# Disclaimer

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