from aws_cdk import (
    Stack,
    aws_apigateway as api_gw,
    aws_logs as logs
)
from constructs import Construct

class ServerlessOpsApi(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define Cloudwatch Logs group
        log_group = logs.LogGroup(self, "ServerlessOpsApiLogs")

        # For this example, we're just creating an empty REST API to be referenced by the rest of the stacks.
        # If you want to customize the settings,  add api keys, set deployment options, etc., here is the place.
        # See https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/README.html for more details
        api = api_gw.RestApi(self, "ServerlessOps",
            deploy_options = api_gw.StageOptions(
                access_log_destination = api_gw.LogGroupLogDestination(log_group),
                access_log_format = api_gw.AccessLogFormat.json_with_standard_fields(
                    caller = True,
                    http_method = True,
                    ip = True,
                    protocol = True,
                    request_time = True,
                    resource_path = True,
                    response_length = True,
                    status = True,
                    user = True
                )
            )
        )
        
        # !! needed? stops errors in building if tasks aren't defined
        api.root.add_method("ANY") 
        # self.api = api_gw.RestApi(self, "ServerlessOps")
        
        # Expose this to be callable from parent so apigw can be passed to other stacks
        self.api = api


        # Todo: Add APIGW CW logging
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/RestApi.html
        # - https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/StageOptions.html#aws_cdk.aws_apigateway.StageOptions