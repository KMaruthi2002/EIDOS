#!/usr/bin/env bash
# Fetch the Franka Panda model (MuJoCo Menagerie, Apache-2.0) and install MuJoCo.
set -e
cd "$(dirname "$0")"
pip install mujoco==3.3.7
if [ ! -d menagerie ]; then
  git clone --depth 1 --filter=blob:none --sparse https://github.com/google-deepmind/mujoco_menagerie menagerie
  (cd menagerie && git sparse-checkout set franka_emika_panda)
fi
echo "On a headless Linux machine also install OSMesa (apt install libosmesa6) and set MUJOCO_GL=osmesa."
