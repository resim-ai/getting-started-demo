##  README.md

### Purpose of this repository

We want to provide you with some very simple examples of how to use ReSim. 

Customers want a very fast example of ReSim in use. This repository provides you with out-of-the-box examples for you to follow along in our [Getting Started Guide](https://docs.resim.ai/setup/). This sample repository shows you how to create builds, experiences, and metrics. It provides readily available, public S3 URLs for you to plug and play in your own ReSim environment.  

Once you have gone through the simply Getting Started Guide, you will then be ready to use your own systems and resources to launch ReSim for your organization. 

### Contents of this repository

- `experience-build/` - This folder contains the experience build that you will use to create your experiences.
- `metrics-build/` - This folder contains the metrics build that you will use to create your metrics.
- `build.sh` - This script will build the experience and metrics builds and push them to S3 and ReSim.
- `README.md` - This file.


This Getting Started guide will highlight the following areas:

1. Providing an experience build that allows you to create a simple scene
  - `Note:` The experience folders in this repository are for local testing purposes only. Your experience build will pull the experiences from S3 and you will reference them using the `--location` flag when creating experiences as outlined in the [ReSim Experience Documentation](https://docs.resim.ai/setup/adding-experiences/).
2. Creating a metrics build that takes the outputs of the experience build and creates some simple metrics
3. Demonstrates sample metrics graph to see how the metrics are displayed

### Contributions

We want to keep this example as simple as possible, while also highlighting the value of ReSim. Feel free to submit a Pull Request if you have any suggestions on how to improve it.



