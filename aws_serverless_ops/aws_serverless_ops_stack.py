import resource
import string
from aws_cdk import (
    Duration,
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_stepfunctions as sf,
    aws_stepfunctions_tasks as tasks,
    aws_apigateway as api_gw
)
from constructs import Construct
import json
# from os import path
from aws_cdk.aws_ecr_assets import DockerImageAsset

class AwsServerlessOpsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        fargate_vpc, 
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Todo: 
        # - ECS logs to cloudtrail (task stdout/err)
        
        #https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ecr_assets/README.html
        mysql_worker_image = DockerImageAsset(self, "MySqlWorker",
            directory="docker/mysql-worker"
            # directory=path.join(__dirname, "docker/mysql-worker")
        )

        # To create a dedicated VPC, uncomment below and comment the from_lookup block
        # ops_vpc = ec2.Vpc(self, "ServerlessOpsVpc")
        # Tag a VPC with serverless-ops = true and uncomment below to use that VPC
        # ops_vpc = ec2.Vpc.from_lookup(self, "ServerlessOpsVpc",
        #     tags = {"serverless-ops": "true"}
        # )
        ops_vpc = ec2.Vpc.from_lookup(self, "ServerlessOpsVpc",
            vpc_id = fargate_vpc 
        )
        ops_cluster = ecs.Cluster(self, "ServerlessOrchestrationCluster", 
            vpc = ops_vpc
        )

        mysql_worker_task = ecs.FargateTaskDefinition(self, "MysqlWorkerEcsTask",
            memory_limit_mib = 512,
            cpu = 256
        )

        mysql_worker_task_container = mysql_worker_task.add_container("MysqlWorkerContainer",
            image=ecs.ContainerImage.from_docker_image_asset(mysql_worker_image)
        )

        sf_task_mysql_worker = tasks.EcsRunTask(self, "RunMySqlWorker",
            integration_pattern = sf.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            cluster = ops_cluster,
            task_definition = mysql_worker_task,
            launch_target = tasks.EcsFargateLaunchTarget(platform_version=ecs.FargatePlatformVersion.LATEST),
            heartbeat = Duration.seconds(600),
            container_overrides = [tasks.ContainerOverride(
                container_definition = mysql_worker_task_container,
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
        sf_task_mysql_fail = sf.Fail(self, "MySqlWorkerFail",
            cause = "job failed",
            error = "Task returned error"
        )

        # Success State, here is where you'd put logic for further action to take when the job completes, if desired.
        # For demo, just logging a message
        sf_task_mysql_success = sf.Succeed(self, "MySqlWorkerSuccess",
            comment = "job complete" 
        )

        # Create StepFunction chain of states
        sf_mysql_worker_definition = sf_task_mysql_worker.next(sf.Choice(self, "JobComplete?")
            .when(sf.Condition.string_equals("$.status", "FAILED"), sf_task_mysql_fail) # change "FAILED" to whatever failure message you're sending back from the container
            .when(sf.Condition.string_equals("$.status", "job complete"), sf_task_mysql_success) # change "job complete" to whatever success message you're sending back from the container
            .otherwise(sf_task_mysql_fail) # for demo purposes, just failing if no replies are known
        )


        # Logging info
        sf_mysql_worker_logs = logs.LogGroup(self, "MySqlWorkerLogs")

        # Create StepFunction
        sf_mysql_statemachine = sf.StateMachine(self, "MySqlWorkerStateMachine",
            definition =  sf_mysql_worker_definition,
            timeout = Duration.days(1),
            logs = sf.LogOptions(
                destination = sf_mysql_worker_logs,
                level = sf.LogLevel.ALL,
                include_execution_data = True
            )
        )
        # Ensure task can report its heartbeat status back to StepFunctions
        sf_mysql_statemachine.grant_task_response(mysql_worker_task.task_role)

        # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_apigateway/RestApi.html
        api = api_gw.RestApi(self, "ServerlessOps")

        # By default, APIGW doesn't create a role, create one to use for StepFunction calls (Integration Request)
        db_iam_role = iam.Role(self, "ServerlessOpsDbWorkerRole",
            assumed_by = iam.ServicePrincipal("apigateway.amazonaws.com")
        )
        # Grant necessary rights to the APIGW role
        sf_mysql_statemachine.grant_start_execution(db_iam_role)
        sf_mysql_statemachine.grant_start_sync_execution(db_iam_role)
        sf_mysql_statemachine.grant_read(db_iam_role)
        
        # Create APIGW resources and methods for /db and /db/backup
        db_resource = api.root.add_resource("db")
        db_backup_resource = db_resource.add_resource("backup")
        db_backup_method_request_template = {
            "input":           "$util.escapeJavaScript($input.json('$'))",
            "stateMachineArn": sf_mysql_statemachine.state_machine_arn
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
                            # response_parameters = {
                            #     "method.response.header.Content-Type": "'application/json'"
                            # },
                            # response_templates = { "application/json": json.dumps(db_backup_status_response_template, indent=4) }
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