from aws_cdk import (
    CfnOutput,
    Duration,
    NestedStack,
    aws_lambda_python_alpha as lambda_alpha_,
    aws_lambda as _lambda,
    aws_ec2 as ec2,
)
from constructs import Construct

class MySqlUsersLambda(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, 
        asset_path,
        function_code,
        entry_point,
        target_vpc, 
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Note: because of the .from_lookup call, your account running CDK needs rights to query VPCs
        ops_vpc = ec2.Vpc.from_lookup(self, "ServerlessOpsVpc",
            vpc_id = target_vpc 
        )

        # Defines an AWS Lambda resource
        """
        This section uses the alpha version of cdk's lambda module:
        https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda_python_alpha/README.html

        Normally, you need to either package the function code or add in a bundler section
        to perform the necessary work (pip install, etc). The alpha module will spawn a
        local docker container, run the `pip install -r requirements`, and bundle for you.

        Be sure to include any python packages in the lambda/mysql-users/requirements.txt if
        you edit the Python file there to use any other dependencies.

        Note: `vpc` is required in this section for Lambda to access RDS, but you only need
        to specify `vpc_subnets` if you want to specifically target where the Lambda ENIs are
        created. By default, CDK uses best-practice values, and omitting `vpc_subnets` defaults
        to PRIVATE subnets (ones without an Internet Gateway).
        """
        mysql_user_lambda = lambda_alpha_.PythonFunction(self, 'MySqlUser',
            entry = asset_path,
            index=function_code,
            handler=entry_point,
            runtime=_lambda.Runtime.PYTHON_3_9,
            vpc = ops_vpc,
            timeout = Duration.minutes(5)
        )

        # Ensure we can assign ParameterStore rights by exposing the role
        self.role = mysql_user_lambda.role

        # Output relevant information user needs to reference later
        # 
        # CfnOutput(self,
        #     "Security group for MySQL Lamba Function for user adds. Be sure to add this to the MySQL database instance's security group",
        #     export_name="MySqlLambdaUserSecurityGroup",
        #     value=mysql_user_lambda.connections.security_groups
        # )
        