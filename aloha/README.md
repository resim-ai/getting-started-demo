# MuJoCo demo

The demo behind the [Run your first test batch](https://docs.signalflag.ai/tutorials/first-batch/) tutorial. A bimanual ALOHA robot in MuJoCo, driven by a pretrained ACT policy, picks up a cube with its right arm and hands it to its left. Each experience is one episode, selected by the `SEED` environment variable, which sets where the cube starts.

## Contents

- `.resim/metrics/config.resim.yml` and `.resim/metrics/templates/raw.liquid` - The metrics config: the topics each episode emits, the per-test and per-batch metrics, and an `ALOHA Metrics` set. A test passes when the cube is handed over and warns otherwise. Sync it with `signalflag metrics sync` from this directory.
- `recordings/seed_<n>/transfer_cube.mcap` - Four recorded episodes. Each MCAP holds the robot and cube transforms (`/tf`), the top camera (`/observations/top`), and the environment's reward and success flag (`/reward`, `/is_success`).
- `src/aloha_honua/replay.py` - Rebuilds an episode's emissions from its recording, without the simulator.
- `src/aloha_honua/emissions.py` - Turns an episode into the emissions the metrics config reads. The simulator and the replay share it, so both emit the same data.
- `Dockerfile` - Builds the replay image.

## Images

Both images read the same `SEED` experiences and emit data for the same metrics config, so a test suite can run either one.

| Image | Runs | Resources | Per test |
|---|---|---|---|
| `public.ecr.aws/resim/open-builds/getting-started-demo:aloha-replay-v1` | Replays the recording for `SEED`. Only the four seeds below are recorded. | The default system resources | A few seconds |
| `public.ecr.aws/resim/open-builds/getting-started-demo:aloha-sim-v1` | Simulates the episode with the ACT policy for any `SEED` | 1 NVIDIA GPU (A10G class), 8 vCPU, 16 GiB | About 25 s of simulation, plus node start and image pull |

The simulator image re-plans every 50 steps (`--policy.n_action_steps=50`), set through its `POLICY_OVERRIDES` environment variable, and runs with deterministic GPU kernels. With those, a seed reproduces its recording exactly. It needs no network access.

## Recordings

Recorded with `aloha-sim-v1` on an NVIDIA A10G. An episode ends when the cube is handed over or after 600 steps.

| Seed | Outcome | Steps | Reward regressions |
|---|---|---|---|
| 250 | Handover complete | 356 | 6 |
| 300 | Handover complete | 545 | 14 |
| 850 | Stalled after lifting the cube | 600 | 12 |
| 1000 | Stalled after lifting the cube | 600 | 4 |

A regression is a step where the reward stage falls back, such as the cube slipping out of a gripper.

## Building the replay image

```shell
docker build -t aloha-replay .
docker run --rm -e SEED=250 -v "$PWD/outputs:/tmp/resim/outputs" aloha-replay
```

The run writes `emissions.resim.jsonl`, `episode.gif`, and a copy of the recording to `outputs/`.

## Licenses

The simulator image contains the [`lerobot/act_aloha_sim_transfer_cube_human`](https://huggingface.co/lerobot/act_aloha_sim_transfer_cube_human) checkpoint, [LeRobot](https://github.com/huggingface/lerobot), [gym-aloha](https://github.com/huggingface/gym-aloha), and [MuJoCo](https://github.com/google-deepmind/mujoco), all under Apache-2.0, and torchvision's ResNet18 ImageNet weights under BSD-3-Clause.
