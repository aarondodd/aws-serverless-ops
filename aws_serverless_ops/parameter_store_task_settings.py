from aws_cdk import (
    Stack,
    aws_ssm as ssm
)
from constructs import Construct

class ServerlessOpsTaskParameters(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # From https://bobbyhadz.com/blog/aws-cdk-ssm-parameters#creating-ssm-parameters-in-aws-cdk
        # and https://catalog.us-east-1.prod.workshops.aws/workshops/d93fec4c-fb0f-4813-ac90-758cb5527f2f/en-US/walkthrough/python/sample/target-construct/ssm-parameter


        # Per https://docs.aws.amazon.com/cdk/api/v1/docs/aws-ssm-readme.html 
        # how to grant a role rights to read (need to grant the ECS task execution role if expecting worker.py to query)
        # param.grantRead(role)