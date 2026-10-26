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


def test_native_unknown_validity_and_zero_disconnect_cannot_authorize():
    from motion_input.xrobo import XRoboNativeInput
    raw = json.dumps({'functionName':'Tracking','value':json.dumps({
        'timeStampNs':1000000000,'predictTime':1000.,'appState':{'focus':True},
        'Head':{'pose':'0,1,0,0,0,0,1','status':3},
        'Controller':{'right':{'pose':'0,0,0,0,0,0,-1','grip':0.,'trigger':0.,'secondaryButton':False}}})})
    source = XRoboNativeInput()
    assert not source.ingest(raw, 1000000000)
    assert source.reason == 'zero_controller_pose'
    assert source.frame['controller_tracked'] is None
    assert source.frame['source_session'] is None
    assert source.frame['hardware_authorized'] is False


def test_native_duplicate_restart_gap_and_coordinate_preservation():
    from motion_input.xrobo import XRoboNativeInput
    def raw(utc, elapsed):
        return json.dumps({'functionName':'Tracking','value':json.dumps({
            'timeStampNs':utc,'predictTime':elapsed,'appState':{'focus':True},
            'Head':{'pose':'0,1,0,0,0,0,1','status':3},
            'Controller':{'right':{'pose':'1,2,3,0,0,0,1','grip':1.,'trigger':.7}}})})
    source = XRoboNativeInput()
    assert source.ingest(raw(100,100),1_000_000_000)
    assert source.frame['position_m'] == [1,2,3]  # No second Z flip.
    assert not source.ingest(raw(100,100),1_010_000_000)
    assert source.ingest(raw(200,200),1_200_000_000)
    assert source.interrupted
    assert source.preview_rejection(1_400_000_000) == 'callback_stale'
    assert source.ingest(raw(300,1),1_410_000_000)
    assert source.interrupted
