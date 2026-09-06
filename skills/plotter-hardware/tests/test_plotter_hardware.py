import contextlib
import importlib.util
import io
import pathlib
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('plotter', pathlib.Path(__file__).resolve().parents[1] / 'scripts/plotter_hardware.py')
plotter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plotter)


class PlotterTests(unittest.TestCase):
    def invoke(self, args):
        output = io.StringIO()
        with patch('sys.argv', ['plotter', *args]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = plotter.main()
        return result, output.getvalue()

    def test_all_mutating_commands_default_to_no_network(self):
        cases = {
            'move-to': ['--x', '1', '--y', '2'],
            'actuator-up': ['--tool', 'pen'],
            'actuator-down': ['--tool', 'eraser'],
            'draw-to': ['--x', '1', '--y', '2', '--pen', 'pen'],
            'plot-cancel': ['--job-id', 'demo'],
            'plot-svg': ['--file', 'demo.svg', '--pen', 'pen'],
        }
        with patch.object(plotter.urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')):
            for command in [*plotter.JSON_WRITE_PATHS, 'plot-cancel', 'plot-svg']:
                with self.subTest(command=command):
                    result, output = self.invoke([command, *cases.get(command, [])])
                    self.assertEqual(result, 0)
                    self.assertIn('Dry run', output)
                    self.assertIn('POST ', output)

    def test_move_to_execute_routes_coordinates(self):
        with patch.object(plotter, 'request', return_value=0) as request:
            self.assertEqual(self.invoke(['move-to', '--x', '1', '--y', '2', '--execute'])[0], 0)
            self.assertTrue(request.call_args.args[1].endswith('/axiDraw/move_to'))
            self.assertEqual(request.call_args.kwargs['body'], {'x': 1.0, 'y': 2.0})

    def test_gpio_options_for_pulse_and_toggle(self):
        for command in ['pulse', 'solenoid-toggle']:
            with self.subTest(command=command), patch.object(plotter, 'request', return_value=0) as request:
                self.invoke([command, '--port', 'D', '--pin', '2', '--default-state', 'LOW', '--execute'])
                self.assertEqual(request.call_args.kwargs['body'], {'port': 'D', 'pin': '2', 'default_state': 'LOW'})
                with self.assertRaises(SystemExit) as error:
                    self.invoke([command, '--port', 'D'])
                self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
