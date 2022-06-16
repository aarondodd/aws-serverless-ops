from aws_cdk import (
    # Duration,
    Stack
)

from aws_cdk.aws_ecr_assets import DockerImageAsset

from constructs import Construct

class MySqlWorker(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ecr_assets/README.html

        asset = DockerImageAsset(self, "MySqlWorker",
            directory=path.join(__dirname, "docker/mysql-worker")
        )


