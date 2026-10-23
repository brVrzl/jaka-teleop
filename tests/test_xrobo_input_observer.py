import json
import unittest

from tools.xrobo_input_observer import parse_tracking


class XRoboObserverTests(unittest.TestCase):
    def payload(self, **right):
        return json.dumps({'functionName': 'Tracking', 'value': json.dumps({
            'Controller': {'right': dict(pose='1,2,3,0,0,0,1', grip=0,
                                         trigger=1, **right)}})})

    def test_observation_preserves_missing_source_validity(self):
        frame = parse_tracking(self.payload())
        self.assertEqual(frame['position_m'], [1, 2, 3])
        self.assertEqual(frame['right_controller']['grip'], 0)
        self.assertEqual(frame['right_controller']['trigger'], 1)
        self.assertEqual(frame['missing'], ['is_tracked', 'status', 'connected'])
        self.assertIsNone(frame['source_sequence'])
        self.assertIsNone(frame['source_session'])

    def test_invalid_pose_rejected(self):
        envelope = json.loads(self.payload())
        value = json.loads(envelope['value'])
        value['Controller']['right']['pose'] = 'nan,0,0,0,0,0,1'
        envelope['value'] = json.dumps(value)
        with self.assertRaises(ValueError):
            parse_tracking(json.dumps(envelope))

    def test_other_events_are_not_tracking_samples(self):
        self.assertIsNone(parse_tracking('{"functionName":"Other"}'))
