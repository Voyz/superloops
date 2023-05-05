import logging
import unittest
from unittest.mock import MagicMock

from superloops import GreenLight, SuperLoop, LoopController

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

        expected_log = "Exception running on_start of TestSuperLoop.CustomLoop: Test on_stop exception"
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

    def test_failure_exceed_max_failures_stop(self):
        self.loop._max_loop_failures = 3
        self.loop.stop = MagicMock()
        for i in range(4):
            self.loop.failure()
        self.loop.stop.assert_called_once()
        self.assertEqual(self.loop._failures, 0)

    def test_failure_exceed_max_failures_stop_clear_green_light(self):
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

    def test_loop_controller(self):
        loop_controller = LoopController(reset_callback=self.reset_callback)

        custom_loop = self.CustomLoop()
        loop_controller.new_loop(custom_loop)

        loop_controller.start()
        self.assertFalse(custom_loop.is_alive, "Custom loop should not be alive after loop_controller starts")

        loop_controller.maintain_loop(custom_loop)
        self.assertTrue(custom_loop.is_alive, "Custom loop should be alive after loop_controller maintains it")

        loop_controller.stop_loop(custom_loop)
        self.assertFalse(custom_loop.is_alive, "Custom loop should not be alive after loop_controller stops it")


if __name__ == '__main__':
    unittest.main()