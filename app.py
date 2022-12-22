#!/usr/bin/env python3
import os
import yaml
import aws_cdk as cdk

from aws_serverless_ops.serverless_ops_tasks import ServerlessOpsTasks

# The core stacks we'll create
from aws_serverless_ops.api_gateway import ServerlessOpsApi
from aws_serverless_ops.ecs_cluster import ServerlessOpsEcs

# Place referenced common settings in settings.yml
with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)

# ASSUMPTIONS
# 1. VPC should already exist and be specified in the settings.yml file.
# 2. VPC specified either has the resources being accessed, or routing and name resolution to those resources

# Todo:
# - create APIGW separately and pass to subsequent stacks
# - stub how to add rights to the worker task role
# - stub how to automate adding worker security group to other SGs

app = cdk.App()

# ops_api and ops_cluster will be two distinct stacks, since it is likely the settings
# for those will change less often than the defined tasks and they may be re-used by
# other components, so we don't want to co-mingle the tasks we run with the core infra
# 
# If you have an existing cluster and/or APIGW, you can replace these with a lookup
# call to query your environment and return the object, to then pass to the tasks.
ops_api = ServerlessOpsApi(app, "ServerlessOpsApi",
    # The env declarations are taken from the current CLI configuration
    # See login.sh for how I prep my environment before running cdk commands
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
)
ops_cluster = ServerlessOpsEcs(app, "ServerlessOpsCluster",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    target_vpc = settings['global']['target_vpc']
)

# We'll create one stack for all tasks and define the tasks themselves as NestedStacks
# There are two main benefits here:
# 1. In the event we have many tasks, each CloudFormation stack can only have 500 resources,
#    but a nested stack only counts as one in the main stack.
# 2. If we create each task as its own stack, we have to specify which to deploy and they'll each
#    show individually in the CloudFormation console. This might be desired in some cases, but not
#    for this demo
# See https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/NestedStack.html for more info
ops_tasks = ServerlessOpsTasks(app, "ServerlessOpsTasksStack", 
    ops_ecs_cluster = ops_cluster.cluster,
    ops_apigateway = ops_api.api,
    settings = settings,
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
)


app.synth()
