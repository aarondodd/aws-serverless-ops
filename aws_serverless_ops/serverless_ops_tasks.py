from aws_cdk import(
    Stack,
)
from constructs import Construct

# For each task, create a NestedStack in the tasks subfolder and import here
from aws_serverless_ops.tasks.task_ecs_mysqlworker import MySqlWorker

# We'll create one stack for all tasks and define the tasks themselves as NestedStacks
# There are two main benefits here:
# 1. In the event we have many tasks, each CloudFormation stack can only have 500 resources,
#    but a nested stack only counts as one in the main stack.
# 2. If we create each task as its own stack, we have to specify which to deploy and they'll each
#    show individually in the CloudFormation console. This might be desired in some cases, but not
#    for this demo
# See https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/NestedStack.html for more info
class ServerlessOpsTasks(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        ops_ecs_cluster,    # the ECS cluster created previously
        ops_apigateway,     # the API GW created previouly
        settings,           # the settings object
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        task_mysqlworker = MySqlWorker(self, settings['tasks']['fargate']['mysql_worker']['name'],
            # Referencing the cluster and api created via the core stacks above
            # See "Accessing resources in a different stack" from https://docs.aws.amazon.com/cdk/v2/guide/resources.html
            ops_cluster = ops_ecs_cluster,
            ops_api = ops_apigateway,
            docker_path = settings['tasks']['fargate']['mysql_worker']['image_path']
        )