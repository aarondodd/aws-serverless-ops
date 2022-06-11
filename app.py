#!/usr/bin/env python3
import os

import aws_cdk as cdk
import yaml
from aws_serverless_ops.aws_serverless_ops_stack import AwsServerlessOpsStack

# Place referenced common settings in settings.yml
with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)

# ASSUMPTIONS
# 1. VPC should already exist and be specified in the settings.yml file.
# 2. VPC specified either has the resources being accessed, or routing and name resolution to those resources

# Todo:
# - create APIGW separately and pass to subsequent stacks
# - create ECS cluster separately and pass to subsequent stacks
# - stacks for each fargate task
# - stub how to add rights to the worker task role
# - stub how to automate adding worker security group to other SGs

app = cdk.App()
AwsServerlessOpsStack(app, "AwsServerlessOpsStack", 

    fargate_vpc=settings['fargate']['vpc'],

    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
