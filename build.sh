#!/bin/bash

set -xo pipefail

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

# login with AWS
AWS_PROFILE=infrastructure
echo "Profile set to $AWS_PROFILE"
aws sts get-caller-identity &> /dev/null
EXIT_CODE="$?"
export AWS_REGION=us-east-1
if [ $EXIT_CODE -eq 0 ]
then
    echo "Token still valid, reusing..."
else
    echo "Token invalid, refreshing..."
    aws sso login
fi
aws ecr-public get-login-password --profile infrastructure --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/resim

# build images
docker build --platform linux/amd64 -t getting-started-experience-build -f experience-build/Dockerfile experience-build
docker build --platform linux/amd64 -t getting-started-metrics-build -f metrics-build/Dockerfile.metrics metrics-build

# tag the images
docker tag getting-started-experience-build public.ecr.aws/resim/open-builds/getting-started-demo:experience-build-${VERSION}
docker tag getting-started-metrics-build public.ecr.aws/resim/open-builds/getting-started-demo:metrics-build-${VERSION}

# push the images
docker push public.ecr.aws/resim/open-builds/getting-started-demo:experience-build-${VERSION}
docker push public.ecr.aws/resim/open-builds/getting-started-demo:metrics-build-${VERSION}

# create the experience build
resim builds create \
--image "public.ecr.aws/resim/open-builds/getting-started-demo:experience-build-${VERSION}" \
--version "experience-build-${VERSION}" \
--name "Experience Build ${VERSION}"\
--description "Demonstration build to show experiences builds" \
--branch "getting-started-demo-branch" \
--project "ReSim Getting Started Demo" \
--system "Getting Started Demo System" \
--auto-create-branch

# create the metrics build
resim metrics-build create \
--image "public.ecr.aws/resim/open-builds/getting-started-demo:metrics-build-${VERSION}" \
--name "Metrics build for Getting Started Experience" \
--project "ReSim Getting Started Demo" \
--version "metrics-build-${VERSION}"
