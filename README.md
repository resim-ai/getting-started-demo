##  README.md

### Purpose of this repository

We want to provide you with some very simple examples of how to use ReSim. 

Customers want a very fast example of ReSim in use. This repository provides you with out-of-the-box examples for you to follow along in our [Getting Started Guide](https://docs.resim.ai/setup/). This sample repository shows you how to create builds, experiences, and metrics. It provides readily available, public S3 URLs for you to plug and play in your own ReSim environment.  

Once you have gone through the simple Getting Started Guide, you will then be ready to use your own systems and resources to launch ReSim for your organization. 

### Contents of this repository

- `devcontainer/` - This folder contains the devcontainer configuration for the ReSim CLI for local development.
- `experience-build/` - This folder contains the experience build that you will use to create your experiences.
  - `/experiences/` - `Note:` The experience folders in this subdirectory are for local testing purposes only. Your experience build will pull the experiences from S3 and you will reference them using the `--location` flag when creating experiences as outlined in the [ReSim Experience Documentation](https://docs.resim.ai/setup/adding-experiences/).
- `metrics-build/` - This folder contains the metrics build that you will use to create your metrics.

### Resources

- [ReSim Getting Started Guide](https://docs.resim.ai/setup/)
- [ReSim CLI](https://github.com/resim-ai/api-client)

### Contributions

We want to keep this example as simple as possible, while also highlighting the value of ReSim. Feel free to submit a Pull Request if you have any suggestions on how to improve it.



