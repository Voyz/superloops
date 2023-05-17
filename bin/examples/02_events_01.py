import threading

from superloops import SuperLoop


def thread_name():
    return threading.current_thread().name


class MyLoop(SuperLoop):
    def on_start(self):
        print(f"on_start - {thread_name()}")
        # Perform any necessary setup here
        return True  # Return False to prevent the loop from starting

    def on_stop(self):
        print(f"on_stop - {thread_name()}")
        # Perform any necessary cleanup here

    def on_thread_start(self):
        print(f"on_thread_start - {thread_name()}")
        # Perform any necessary setup here

    def on_thread_stop(self):
        print(f"on_thread_stop - {thread_name()}")
        # Perform any necessary cleanup here

    def cycle(self):
        pass


loop = MyLoop()

loop.start()
loop.stop()
