"""MuJoCo adapter for any position-actuated parallel gripper profile."""
import mujoco
import numpy as np
from teleoperation.parallel_gripper import GripperCommand, GripperObservation


class MujocoParallelGripper:
    def __init__(self, plant, profile, *, target_generator=None):
        self.plant = plant
        self.target_generator = target_generator
        self.ids = np.array([mujoco.mj_name2id(plant.model, mujoco.mjtObj.mjOBJ_ACTUATOR, n)
                             for n in profile['actuators']], dtype=int)
        if np.any(self.ids < 0):
            raise ValueError('missing parallel gripper actuator')
        self.open = np.array(profile['open_position'], dtype=float)
        self.closed = np.array(profile['closed_position'], dtype=float)
        if (self.open.shape != self.ids.shape or self.closed.shape != self.ids.shape
                or not np.all(np.isfinite(self.open)) or not np.all(np.isfinite(self.closed))
                or np.any(self.closed == self.open)):
            raise ValueError('invalid parallel gripper endpoint mapping')
        ranges = plant.model.actuator_ctrlrange[self.ids]
        if np.any(np.minimum(self.open,self.closed)<ranges[:,0]) or np.any(np.maximum(self.open,self.closed)>ranges[:,1]):
            raise ValueError('gripper endpoints outside actuator limits')
        self.qpos = plant.model.jnt_qposadr[plant.model.actuator_trnid[self.ids,0]]
        plant.data.qpos[self.qpos] = self.open
        plant.data.ctrl[self.ids] = self.open
        mujoco.mj_forward(plant.model,plant.data)

    def observe(self, now_ns):
        if self.target_generator is not None:
            # Both models came from the same assembled asset. Keep moving tool
            # geometry in the authoritative collision model current.
            target = self.target_generator
            target.ik.data.qpos[self.qpos] = self.plant.data.qpos[self.qpos]
            mujoco.mj_forward(target.model, target.ik.data)
        fractions = (self.plant.data.qpos[self.qpos]-self.open)/(self.closed-self.open)
        valid = bool(np.all(np.isfinite(fractions)) and np.all(fractions >= -.02)
                     and np.all(fractions <= 1.02) and np.ptp(fractions) < .05)
        return GripperObservation(float(np.clip(np.mean(fractions),0,1)),now_ns,now_ns,
                                  valid,None if valid else 'joint_tracking_invalid','mujoco')

    def submit(self, command: GripperCommand):
        if not 0 <= command.closed_fraction <= 1:
            raise ValueError('gripper target outside [0,1]')
        self.plant.data.ctrl[self.ids] = self.open + command.closed_fraction*(self.closed-self.open)

    def hold(self):
        pass  # MuJoCo keeps the last position command; never auto-opens.
