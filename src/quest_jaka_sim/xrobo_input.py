"""Explicit UNVERIFIED XRobo replay experiment; never a hardware input adapter."""
from motion_input.xrobo import XRoboNativeInput
from motion_input import Pose6D, AnalogClutchSample
from motion_input.hts_canonical import CanonicalQuestState, QuestHandObservation, QuestHeadObservation
from motion_input.model import Side, TrackingState

MODE = 'xrobo-native-experimental'


class XRoboSimulationRouter:
    def __init__(self, *, stale_after_s=.15):
        self.input = XRoboNativeInput(stale_after_s)

    def ingest(self, datagram, session):
        now = datagram.receive_monotonic_ns
        accepted = self.input.ingest(datagram.payload.decode('utf-8'), now)
        if self.input.interrupted or not accepted:
            session.arm_clutch.fault(now, 'XROBO_UNVERIFIED_CONTINUITY_BREAK')
            session.buffer.clear()
        if accepted:
            f = self.input.frame
            try:
                head = [float(v) for v in f['head']['pose'].split(',')]
                head_pose = Pose6D(tuple(head[:3]),tuple(head[3:]))
                pose = Pose6D(tuple(f['position_m']),tuple(f['orientation_xyzw']))
            except ValueError:
                self.input.frame = None
                self.input.reason = 'invalid_pose'
                accepted = False
                session.arm_clutch.fault(now, 'XROBO_INVALID_POSE')
                session.buffer.clear()
            if accepted:
                count = self.input.local_callback_count
                source_ns = f['source_time_stamp_ns']
                state = CanonicalQuestState(now, source_ns, count, 'xrobo_unverified_world',
                    QuestHeadObservation(True,now,source_ns,None,0.,head_pose,1.),
                    QuestHandObservation(Side.LEFT,TrackingState.DISCONNECTED,False,
                        None,None,None,None,None,None,'left_wrist'),
                    # LIMITED + usable only for this isolated simulation experiment.
                    # This boolean is NOT a claim of source tracking validity.
                    QuestHandObservation(Side.RIGHT,TrackingState.LIMITED,True,now,
                        source_ns,None,count,0.,pose,'xrobo_visual_world'),
                    {'input_mode':MODE,'simulation_only':True,'controller_tracked':None,
                     'controller_connected':None,'source_session':None,'source_sequence':None,
                     'reference_space_verified':False,'continuity_verified':False})
                session.ingest_shared_state(state,pose_only=True)
        self.poll(now,session)
        return accepted

    def poll(self, now_ns, session):
        f = self.input.frame
        usable = self.input.preview_rejection(now_ns) is None
        received = self.input.received_ns or 0
        count = self.input.local_callback_count
        right = {} if f is None else f['right_controller']
        if right.get('secondaryButton') is True:
            session.arm_clutch.fault(now_ns,'XROBO_B_STOP')
            usable = False
        # No continuity_generation: the existing clutch cannot auto-reanchor this source.
        grip = AnalogClutchSample(right.get('grip',0.),received,count,valid=usable)
        session.parallel_trigger = AnalogClutchSample(right.get('trigger',0.),received,count,valid=usable)
        session.set_clutch_samples(index=grip,
            grip=AnalogClutchSample(0.,received,count,valid=False),
            left_controller_valid=usable,provider=MODE)

    def telemetry(self):
        return {'input_mode':MODE,'controller_valid':None,'controller_connected':None,
                'source_session':None,'source_sequence':None,'hardware_authorized':False,
                'reference_space_verified':False,'automatic_reanchor_enabled':False,
                'local_callback_count':self.input.local_callback_count,
                'rejected_callbacks':self.input.rejected,'last_input_reason':self.input.reason}
