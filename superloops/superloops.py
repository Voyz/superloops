import logging
import threading
from abc import abstractmethod, ABC

_LOGGER = logging.getLogger('superloops')


class GreenLight(threading.Event):
    """ Indicates 'healthy' state amongst all loops managed by the LoopController. """

    def clear(self):
        if not self.is_set():
            _LOGGER.debug(f'GreenLight: Reset from {threading.current_thread().name} ignored, already resetting.')
        else:
            _LOGGER.debug(f'GreenLight: Reset initialised from {threading.current_thread().name}.')
            super().clear()

class SuperLoop(ABC):
    """
    SuperLoop is an abstract base class that provides a foundation for implementing threaded cyclic functionality with built-in support for failure handling, health propagation and graceful termination.

    This class should be inherited by other classes that want to utilize these capabilities, extending the 'cycle' method which will be called on every cycle of the loop.

    SuperLoops are expected to be managed by a LoopController.

    A number of event callbacks can also be implemented:

    * on_start - Called before new thread is created and started. Must return a boolean indicating whether loop should continue starting.
    * on_stop -  Called after the thread is stopped.
    * on_thread_start - Called from within the thread before starting the loop.
    * on_thread_stop - Called from within the thread after stopping the loop.

    Attributes:
        green_light (threading.Event): A threading.Event object representing the healthy state of the loop. If not provided, this loop cannot propagate its health status to other loops.
        grace_period (int): The number of seconds to wait when stopping the loop gracefully. Default is 5 seconds.
        max_loop_failures (int): The maximum number of failures allowed before reporting issues. Default is 10 failures.
        reset_globally (bool): A flag that indicates if this loop should be reset when other loops report issues. Default is True.

    Example:
        class CustomLoop(SuperLoop):
            def cycle(self):
                # Implement custom loop functionality
                pass
    """


    def __init__(self,
                     green_light:threading.Event=None,
                     grace_period:int=5,
                     max_loop_failures:int=10,
                     reset_globally:bool=True):

            self._running = False
            self._thread = None
            self._failures = 0
            self._killed_thread = {}
            self._thread_index = 0
            self._operational_lock = threading.Lock()

            self._green_light = green_light
            self._grace_period = grace_period
            self._max_loop_failures = max_loop_failures
            self.reset_globally = reset_globally

    @abstractmethod
    def cycle(self):
        raise NotImplementedError()

    def on_start(self, *args, **kwargs) -> bool:
        """ Called before new thread is created and started. Must return a boolean indicating whether loop should continue starting. """
        return True

    def on_stop(self, *args, **kwargs):
        """ Called after the thread is stopped. """
        pass

    def on_thread_start(self):
        """ Called from within the thread before starting the loop. """
        pass

    def on_thread_stop(self):
        """ Called from within the thread after stopping the loop. """
        pass

    def start(self, *args, **kwargs):
        with self._operational_lock:
            if self.is_alive or self._running: # we can only start if not currently running
                return

            self._running = True

            try:
                continue_starting = self.on_start(*args, **kwargs)
            except Exception as e:
                _LOGGER.exception(f'Exception running on_start of {self}: {e}')
                continue_starting = True

            if not continue_starting:
                _LOGGER.info(f'{self} on_start returned False, stopping')
                self._running = False
                return

            self._start_new_thread()

    def _start_new_thread(self):
        name = self.make_name(self._thread_index)
        self._thread_index += 1
        self._thread = threading.Thread(
            target=self._start_thread, name=name, args=(name,)
        )
        self._thread.daemon = True
        self._thread.start()

    def _start_thread(self, thread_name:str):
        _LOGGER.info(f'{thread_name}: Started')

        try:
            self.on_thread_start()
        except Exception as e:
            _LOGGER.exception(f'{thread_name}: Exception during on_thread_start, exiting: {e}')
            return

        self._loop(thread_name)

        try:
            self.on_thread_stop()
        except Exception as e:
            _LOGGER.exception(f'{thread_name}: Exception during shutdown on_thread_stop: {e}')

        _LOGGER.info(f'{thread_name}: Exited gracefully, running={self._running}, killed={self._killed_thread.get(thread_name, False)}')

    def _loop(self, thread_name:str):
        while self._running and not self._killed_thread.get(thread_name, False):
            self.cycle()

    def stop(self, *args, **kwargs) -> bool:
        """ Attempt to stop the thread, waiting up to 'grace_period' seconds for it to stop. """

        if self._thread is not None:
            with self._operational_lock:
                _LOGGER.info(f'{self.thread_name}: Stopping')
                self._running = False

                try:
                    self.on_stop(*args, **kwargs)
                except Exception as e:
                    _LOGGER.exception(f'Exception running on_start of {self}: {e}')

                if threading.current_thread() == self._thread:
                    _LOGGER.info(f'Cannot stop {threading.current_thread().name} from within itself.~~')
                else:
                    self._thread.join(timeout=self._grace_period)

                stopped = not self.is_alive
                self._thread = None
                return stopped

    def hard_reset(self):
        if self._thread is not None:
            name = self.make_name(self._thread_index-1)
            _LOGGER.info(f'{self.thread_name}: Hard reset')
            stopped = self.stop()
            with self._operational_lock:
                self._killed_thread[name] = True
                if not stopped:
                    _LOGGER.info(f'{self.thread_name} Unable to stop')

            self._running = True
            self._start_new_thread()

    def failure(self):
        """ Allows to mark the thread's state as non-healthy. If this happens more times than 'max_loop_failures', the loop will attempt to stop its thread, and propagate the information about lack of health to other threads through the LoopController, which should cause all threads to reset. """

        self._failures += 1

        if self._failures > self._max_loop_failures:
            _LOGGER.info(
                f'{str(self)}: Exceeded maximum number of failures ({self._failures}/{self._max_loop_failures}), terminating.')
            self._failures = 0
            if self._green_light is not None:
                self._green_light.clear()
            self.stop()
            return True
        return False

    @property
    def is_alive(self) -> bool:
        """Returns True if the background thread is running."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def running(self) -> bool:
        """Returns True if the loop is running."""
        return self._running

    def make_name(self, thread_index:int):
        return f'{self.__class__.__qualname__}_{thread_index}'

    @property
    def thread_name(self) -> str:
        return self._thread.name if self._thread is not None else str(self)

    def __str__(self):
        return f'{self.__class__.__qualname__}'



class LoopController(SuperLoop):
    """
    LoopController is a class that provides a convenient way to manage and maintain multiple SuperLoops. It offers functionality to add, start, maintain, stop, and reset loops while also managing a global GreenLight Event for signaling the healthy state of the system.

    All loops managed by one LoopController are bundled together using one GreenLight Event. When set, it indicates all loops are healthy. When unset, it indicates that a reset is necessary. All loops that have 'reset_globally' set to True will be reset upon observing an unhealthy state of the system (represented by an unset GreenLight Event).

    Attributes:
        reset_callback (callable): A callable to be executed when the LoopController is reset.

    Example:
        loop_controller = LoopController()
        my_super_loop = MySuperLoop()
        loop_controller.new_loop(my_super_loop)

        loop_controller.start()
    """
    def __init__(self, reset_callback:callable, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._green_light = GreenLight()
        self._green_light.set()
        self.loops = []
        self._reset_callback = reset_callback

    @property
    def green_light(self):
        return self._green_light

    def new_loop(self, loop:SuperLoop):
        self.loops.append(loop)
        return loop

    def _reset(self):
        _LOGGER.info(f'{self}: Stopping loops')

        for loop in self.loops:
            if loop.reset_globally:
                loop.stop()

        _LOGGER.info(f'{self}: Resetting')

        if self._reset_callback is not None and callable(self._reset_callback):
            self._reset_callback()


        _LOGGER.info(f'{self}: Restarting loops')
        for loop in self.loops:
            if loop.reset_globally:
                if loop.is_alive or loop.running:
                    loop.hard_reset()
                else:
                    loop.start()

        self._green_light.set()
        _LOGGER.info(f'{self}: Restart completed')


    def cycle(self):
        if not self._green_light.is_set():
            _LOGGER.info(f'{self}: green light is not set, resetting.')
            self._reset()


    def maintain_loop(self, loop:SuperLoop):
        try:
            if not loop.is_alive:
                _LOGGER.debug(f"{loop} is stopped, attempting to start")
                loop.start()
        except Exception as e:
            _LOGGER.exception(f'Exception maintaining {loop}~~: {e}')

    def stop_loop(self, loop:SuperLoop):
        try:
            loop.stop()
        except Exception as e:
            _LOGGER.exception(f'Exception stopping {loop}~~: {e}')



    def __str__(self):
        return f"{self.__class__.__qualname__}"
