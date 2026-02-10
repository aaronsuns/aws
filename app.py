#!/usr/bin/env python3
import os
import aws_cdk as cdk
from video_processing.video_processing_stack import VideoProcessingStack


app = cdk.App()

# Stage controls logical environment (dev/stage/prod). In a real multi-account
# setup you typically deploy each stage to a separate AWS account and/or region.
stage = os.getenv("STAGE", "dev")

VideoProcessingStack(
    app,
    f"VideoProcessingStack-{stage}",
    stage=stage,
    # Account/Region are determined from the CLI or environment variables.
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()
