"""Rebuild an episode's emissions from its MCAP recording, without running the simulator.

The recording holds the cube's pose in /tf, the camera in /observations/top, and the
environment's reward and success flag in /reward and /is_success. That is everything
emit_episode needs, so replaying a recording produces the same emissions and charts
as the run that recorded it, on a CPU and in seconds.

The experience's SEED selects which recording to replay, the same variable the
simulator reads, so a replay build and a simulator build run the same experiences.
"""

import logging
import os
import shutil
from pathlib import Path

import av
import numpy as np
from mcap.reader import make_reader
from mcap_protobuf.decoder import DecoderFactory

from aloha_honua.emissions import emit_episode, make_emitter

logger = logging.getLogger(__name__)

RECORDINGS_DIR = Path(os.environ.get("RECORDINGS_DIR", "/app/recordings"))
OUTPUT_DIR = Path("/tmp/resim/outputs")
CUBE_FRAME = "box"


def read_recording(mcap_path: Path) -> dict:
    """Read a recording into the results dict that run_policy returns."""
    times, cube_positions, frames = [], [], []
    rewards, successes = {}, {}
    codec = av.CodecContext.create("h264", "r")

    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        for _, channel, message, decoded in reader.iter_decoded_messages(log_time_order=True):
            if channel.topic == "/tf":
                box = next(t for t in decoded.transforms if t.child_frame_id == CUBE_FRAME)
                # The cube hangs directly off the world frame, so its transform is its
                # world position, the same value the simulator reads from xpos.
                assert box.parent_frame_id == "world", box.parent_frame_id
                times.append(message.log_time)
                cube_positions.append(np.array([box.translation.x, box.translation.y, box.translation.z]))
            elif channel.topic == "/reward":
                rewards[message.log_time] = decoded.value
            elif channel.topic == "/is_success":
                successes[message.log_time] = decoded.value
            elif channel.topic == "/observations/top":
                for packet in codec.parse(decoded.data):
                    frames.extend(frame.to_ndarray(format="rgb24") for frame in codec.decode(packet))
    frames.extend(frame.to_ndarray(format="rgb24") for frame in codec.decode(None))

    missing = [t for t in times if t not in rewards]
    if missing:
        raise ValueError(f"{mcap_path} has no /reward for {len(missing)} of {len(times)} steps")

    return {
        "times": [t / 1e9 for t in times],
        "rewards": np.array([rewards[t] for t in times]),
        "is_success": bool(successes.get(times[-1], False)),
        "frames": frames,
        "cube_positions": cube_positions,
    }


def main():
    logging.basicConfig(level=logging.INFO)
    seed = int(os.environ.get("SEED", "1000"))
    recording = RECORDINGS_DIR / f"seed_{seed}" / "transfer_cube.mcap"
    logger.info("Replaying %s", recording)

    results = read_recording(recording)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Attach the recording itself, as a simulated run does.
    shutil.copy(recording, OUTPUT_DIR / recording.name)

    with make_emitter() as emitter:
        emit_episode(emitter, results, OUTPUT_DIR)


if __name__ == "__main__":
    main()
