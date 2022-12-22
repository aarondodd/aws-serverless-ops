from aws_cdk import (
    Duration,
    NestedStack,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
    aws_stepfunctions as sf,
    aws_stepfunctions_tasks as tasks,
    aws_ssm as ssm,
    aws_apigateway as api_gw
)
from constructs import Construct
import json
from aws_cdk.aws_ecr_assets import DockerImageAsset

class MySqlWorker(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, 
        ops_cluster,    # Object: The ECS cluster to be used
        ops_api,        # Object: The API Gateway to be used
        docker_path,    # String: The path to the docker image, from CDK root, i.e. "docker/mysql-worker"
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the docker image to be used by Fargate
        # This call will:
        # 1. build the image
        # 2. create a dedicated ECR
        # 3. deploy the image to the dedicated ECR
        # See https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ecr_assets/DockerImageAsset.html for more info
        #     particularly if you need to specify build args, etc.
        docker_image = DockerImageAsset(self, "MySqlWorker",
            directory = docker_path
            # directory="docker/mysql-worker"
        )

        # create the Fargate task
        fargate_task = ecs.FargateTaskDefinition(self, "MysqlWorkerEcsTask",
            memory_limit_mib = 512,
            cpu = 256
        )

        # assign the docker image to the Fargate task
        # For more logging info, see https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ecs/LogDriver.html#aws_cdk.aws_ecs.LogDriver
        # specifically, if you need to change the loggroup or prefix
        fargate_task_container = fargate_task.add_container("MysqlWorkerContainer",
            image = ecs.ContainerImage.from_docker_image_asset(docker_image),
            logging = ecs.LogDrivers.aws_logs(
                stream_prefix = "serverlessops-task-mysql"
            )
        )

        # Ensure fargate task can talk to Parameter Store by exposing the task execution role to be used when creating the parameters
        self.task_role = fargate_task.task_role
        self.execution_role = fargate_task.execution_role

        # Create the StepFunction task
        # The "environment" block is where container envvars are passed in. 
        # Be sure to keep the $$.Task.Token as that is how to send back the job status. 
        # For the rest, define as your worker.py in docker will accept. For this demo, we're passing in dummy 
        #   info and just validating it's been specified.
        # For a true deployment, sensitive information like user/pass should NOT be done this way. Check the
        #   demo version of worker.py to see how to leverage Parameter Store instead.
        sf_task = tasks.EcsRunTask(self, "RunMySqlWorker",
            integration_pattern = sf.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            cluster = ops_cluster,
            task_definition = fargate_task,
            launch_target = tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST),
            heartbeat = Duration.seconds(600),
            container_overrides = [tasks.ContainerOverride(
                container_definition = fargate_task_container,
                environment = [
                    tasks.TaskEnvironmentVariable(name="TASK_TOKEN_ENV_VARIABLE", value=sf.JsonPath.string_at("$$.Task.Token")),
                    tasks.TaskEnvironmentVariable(name="JOB_NAME", value=sf.JsonPath.string_at("$.job_name")),
                    tasks.TaskEnvironmentVariable(name="DB_NAME", value=sf.JsonPath.string_at("$.job_options.db_name")),
                    tasks.TaskEnvironmentVariable(name="DB_HOST", value=sf.JsonPath.string_at("$.job_options.db_host")),
                    tasks.TaskEnvironmentVariable(name="DB_PORT", value=sf.JsonPath.string_at("$.job_options.db_port")),
                    tasks.TaskEnvironmentVariable(name="DB_USER", value=sf.JsonPath.string_at("$.job_options.db_user")),
                    tasks.TaskEnvironmentVariable(name="DB_PASS", value=sf.JsonPath.string_at("$.job_options.db_pass")),
                    tasks.TaskEnvironmentVariable(name="S3_BUCKET", value=sf.JsonPath.string_at("$.job_options.s3_bucket")),
                    tasks.TaskEnvironmentVariable(name="S3_PATH", value=sf.JsonPath.string_at("$.job_options.s3_path")),
                ]
            )]
        )

        # Fail State, here is where you'd put logic to take when there's a failure, like sending an SNS notification.
        # For demo, just logging a message
        sf_step_fail = sf.Fail(self, "MySqlWorkerFail",
            cause = "job failed",
            error = "Task returned error"
        )

        # Success State, here is where you'd put logic for further action to take when the job completes, if desired.
        # For demo, just logging a message
        sf_step_success = sf.Succeed(self, "MySqlWorkerSuccess",
            comment = "job complete" 
        )

        # Create StepFunction chain of states
        st_definition = sf_task.next(sf.Choice(self, "JobComplete?")
            .when(sf.Condition.string_equals("$.status", "FAILED"), sf_step_fail) # change "FAILED" to whatever failure message you're sending back from the container
            .when(sf.Condition.string_equals("$.status", "job complete"), sf_step_success) # change "job complete" to whatever success message you're sending back from the container
            .otherwise(sf_step_fail) # for demo purposes, just failing if no replies are known
        )

        # Create the logging group
        sf_logs = logs.LogGroup(self, "/serverlessops/MySqlWorkerLogs")

        # Create StepFunction
        sf_statemachine = sf.StateMachine(self, "MySqlWorkerStateMachine",
            definition =  st_definition,
            timeout = Duration.days(1),
            logs = sf.LogOptions(
                destination = sf_logs,
                level = sf.LogLevel.ALL,
                include_execution_data = True
            )
        )
        # Ensure task can report its heartbeat status back to StepFunctions
        sf_statemachine.grant_task_response(fargate_task.task_role)

        # By default, APIGW doesn't create a role, create one to use for StepFunction calls (Integration Request)
        db_iam_role = iam.Role(self, "ServerlessOpsDbWorkerRole",
            assumed_by = iam.ServicePrincipal("apigateway.amazonaws.com")
        )
        # Grant necessary rights to the APIGW role
        sf_statemachine.grant_start_execution(db_iam_role)
        sf_statemachine.grant_start_sync_execution(db_iam_role)
        sf_statemachine.grant_read(db_iam_role)
        
        # Create APIGW resources and methods for /db and /db/backup
        db_resource = ops_api.root.add_resource("db")
        db_backup_resource = db_resource.add_resource("backup")
        db_backup_method_request_template = {
            "input":           "$util.escapeJavaScript($input.json('$'))",
            "stateMachineArn": sf_statemachine.state_machine_arn
        }
        db_backup_method = db_backup_resource.add_method("POST",
            api_gw.AwsIntegration(
                service = "states",
                action = "StartExecution",
                integration_http_method = "POST",
                options = api_gw.IntegrationOptions(
                    passthrough_behavior = api_gw.PassthroughBehavior.NEVER,
                    credentials_role = db_iam_role,
                    request_templates = { "application/json": json.dumps(db_backup_method_request_template, indent=4) },
                    integration_responses = [
                        api_gw.IntegrationResponse(
                            status_code = "200",
                            response_templates = { "application/json": "" } # you should define a template that returns a format you'll support, just passing through for the demo
                        )
                    ]
                )
            ),
            method_responses = [ 
                api_gw.MethodResponse(
                    status_code="200"
                ) 
            ]
        )

        # Create resources and methods for /db/backup/status
        # Mapping template for status responses, created as a string since we're making no transformations via CDK
        # The "context" block below is useful for debugging but probably too much sensitive info for a prod deployment
        db_backup_status_response_template = '''{ 
    "status": {
        "executionArn": $input.json('$.executionArn'),
        "output":       $input.json('$.output'),
        "startDate":    $input.json('$.startDate'),
        "status":       $input.json('$.status'),
        "stopDate":     $input.json('stopDate'),
        "traceHeader":  $input.json('traceHeader')
    },
    "context" : { 
        "account-id":                      "$context.identity.accountId",
        "api-id":                          "$context.apiId",
        "api-key":                         "$context.identity.apiKey",
        "authorizer-principal-id":         "$context.authorizer.principalId",
        "caller":                          "$context.identity.caller",
        "cognito-authentication-provider": "$context.identity.cognitoAuthenticationProvider",
        "cognito-authentication-type":     "$context.identity.cognitoAuthenticationType",
        "cognito-identity-id":             "$context.identity.cognitoIdentityId",
        "cognito-identity-pool-id":        "$context.identity.cognitoIdentityPoolId",
        "http-method":                     "$context.httpMethod",
        "stage":                           "$context.stage",
        "source-ip":                       "$context.identity.sourceIp",
        "user":                            "$context.identity.user",
        "user-agent":                      "$context.identity.userAgent",
        "user-arn":                        "$context.identity.userArn",
        "request-id":                      "$context.requestId",
        "resource-id":                     "$context.resourceId",
        "resource-path":                   "$context.resourcePath"
    }
}'''

        db_backup_status_resource = db_backup_resource.add_resource("status")
        db_backup_status_method = db_backup_status_resource.add_method("POST",
            api_gw.AwsIntegration(
                service = "states",
                action = "DescribeExecution",
                integration_http_method = "POST",
                options = api_gw.IntegrationOptions(
                    passthrough_behavior = api_gw.PassthroughBehavior.WHEN_NO_MATCH,
                    credentials_role = db_iam_role,
                    integration_responses = [
                        api_gw.IntegrationResponse(
                            status_code = "200",
                            response_templates = { "application/json": db_backup_status_response_template }
                        )
                    ]
                )
            ),
            method_responses = [ 
                api_gw.MethodResponse(
                    status_code="200"
                ) 
            ]
        )