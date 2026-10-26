# Simulation assets

## English

The default mounted MuJoCo asset is `jaka_rh56_visual_coacd.xml`. Its source
model is `jaka_rh56.xml`; the runtime asset uses the reviewed visual/CoACD
geometry and current RH56 actuator limits. The committed asset is consumed by
the simulation configs and is not rebuilt automatically during runtime.

Use the asset builder only for offline inspection or the explicit check:

```bash
.venv/bin/python tools/build_rh56_visual_coacd_runtime_asset.py --check
```

`assets/correll_rh56dfx/` is a licensed reference model, not the mounted
JAKA/RH56 runtime. Preserve upstream attribution and do not treat reference
geometry as physical collision authority.

## 中文

默认挂载的 MuJoCo asset 是 `jaka_rh56_visual_coacd.xml`，源模型是 `jaka_rh56.xml`；runtime asset 使用经过
review 的 visual/CoACD geometry 和当前 RH56 actuator limit。提交的 asset 由 simulation config 使用，运行时不会
自动重建。

asset builder 只用于离线检查或显式 check：

```bash
.venv/bin/python tools/build_rh56_visual_coacd_runtime_asset.py --check
```

`assets/correll_rh56dfx/` 是带 license 的 reference model，不是挂载的 JAKA/RH56 runtime。保留 upstream
attribution，不要把 reference geometry 当作真机 collision authority。

## DH PGE-50-26 simulation proxy

`dh_pge_50_26_proxy.xml` is a **dimensioned movable proxy, not official CAD or a
validated physical collision model**. The [DH official EN.23.01 catalog, p.19](https://en.dh-robotics.com/wp-content/uploads/2022/03/Servo-Electric-Gripper_DH-Robotics_EN.23.01.pdf)
lists PGE-50-26 without brake as 97 × 55 × 29 mm, 0.4 kg, total stroke 26 mm.
Do not substitute the different PGE-5-26 specifications on the current product page.
An official mesh for the exact installed suffix was not obtained.

The proxy divides that envelope into a 77 mm housing and 20 mm finger section;
finger shape and mass split (0.36 kg housing, 0.02 kg each finger) are assumptions.
MuJoCo computes uniform-box inertias from these masses, not measured inertias.
The flange-to-base translation is an **assumed** +9 mm along flange Z, with identity
rotation; TCP is the midpoint of the fingertip plane at flange Z=106 mm. The
physical adapter plate, cable, tool orientation/TCP and payload remain unverified.
Two opposed slide joints each travel 13 mm with an equality constraint. The
proxy retains 0.2 mm closed clearance to avoid artificial finger interpenetration:
inner-face gap is `0.0262 - 0.026 * closed_fraction` metres. This clearance is a
simulation geometry choice, not a manufacturer minimum gap claim.

`build_viewer_mjcf` replaces only the RH56 subtree/assets/constraints/actuators
with this component in a generated model. The JAKA tree is not copied. The
shared IK selects `jaka_dh_tcp`; solver, continuation, native limits and watchdog
are unchanged. Moving gripper joints are synchronized into its collision model.
The original RH56 assets and six-channel action convention remain unchanged.
