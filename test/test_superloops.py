import logging
import time
import unittest
from threading import Event
from unittest.mock import MagicMock, PropertyMock, Mock

from superloops import GreenLight, SuperLoop, LoopController, super_loop_factory


class TestGreenLight(unittest.TestCase):

    def test_green_light_clear(self):
        green_light = GreenLight()
        green_light.set()
        self.assertTrue(green_light.is_set())

        green_light.clear()
        self.assertFalse(green_light.is_set())

        green_light.clear()
        self.assertFalse(green_light.is_set(), "GreenLight should still be unset")


class TestSuperLoop(unittest.TestCase):

    class CustomLoop(SuperLoop):
        def cycle(self):
            pass

    def setUp(self):
        green_light = GreenLight()
        green_light.set()
        self.loop = self.CustomLoop(green_light=green_light)

    def test_super_loop_start_stop(self):


        self.loop.start()
        self.assertTrue(self.loop.is_alive, "Loop should be alive after start")

        self.loop.stop()
        self.assertFalse(self.loop.is_alive, "Loop should not be alive after stop")

    def test_start_loop_twice(self):
        self.loop.on_start = MagicMock(return_value=True)

        self.loop.start()
        self.assertTrue(self.loop.is_alive, "Loop should be alive after start")

        self.loop.start()
        self.assertTrue(self.loop.is_alive, "Loop should still be alive after trying to start again")
        self.loop.on_start.assert_called_once()  # Verify on_start was called only once

        self.loop.stop()
        self.assertFalse(self.loop.is_alive, "Loop should not be alive after stop")

    def test_on_start(self):
        self.loop.on_start = MagicMock(return_value=True)
        self.loop.start()
        self.loop.on_start.assert_called_once()
        self.loop.stop()

    def test_on_stop(self):
        self.loop.on_stop = MagicMock()
        self.loop.start()
        self.loop.stop()
        self.loop.on_stop.assert_called_once()

    def test_on_thread_start(self):
        self.loop.on_thread_start = MagicMock()
        self.loop.start()
        while not self.loop.is_alive:
            time.sleep(0.1)
        self.loop.on_thread_start.assert_called_once()
        self.loop.stop()

    def test_on_thread_stop(self):
        self.loop.on_thread_stop = MagicMock()
        self.loop.start()
        self.loop.stop()
        self.loop.on_thread_stop.assert_called_once()


    def test_on_start_exception(self):
        self.loop.on_start = MagicMock(side_effect=Exception("Test on_start exception"))
        self.loop._start_new_thread = MagicMock()
        with self.assertLogs(logging.getLogger('superloops'), level='ERROR') as cm:
            self.loop.start()
            self.loop.stop()

        expected_log = "Exception running on_start of TestSuperLoop.CustomLoop: Test on_start exception"
        self.assertEqual(expected_log, cm.records[0].msg)
        self.loop._start_new_thread.assert_called_once()

    def test_on_stop_exception(self):
        self.loop.on_stop = MagicMock(side_effect=Exception("Test on_stop exception"))
        with self.assertLogs(logging.getLogger('superloops'), level='ERROR') as cm:
            self.loop.start()
            self.loop.stop()

        expected_log = "Exception running on_stop of TestSuperLoop.CustomLoop: Test on_stop exception"
        self.assertEqual(expected_log, cm.records[0].msg)

    def test_on_thread_start_exception(self):
        self.loop.on_thread_start = MagicMock(side_effect=Exception("Test on_thread_start exception"))
        self.loop._loop = MagicMock()
        with self.assertLogs(logging.getLogger('superloops'), level='ERROR') as cm:
            self.loop.start()
            self.loop.stop()

        expected_log = "TestSuperLoop.CustomLoop_0: Exception during on_thread_start, exiting: Test on_thread_start exception"
        self.assertEqual(expected_log, cm.records[0].msg)
        self.loop._loop.assert_not_called()

    def test_on_thread_stop_exception(self):
        self.loop.on_thread_stop = MagicMock(side_effect=Exception("Test on_thread_stop exception"))
        with self.assertLogs(logging.getLogger('superloops'), level='ERROR') as cm:
            self.loop.start()
            self.loop.stop()

        expected_log = "TestSuperLoop.CustomLoop_0: Exception during shutdown on_thread_stop: Test on_thread_stop exception"
        self.assertEqual(expected_log, cm.records[0].msg)

    def test_on_start_returns_false(self):
        self.loop.on_start = MagicMock(return_value=False)
        self.loop._start_new_thread = MagicMock()
        with self.assertLogs(logging.getLogger('superloops'), level='INFO') as cm:
            self.loop.start()
            self.loop.stop()

        expected_log = "TestSuperLoop.CustomLoop on_start returned False, stopping"
        self.assertEqual(expected_log, cm.records[0].msg)
        self.assertFalse(self.loop.running)
        self.loop._start_new_thread.assert_not_called()

    def test_hard_reset_stop_returns_true(self):
        self.loop.start()
        temp_stop = self.loop.stop
        self.loop.stop = MagicMock(return_value=True)
        self.loop._start_new_thread = MagicMock()
        self.loop.hard_reset()

        self.loop._start_new_thread.assert_called_once()
        thread_name = self.loop.thread_name
        self.assertTrue(self.loop._killed_thread[thread_name])
        temp_stop()

    def test_hard_reset_stop_returns_false(self):
        self.loop.start()
        temp_stop = self.loop.stop
        self.loop.stop = MagicMock(return_value=False)
        self.loop._start_new_thread = MagicMock()
        with self.assertLogs(logging.getLogger('superloops'), level='INFO') as cm:
            self.loop.hard_reset()

        thread_name = self.loop.thread_name

        expected_log = f'{thread_name} Unable to stop'
        self.assertEqual(expected_log, cm.records[1].msg)

        self.loop._start_new_thread.assert_called_once()
        self.assertTrue(self.loop._killed_thread[thread_name])
        temp_stop()

    def test_failure_no_exceed_max_failures(self):
        self.loop._max_loop_failures = 3
        for i in range(2):
            self.assertFalse(self.loop.failure())
        self.assertEqual(self.loop._failures, 2)

    def test_failure_exceed_max_failures(self):
        self.loop._max_loop_failures = 3
        self.loop.stop = MagicMock()
        for i in range(4):
            self.loop.failure()
        self.loop.stop.assert_not_called()
        self.assertEqual(self.loop._failures, 0)

    def test_failure_exceed_max_failures_stop(self):
        self.loop._stop_on_failure = True
        self.loop._max_loop_failures = 3
        self.loop.stop = MagicMock()
        for i in range(4):
            self.loop.failure()
        self.loop.stop.assert_called_once()
        self.assertEqual(self.loop._failures, 0)

    def test_failure_exceed_max_failures_stop_clear_green_light(self):
        self.loop._stop_on_failure = True
        self.loop._max_loop_failures = 3
        self.loop.stop = MagicMock()
        for i in range(4):
            self.loop.failure()
        self.loop.stop.assert_called_once()
        self.assertEqual(self.loop._failures, 0)
        self.assertFalse(self.loop._green_light.is_set())

class TestLoopController(unittest.TestCase):

    class CustomLoop(SuperLoop):
        def cycle(self):
            pass

    def reset_callback(self):
        pass

    def setUp(self):
        self.reset_callback = MagicMock()
        self.controller = LoopController(self.reset_callback)
        self.loop1 = self.CustomLoop()
        self.loop2 = self.CustomLoop()
        self.controller.new_loop(self.loop1)
        self.controller.new_loop(self.loop2)



    def test_loop_controller(self):
        self.controller.new_loop(self.loop1)

        self.controller.start()
        self.assertFalse(self.loop1.is_alive, "Custom loop should not be alive after loop_controller starts")

        self.controller.maintain_loop(self.loop1)
        self.assertTrue(self.loop1.is_alive, "Custom loop should be alive after loop_controller maintains it")

        self.controller.stop_loop(self.loop1)
        self.assertFalse(self.loop1.is_alive, "Custom loop should not be alive after loop_controller stops it")



    # Add the new tests here
    def test_reset_all_loops_stop_reset_restart(self):
        self.loop1.stop = MagicMock(return_value=True)
        self.loop1.start = MagicMock()
        self.loop2.stop = MagicMock(return_value=True)
        self.loop2.start = MagicMock()

        self.controller._reset()

        self.loop1.stop.assert_called_once()
        self.loop1.start.assert_called_once()
        self.loop2.stop.assert_called_once()
        self.loop2.start.assert_called_once()
        self.reset_callback.assert_called_once()

    def test_reset_loop_fails_to_stop_hard_reset(self):
        self.loop1.stop = MagicMock(return_value=False)
        self.loop1.hard_reset = MagicMock()
        self.loop2.stop = MagicMock(return_value=True)
        self.loop2.start = MagicMock()

        self.loop1._running = True
        self.loop2._running = False
        self.controller._reset()

        self.loop1.stop.assert_called_once()
        self.loop1.hard_reset.assert_called_once()
        self.loop2.stop.assert_called_once()
        self.loop2.start.assert_called_once()
        self.reset_callback.assert_called_once()

    def test_reset_callback_raises_exception(self):
        self.reset_callback.side_effect = Exception("Reset callback exception")

        self.loop1.stop = MagicMock(return_value=True)
        self.loop1.start = MagicMock()
        self.loop2.stop = MagicMock(return_value=True)
        self.loop2.start = MagicMock()

        with self.assertLogs(logging.getLogger('superloops'), level='ERROR') as cm:
            self.controller._reset()

            self.loop1.stop.assert_called_once()
            self.loop1.start.assert_called_once()
            self.loop2.stop.assert_called_once()
            self.loop2.start.assert_called_once()

            self.assertEqual("Exception during reset_callback: Reset callback exception", cm.records[0].msg)

    def test_cycle_green_light_set(self):
        self.controller._reset = MagicMock()
        self.controller._green_light.set()
        with self.assertRaises(AssertionError) as ar, \
                self.assertLogs(logging.getLogger('superloops'), level='INFO') as cm:
            self.controller.cycle()

            self.assertEqual(0, len(cm.records))
            self.controller._reset.assert_not_called()
        self.assertEqual('no logs of level INFO or higher triggered on superloops', str(ar.exception))

    def test_cycle_green_light_not_set(self):
        self.controller._green_light.clear()
        self.controller._reset = MagicMock()
        with self.assertLogs(logging.getLogger('superloops'), level='INFO') as cm:
            self.controller.cycle()

            self.assertEqual("LoopController: green light is not set, resetting.", cm.records[0].msg)
            self.controller._reset.assert_called_once()

    def test_maintain_loop_alive(self):
        type(self.loop1).is_alive = PropertyMock(return_value=True)
        self.loop1.start = MagicMock()

        self.controller.maintain_loop(self.loop1)

        self.loop1.start.assert_not_called()

    def test_maintain_loop_not_alive(self):
        type(self.loop1).is_alive = PropertyMock(return_value=False)
        self.loop1.start = MagicMock()

        self.controller.maintain_loop(self.loop1)

        self.loop1.start.assert_called_once()

    def test_stop_loop(self):
        self.loop1.stop = MagicMock()

        self.controller.stop_loop(self.loop1)

        self.loop1.stop.assert_called_once()

    def test_maintain_loop_start_exception(self):
        type(self.loop1).is_alive = PropertyMock(return_value=False)
        self.loop1.start = MagicMock(side_effect=Exception('start exception'))

        with self.assertLogs(logging.getLogger('superloops'), level='ERROR') as cm:
            self.controller.maintain_loop(self.loop1)

            self.assertEqual("Exception maintaining TestLoopController.CustomLoop~~: start exception", cm.records[0].msg)

    def test_stop_loop_exception(self):
        self.loop1.stop = MagicMock(side_effect=Exception('stop exception'))

        with self.assertLogs(logging.getLogger('superloops'), level='ERROR') as cm:
            self.controller.stop_loop(self.loop1)

            self.assertEqual("Exception stopping TestLoopController.CustomLoop~~: stop exception", cm.records[0].msg)


    def test_new_from_factory(self):
        loop1 = MagicMock(spec=SuperLoop)
        mock_factory = MagicMock(return_value=loop1)
        self.controller.set_loop_factory(mock_factory)
        created_loop = self.controller.new_from_factory(self.CustomLoop, use_green_light=False)

        mock_factory.assert_called_once_with(self.CustomLoop, None, None, None, None, None)
        self.assertEqual(created_loop, loop1, "new_from_factory should return the loop created by the factory")
        loop1.set_green_light.assert_not_called()

    def test_new_from_factory_with_green_light(self):
        loop1 = MagicMock(spec=SuperLoop)
        mock_factory = MagicMock(return_value=loop1)
        self.controller.set_loop_factory(mock_factory)
        created_loop = self.controller.new_from_factory(self.CustomLoop, use_green_light=True)

        mock_factory.assert_called_once_with(self.CustomLoop, None, None, None, None, None)
        self.assertEqual(created_loop, loop1, "new_from_factory should return the loop created by the factory")
        self.assertIn(loop1, self.controller.loops, "The loop should be added to the controller's loop list when use_green_light is True")
        loop1.set_green_light.assert_called()


    def test_set_loop_factory(self):
        mock_factory = MagicMock()
        self.controller.set_loop_factory(mock_factory)
        self.assertEqual(self.controller._loop_factory, mock_factory, "set_loop_factory should set the controller's loop factory to the provided factory")


class TestSuperLoopSelfStop(unittest.TestCase):

    class CustomLoop(SuperLoop):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.stop_called = False

        def cycle(self):
            if not self.stop_called:
                self.stop_called = True
                self.stop()


    def setUp(self):
        green_light = GreenLight()
        green_light.set()
        self.loop = self.CustomLoop(green_light=green_light)

    def test_stop_from_within_thread(self):
        with self.assertLogs(logging.getLogger('superloops'), level='INFO') as cm:

            self.loop.start()
            time.sleep(0.1)
            self.assertEqual("TestSuperLoopSelfStop.CustomLoop_0: Started", cm.records[0].msg)
            self.assertEqual("TestSuperLoopSelfStop.CustomLoop_0: Stopping", cm.records[1].msg)
            self.assertEqual('Cannot join thread "TestSuperLoopSelfStop.CustomLoop_0" from within itself.', cm.records[2].msg)

class TestLoopControllerMocks(unittest.TestCase):

    def setUp(self):
        self.controller = LoopController(None)
        self.loop1 = Mock(spec=SuperLoop)
        self.loop2 = Mock(spec=SuperLoop)
        self.loop1.is_alive = False
        self.loop2.is_alive = False
        self.controller.new_loop(self.loop1)
        self.controller.new_loop(self.loop2)

    def test_maintain_loops(self):
        self.controller.maintain_loops()
        self.loop1.start.assert_called_once()
        self.loop2.start.assert_called_once()

    def test_stop_loops(self):
        self.controller.stop_loops()
        self.loop1.stop.assert_called_once()
        self.loop2.stop.assert_called_once()

    def test_has_alive_loops_no_loops_alive(self):
        self.loop1.is_alive = False
        self.loop2.is_alive = False
        self.assertFalse(self.controller.has_alive_loops(), "has_alive_loops should return False when no loops are alive")

    def test_has_alive_loops_with_alive_loops(self):
        self.loop1.is_alive = True
        self.loop2.is_alive = False
        self.assertTrue(self.controller.has_alive_loops(), "has_alive_loops should return True when at least one loop is alive")

    def test_alive_loops_no_loops_alive(self):
        self.loop1.is_alive = False
        self.loop2.is_alive = False
        self.assertEqual([], self.controller.alive_loops(), "alive_loops should return an empty list when no loops are alive")

    def test_alive_loops_with_alive_loops(self):
        self.loop1.is_alive = True
        self.loop2.is_alive = False
        self.assertEqual([self.loop1], self.controller.alive_loops(), "alive_loops should return a list with alive loops")

class TestSuperLoopFactory(unittest.TestCase):
    class CustomLoop(SuperLoop):
        def cycle(self):
            pass

    def test_super_loop_factory_default_parameters(self):
        factory = super_loop_factory()
        created_loop = factory(self.CustomLoop)
        self.assertIsInstance(created_loop, self.CustomLoop)
        self.assertIsNone(created_loop._green_light)
        self.assertEqual(created_loop._grace_period, 5)
        self.assertEqual(created_loop._max_loop_failures, 10)
        self.assertFalse(created_loop._stop_on_failure)
        self.assertTrue(created_loop.reset_globally)

    def test_super_loop_factory_custom_parameters(self):
        custom_green_light = GreenLight()
        factory = super_loop_factory(green_light=custom_green_light, grace_period=10, max_loop_failures=5, stop_on_failure=True, reset_globally=False)
        created_loop = factory(self.CustomLoop)
        self.assertIsInstance(created_loop, self.CustomLoop)
        self.assertEqual(created_loop._green_light, custom_green_light)
        self.assertEqual(created_loop._grace_period, 10)
        self.assertEqual(created_loop._max_loop_failures, 5)
        self.assertTrue(created_loop._stop_on_failure)
        self.assertFalse(created_loop.reset_globally)


class TestIntegration(unittest.TestCase):

    class GoodLoop(SuperLoop):

        def __init__(self, *args, event, **kwargs):
            self.event = event
            super().__init__(*args, **kwargs)

        def cycle(self):
            self.event.wait()
            time.sleep(0.1)

    class BadLoop(SuperLoop):
        def __init__(self, *args, event, **kwargs):
            super().__init__(*args, **kwargs)
            self.event = event
            self.counter = 0

        def cycle(self):
            self.event.wait()
            self.counter += 1
            if self.counter in [3,4,5]:
                self.failure()

        def on_start(self):
            return self.counter == 0

    def reset_callback(self):
        self.called_reset_callback = True

    def test_integration(self):
        # logging.basicConfig(level = logging.INFO)
        self.called_reset_callback = False
        green_light = GreenLight()
        green_light.set()
        loop_factory = super_loop_factory(
            green_light=green_light,
            max_loop_failures=2,
        )
        loop_controller = loop_factory(LoopController, reset_callback=self.reset_callback, loop_factory=loop_factory)

        green_light = loop_controller.green_light
        event = Event()
        event.clear()

        loop1 = loop_controller.new_from_factory(self.BadLoop, green_light=green_light, max_loop_failures=2, event=event)
        loop2 = self.GoodLoop(green_light=green_light, event=event)

        loop_controller.new_loop(loop2)

        loop_controller.start()

        # Give the loop controller some time to start
        while not loop_controller.is_alive:
            time.sleep(0.1)

        # Starting the custom loops
        loop_controller.maintain_loop(loop2)
        loop_controller.maintain_loop(loop1)

        # Give some time for the loops to exceed the failure limit
        while not self.called_reset_callback:
            event.set()
            time.sleep(0.1)

        event.clear()

        while not loop_controller.green_light.is_set():
            time.sleep(0.1)

        # Check if the reset_callback was called
        self.assertTrue(self.called_reset_callback, 'Reset callback should have been called')

        # Check if both loops have been reset
        self.assertEqual(0, loop1._failures, 'loop1 should have been reset')
        self.assertEqual(0, loop2._failures,  'loop2 should have been reset')

        # Gracefully stop both loops
        loop_controller.stop_loop(loop1)
        loop_controller.stop_loop(loop2)

        # Gracefully stop the LoopController
        loop_controller.stop()


if __name__ == '__main__':
    unittest.main()