from aws_cdk import(
    Stack,
    aws_ssm as ssm,
)
from constructs import Construct

# For each task, create a NestedStack in the tasks subfolder and import here
from aws_serverless_ops.tasks.task_ecs_mysqlworker import MySqlWorker

class ServerlessOpsTasks(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        ops_ecs_cluster,    # the ECS cluster created previously
        ops_apigateway,     # the API GW created previouly
        settings,           # the settings object
        **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create the mysql worker task (db backup, restore)
        # Todo: have task self-update rights to Parameter Store /serverlessops/databases
        task_mysqlworker = MySqlWorker(self, settings['tasks']['fargate']['mysql_worker']['name'],
            # Referencing the cluster and api created via the core stacks above
            # See "Accessing resources in a different stack" from https://docs.aws.amazon.com/cdk/v2/guide/resources.html
            ops_cluster = ops_ecs_cluster,
            ops_api = ops_apigateway,
            docker_path = settings['tasks']['fargate']['mysql_worker']['image_path'],
            #ssm_keybase = "/serverlessops/databases"
        )
        
        # Create Parameter Store values for demo entries in the settings.yml
        # You may not want to manage user/pass info in this manner, but it is useful to see for a demo.
        # If managing the Parameter Store values outside CDK, I would have this section cut down to just 
        # setting the keybase and ensuring the task role has rights to it
        
        # This will loop through settings.yml's parameters: databases section and create keys at /serverlessops/databases in Parameter Store
        # This isn't well written, as it only handles strings, does no validation, and doesn't use the "secret" flag for the password
        for db in settings['parameters']['databases']:
            for env in settings['parameters']['databases'][db]:
                root_param = ssm.StringParameter(self, db+"/"+env,
                    parameter_name = "/serverlessops/databases/" + db + "/" + env,
                    string_value = "Settings for ServerlessOps DB worker task"
                )
                # Add task rights to use this parameter -- commenting out, call grants to the specific key not subkeys too. Moved to section below for now.
                # root_param.grant_read(task_mysqlworker.task_role)
                
                for key, value in settings['parameters']['databases'][db][env].items():
                    #print(f"{key} - {value}")
                    param = ssm.StringParameter(self, key,
                        parameter_name = "/serverlessops/databases/" + db + "/" + env + "/" + key,
                        string_value = value
                    )
                    # Add task rights to use this parameter
                    # param.grant_read(task_mysqlworker.execution_role)
                    param.grant_read(task_mysqlworker.task_role)
