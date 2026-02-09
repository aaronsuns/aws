#!/usr/bin/env python3
import os
import aws_cdk as cdk
from aws_serverless_api.aws_serverless_api_stack import AwsServerlessApiStack

app = cdk.App()
AwsServerlessApiStack(app, "AwsServerlessApiStack",
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region are determined from the CLI or environment variables.
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION'),
    ),
)

app.synth()
