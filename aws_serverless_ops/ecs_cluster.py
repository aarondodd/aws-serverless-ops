# import resource
# import string
from aws_cdk import (
    # Duration,
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
)
from constructs import Construct
import json

class ServerlessOpsEcs(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        target_vpc, 
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Todo: 
        # - ECS logs to cloudtrail (task stdout/err)
        
        # To create a dedicated VPC, uncomment below and comment the from_lookup block
        # ops_vpc = ec2.Vpc(self, "ServerlessOpsVpc")
        # Tag a VPC with serverless-ops = true and uncomment below to use that VPC
        # ops_vpc = ec2.Vpc.from_lookup(self, "ServerlessOpsVpc",
        #     tags = {"serverless-ops": "true"}
        # )

        # Note: because of the .from_lookup call, your account running CDK needs rights to query VPCs
        ops_vpc = ec2.Vpc.from_lookup(self, "ServerlessOpsVpc",
            vpc_id = target_vpc 
        )
        self.cluster = ecs.Cluster(self, "ServerlessOpsCluster", 
            vpc = ops_vpc
        )