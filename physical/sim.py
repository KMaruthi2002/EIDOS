"""Simulated robot for EIDOS physical skills.

A Franka Panda arm (MuJoCo Menagerie model, Apache-2.0) at a table with
coloured blocks. The controller is scripted (inverse kinematics plus a
pick/place routine); nothing here is learned. EIDOS supplies *what* to do
and *how to check it*; this module supplies the arm.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "osmesa")
os.environ.setdefault("PYOPENGL_PLATFORM", "osmesa")

import mujoco  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
PANDA = HERE / "menagerie" / "franka_emika_panda" / "panda.xml"

BLOCKS = {  # name: rgba
    "blue": (0.16, 0.36, 0.95, 1),
    "green": (0.12, 0.70, 0.36, 1),
    "yellow": (0.98, 0.78, 0.12, 1),
}
HALF = 0.022  # block half size (m)


def scene_xml(layout: dict[str, tuple[float, float]]) -> str:
    bodies = "\n".join(
        f'''<body name="{n}" pos="{x} {y} {HALF + 0.001}"><freejoint name="{n}_j"/>
             <geom type="box" size="{HALF} {HALF} {HALF}" rgba="{' '.join(map(str, BLOCKS[n]))}"
                   mass="0.05" friction="1.5 0.02 0.001" condim="4" solref="0.01 1"/></body>'''
        for n, (x, y) in layout.items())
    return f'''<mujoco model="eidos table">
  <include file="{PANDA}"/>
  <option timestep="0.002" integrator="implicitfast"/>
  <visual><headlight diffuse="0.4 0.4 0.4" ambient="0.32 0.32 0.32" specular="0 0 0"/>
          <global offwidth="1280" offheight="720"/><quality shadowsize="4096"/></visual>
  <asset>
    <texture type="2d" name="wood" builtin="flat" rgb1="0.80 0.78 0.74" width="64" height="64"/>
    <material name="table" texture="wood" reflectance="0.05"/>
    <texture type="skybox" builtin="gradient" rgb1="0.93 0.95 0.97" rgb2="0.80 0.84 0.89" width="256" height="1536"/>
  </asset>
  <worldbody>
    <light pos="0.4 -0.6 1.6" dir="-0.2 0.4 -1" directional="true" castshadow="true" diffuse="0.55 0.55 0.55"/>
    <geom name="table" type="plane" size="1.2 1.2 0.05" material="table"/>
    <camera name="front" pos="1.08 -0.72 0.68" xyaxes="0.7167 0.6974 -0.0000 -0.2838 0.2917 0.9134" fovy="46"/>
    <camera name="top" pos="0.5 0.0 1.05" xyaxes="0 -1 0 1 0 0" fovy="36"/>
    <camera name="side" pos="0.5 -0.85 0.07" xyaxes="1 0 0 0 0 1" fovy="30"/>
    <camera name="side2" pos="1.25 0.0 0.07" xyaxes="0 1 0 0 0 1" fovy="30"/>
    {bodies}
  </worldbody>
</mujoco>'''


class Sim:
    def __init__(self, layout: dict[str, tuple[float, float]], seed: int = 0):
        # Written next to panda.xml so its relative mesh paths resolve.
        path = PANDA.parent / "_eidos_scene.xml"
        path.write_text(scene_xml(layout).replace(str(PANDA), "panda.xml"))
        self.m = mujoco.MjModel.from_xml_path(str(path))
        self.d = mujoco.MjData(self.m)
        home = self.m.key_qpos[0][:9] if self.m.nkey else None
        if home is not None:
            self.d.qpos[:9] = home
            self.d.ctrl[:7] = home[:7]
        self.d.ctrl[7] = 255
        mujoco.mj_forward(self.m, self.d)
        self.hand = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, "hand")
        self.down = self.d.xmat[self.hand].reshape(3, 3).copy()   # gripper-down orientation
        self.renderers: dict[tuple, mujoco.Renderer] = {}
        self.frames: list[np.ndarray] = []
        self.record_every = 0.04      # seconds between recorded frames (25 fps)
        self._last_rec = -1.0
        self.overlay = None           # callable(img) -> img, for captions
        self.recording = True
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------ rendering
    def render(self, camera="front", w=960, h=540) -> np.ndarray:
        key = (w, h)
        if key not in self.renderers:
            self.renderers[key] = mujoco.Renderer(self.m, h, w)
        r = self.renderers[key]
        r.update_scene(self.d, camera=camera)
        return r.render().copy()

    def _maybe_record(self):
        if self.d.time - self._last_rec >= self.record_every:
            self._last_rec = self.d.time
            img = self.render("front")
            if self.overlay:
                img = self.overlay(img)
            self.frames.append(img)

    def step(self, seconds: float, record: bool = True):
        n = int(seconds / self.m.opt.timestep)
        for _ in range(n):
            mujoco.mj_step(self.m, self.d)
            if record and self.recording:
                self._maybe_record()

    # ------------------------------------------------------------ kinematics
    def tip(self) -> np.ndarray:
        """Point between the fingertips."""
        R = self.d.xmat[self.hand].reshape(3, 3)
        return self.d.xpos[self.hand] + R @ np.array([0, 0, 0.105])

    def ik(self, target: np.ndarray, iters: int = 200) -> np.ndarray:
        """Joint angles that put the fingertip point at `target`, gripper down."""
        m, d = self.m, self.d
        data = mujoco.MjData(m)
        data.qpos[:] = d.qpos
        jacp = np.zeros((3, m.nv))
        jacr = np.zeros((3, m.nv))
        for _ in range(iters):
            mujoco.mj_kinematics(m, data)
            mujoco.mj_comPos(m, data)
            R = data.xmat[self.hand].reshape(3, 3)
            tip = data.xpos[self.hand] + R @ np.array([0, 0, 0.105])
            err_p = target - tip
            # orientation error: rotate R toward self.down
            Re = self.down @ R.T
            err_r = 0.5 * np.array([Re[2, 1] - Re[1, 2], Re[0, 2] - Re[2, 0], Re[1, 0] - Re[0, 1]])
            if np.linalg.norm(err_p) < 1e-4 and np.linalg.norm(err_r) < 1e-3:
                break
            mujoco.mj_jac(m, data, jacp, jacr, tip, self.hand)
            J = np.vstack([jacp[:, :7], jacr[:, :7]])
            e = np.concatenate([err_p, 0.5 * err_r])
            dq = J.T @ np.linalg.solve(J @ J.T + 1e-4 * np.eye(6), e)
            data.qpos[:7] += dq
            data.qpos[:7] = np.clip(data.qpos[:7], m.jnt_range[:7, 0], m.jnt_range[:7, 1])
        return data.qpos[:7].copy()

    def move_to(self, target, seconds: float = 1.2):
        """Straight-line move of the fingertip, gripper pointing down."""
        start = self.tip()
        target = np.asarray(target, float)
        steps = max(2, int(seconds / 0.05))
        for k in range(1, steps + 1):
            a = k / steps
            a = a * a * (3 - 2 * a)
            q = self.ik(start + (target - start) * a, iters=60)
            self.d.ctrl[:7] = q
            self.step(seconds / steps)
        self.step(0.25)

    def grip(self, close: bool):
        self.d.ctrl[7] = 0 if close else 255
        self.step(0.6)

    # ------------------------------------------------------------ objects
    def pos(self, name: str) -> np.ndarray:
        bid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_BODY, name)
        return self.d.xpos[bid].copy()

    def pick_and_place(self, obj: str, dest_xy, dest_z: float):
        """Pick `obj` and set it down with its centre at (dest_xy, dest_z)."""
        p = self.pos(obj)
        hover = 0.16
        self.grip(False)
        self.move_to([p[0], p[1], p[2] + hover], 1.1)
        self.move_to([p[0], p[1], p[2] - 0.004], 0.8)
        self.grip(True)
        self.move_to([p[0], p[1], p[2] + hover], 0.9)
        self.move_to([dest_xy[0], dest_xy[1], dest_z + hover], 1.2)
        self.move_to([dest_xy[0], dest_xy[1], dest_z + 0.006], 0.8)
        self.grip(False)
        self.move_to([dest_xy[0], dest_xy[1], dest_z + hover], 0.8)

    def nudge(self, name: str, dxy=(0.0, 0.09), up: float = 0.0):
        """A disturbance: knock a block sideways (someone bumps the table)."""
        jid = mujoco.mj_name2id(self.m, mujoco.mjtObj.mjOBJ_JOINT, name + "_j")
        adr = self.m.jnt_qposadr[jid]
        self.d.qpos[adr:adr + 2] += np.asarray(dxy)
        self.d.qpos[adr + 2] = HALF + 0.001 + up
        vadr = self.m.jnt_dofadr[jid]
        self.d.qvel[vadr:vadr + 6] = 0
        mujoco.mj_forward(self.m, self.d)
        self.step(0.4)

    def home(self):
        """Park the arm clear of the work area so the cameras see the blocks."""
        self.move_to([0.22, 0.30, 0.42], 1.0)
