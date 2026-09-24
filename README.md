##  README.md

### Purpose of this repository

We want to provide you with some very simple examples of how to use ReSim. 

Customers want a fast example of ReSim in use. This repository provides you with out-of-the-box examples for you to follow along in our [Getting Started Guide](https://docs.resim.ai/setup/). You can use the pre-baked experiences, builds (experience and metric builds), and metrics to follow along with the guide and stand something of substance up quickly. It provides readily available, public S3 and ECR URLs for you to plug and play in your own ReSim environment. 

We want to avoid duplicating documentation of how to use ReSim into this repository. We recommend at least going through the [Core Concepts](https://docs.resim.ai/core-concepts/) section of ReSim's documentation before you begin the Getting Started Guide.  

Once you have gone through the simple Getting Started Guide, you will then be ready to use your own systems and resources to launch ReSim for your organization. 

### Contents of this repository

- `devcontainer/` - This folder contains the devcontainer configuration for testing things in this guide locally.
- `experience-build/` - This folder contains the experience build that you will use to create your experiences. This `sim_run.py` script is copying over the file from your experience into the output location. Presumably your experience build will create output files based on your systems running against your experiences.
  - `/experiences/` - These experiences are locally stored instead of S3. For your own experiences you may choose to store them in S3. 
  - `sim_run.py` also emits every flight sample to `/tmp/resim/outputs/emissions.resim.jsonl` with the SignalFlag SDK, plus an event whenever the flight state or health flag changes. Each event carries metrics of its own, such as a table of position and speed at that moment, flight totals on landing, and a chart of the broken limit on a health warning or error. These emissions are the data the metrics are computed from.
- `tools/generate_flight_logs.py` - Generates the four flight logs in `experience-build/experiences/`. Each flight flies the same survey lap around the launch pad. The warning flight climbs above a 120 m altitude ceiling, and the error flight overshoots a 350 m geofence; each reports its health flag while it breaks that limit. Run `python3 tools/generate_flight_logs.py` to regenerate them.
- `.resim/metrics/config.resim.yml` - The metrics config. Each metric is a SQL query over the emitted flight samples plus the chart that draws it, and the `Off-Nominal Samples` metric decides whether each test passes. `templates/flight_path.liquid` draws the top-down flight path. Sync both to your branch with `signalflag metrics sync`.
- `metrics-build/` - A metrics build for the legacy metrics path, used by the `metrics-build-v25` image. The current demo does not need it.

### URLs for the pre-baked experiences, builds, and metrics

These are the `--location` attributes for experiences and builds. 

- Experiences: 
  - **Maiden Flight Voyage** - `experiences/maiden_drone_flight/`
  - **Drone Flight Fast** - `experiences/fast_drone_flight/`
  - **Drone Flight with Warning** - `experiences/warning_drone_flight/`
  - Drone Flight with Error - `experiences/error_drone_flight/`
- **Experience Build** - `public.ecr.aws/resim/open-builds/getting-started-demo:experience-build-v29`
- Metrics Set - `Drone Flight Metrics`, defined in `.resim/metrics/config.resim.yml`

The `experience-build-v25` and `metrics-build-v25` images remain available for the legacy metrics path.


### Resources

- [Overview of ReSim Core Concepts](https://docs.resim.ai/core-concepts/)
- [ReSim Getting Started Guide](https://docs.resim.ai/setup/)
- [ReSim CLI](https://github.com/resim-ai/api-client)

### Contributions

We want to keep this example as simple as possible, while also highlighting the value of ReSim. Feel free to submit a Pull Request if you have any suggestions on how to improve it.



