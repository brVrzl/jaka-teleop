"""Protocol boundary tests; synthetic inputs are not Quest acceptance."""
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'trossen_observer', Path(__file__).parents[1] / 'tools/trossen_input_observer.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


class TrossenObserverTests(unittest.TestCase):
    def test_raw_tracking_and_grip_stay_independent(self):
        frame = {'right_controller': {'is_tracked': 1,
                 'pose6d': dict.fromkeys(('x', 'y', 'z', 'ax', 'ay', 'az'), 0),
                 'triggers': {'hand_trigger': 0, 'index_trigger': 1},
                 'buttons': {'one': 0, 'two': 1},
                 'thumbstick': {'x_axis': 0, 'y_axis': 0}}}
        parsed, missing = observer.parse_payload(json.dumps(frame).encode())
        self.assertEqual(parsed, frame)
        self.assertEqual(missing, [])

    def test_absent_fields_are_explicit_not_fabricated(self):
        parsed, missing = observer.parse_payload(b'{"right_controller":{"is_tracked":0}}')
        self.assertIn('triggers.hand_trigger', missing)
        self.assertNotIn('pose6d', parsed['right_controller'])

    def test_reject_malformed_and_nonfinite_values(self):
        for raw in (b'HTS,0', b'[]', b'{}',
                    b'{"right_controller":{"is_tracked":2}}',
                    b'{"right_controller":{"is_tracked":1,"pose6d":{"x":NaN}}}',
                    b'{"right_controller":{"is_tracked":1,"triggers":{"hand_trigger":2}}}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                observer.parse_payload(raw)


if __name__ == '__main__':
    unittest.main()
