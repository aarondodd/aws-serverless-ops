# Serverless Ops Demo

**WORK IN PROGRESS!** 

> Draft v0.01, not fully tested or documented, but works in my account :-D. If you do try this and have problems, feel free to open an Issue.
> ToDos:
> - Cloudwatch Logs go to various logstreams, need to adjust CDK to be more organized
> - Need CDK to output all the settings the user will need (ECS Cluster ID, etc)
> - Prior example fed all parameters into each request, refactored to use ParameterStore, need to clean up the steps listed
> - SSM RunDocument to show API-GW fronting an existing automation not yet coded
> - Values like passwords should be encrypted in Parameter Store and when passed between StepFunction steps, but not yet implemented.
> - Common steps, like Parameter Store lookups, could be a dedicated function called by StepFunction before invoking Lambda or Fargate, but not yet refactored that way 

## What the heck is this?

This is an example design and sample code for running operational tasks in using AWS serverless services. It is not a best-practice solution for particular job types (in fact, there are better, more modern ways for the examples used here), but a guide for how various AWS services can be used together from an operations' team mindset.

Deploying this CDK project will create:
1. An ECS cluster configured for Fargate use
2. An ECS/Fargate task that can take a MySQL backup from an RDS instance and store it on an S3 bucket
3. A Lambda Function that can change the password for a user on a MySQL instance 
4. A StepFunction that orchestrates the ECS/Fargate task
5. [PENDING] orchestrate the Lambda Function via StepFunction
6. An API Gateway that can trigger the StepFunction

## But, why?

Operational Excellence in cloud hosting is a journey for many teams, especially when managing large environments actively migrating/re-platforming from on-prem where a mix of scripts and automation tools have grown organically over time. Often, the easiest approach is to spin up an EC2 instance (a.k.a. "jumpbox") and run operations tasks from that. Over time, this becomes a scalability, as well as cost, issue as more are spun up to meet demand and resources can sit idle during off-hours.

The goal is to give an example path forward for right-hosting tasks in the most cost-effective, least-burdensome manner, with approaches that can be reused as teams move to more modern, native cloud designs.

## Okay, how?

Similar to ["The Strangler Pattern"](https://martinfowler.com/bliki/StranglerFigApplication.html) for slowly peeling off layers of a monolithic application into microservices, this approach how to move common operations tasks to various serverless compute services to be run:

1. on demand by the operations engineers
2. on demand in a self-service model by peers/customers of the operations engineers
3. on a schedule
4. in response to events

## Cool, using which services and technologies?

A mix will be shown in this demo, but the full stack is not required, so don't be scared off by the listing of services. The point is to highlight how each can play a role based on particular use-cases. Also, unless otherwise mentioned, you can pretty much use any scripting language you wish (within reason, you [cow](https://bigzaphod.github.io/COW/) weirdos...).

### The stack

Below are all of the technologies this demo uses.

**AWS API Gateway**
A serverless API service fronting the architecture.

Use-case(s) here:
- As an API layer: presenting a documented call/response structure to end-users/customers for self-service execution of tasks and querying of status
- As an abstraction layer: offers the ability to change the backend used when a request comes in without affecting the caller. I.e., you can send requests to a lifted-and-shifted application on EC2, then slowly migrate the calls to Lambda Functions or such over time, without changing the workflow of the initiator of the request.
- As a translation layer: the requests and responses can be transformed on the fly, allowing you to mimic prior API-based orchestration systems to ease porting over integration points, allowing you to refactor slwoly over time. I.e., if your team uses tools like RunDeck where partner teams call its API directly, you can reasonably mimic that workflow, lessening the burden on those partner teams.

Completely optional to use in this demo, other methods for executing/tracking will be shown.

**AWS StepFunctions**
A serverless workflow orchestration service. You can create automated workflows to integrate various services and take action based on the state changes between each step.

Use-case(s) here:
- The orchestration of the steps required to complete an operations tasks (such as validating input passed, looking up attributes, calling an ECS/Fargate task, branching based on success/failure, sending notifications, etc.)

Semi-optional to use in this demo, but highly recommended to explore. Some example tasks will assume a StepFunction has executed them and rely on it, although you could easily alter the examples to be self-contained.

**AWS Lambda Functions**
A serverless, event-driven compute service. You can create discrete functions and tie them together, paying for only the execution time of that function (plus storage costs).

Use-case(s) here:
- Tasks that run quickly and  don't require a lot of local storage, such as changing a user password in a database

If the type of task you wish to run can be contained within a Lambda Function, it may be the most cost-effective service to leverage. However, almost anything you can run in a Lambda Function can also be run on ECS/Fargate (below), especially with Lambda's [containers support](https://aws.amazon.com/about-aws/whats-new/2020/12/aws-lambda-now-supports-container-images-as-a-packaging-format/).

**AWS Elastic Container Service (ECS)/Fargate**
[AWS Fargate](https://aws.amazon.com/fargate/) is a serverless, pay-as-you-go compute engine that lets you focus on building applications without managing servers. AWS Fargate is compatible with both [Amazon Elastic Container Service (ECS)](https://aws.amazon.com/ecs/?pg=ln&sec=hiw) and [Amazon Elastic Kubernetes Service (EKS)](https://aws.amazon.com/eks/?pg=ln&sec=hiw).

You package your task into a container with all dependencies, define the task, and let AWS manage the infrastructure, paying only for what you consume (plus storage costs).

Use-case(s) here:
- Execution of longer-running tasks or tasks requiring more local storage, such as database backups.

This is a core part of the demo.

**AWS Elastic Container Registry (ECR)**
A fully managed container repository.

Use-case(s) here:
- To store the containers used for ECS/Fargate and/or container-based Lambda Functions

Optional to learn for the demo, but ECR is a foundational part of the demo workflow.

**AWS CloudWatch, CloudWatch Logs**
Application and infrastructure monitoring service. CloudWatch stores all metrics for compute and other services, which can be tied to rules for triggering other actions (think an infrastructure event bus). CloudWatch Logs store logfiles from compute and application sources and provides a query interface for filtering results.

Use-case(s) here:
- Store the STDOUT and STDERR of ECS/Fargate tasks
- Store the output of Lambda functions
- Track the performance of task executions

Optional part of this demo, but highly recommended to explore. The tasks and related services of this demo will leverage CloudWatch regardless. If you ever need to debug what's going on, CloudWatch Logs is where you'll find the output.

**AWS Lambda Functions**
[PENDING / TBD] [AWS Lambda](https://aws.amazon.com/lambda/) is a serverless, event-driven compute service that lets you run code for virtually any type of application or backend service without provisioning or managing servers

Use-case(s) here:
- For quick-running tasks (under 15 minutes) with minimal local storage requirements

Required. This is a core part of the demo (example function TBD).

**AWS Systems Manager Parameter Store**
A secure, hierarchical storage for configuration data management and secrets management. Using Parameter Store decouples job configuration from job definition, allowing you to centrally and securely manage things like usernames, host names, etc.

Use-case(s) here:
- Central place for user/server information

Optional to learn, but highly recommended. Most tasks shown here also show passing in parameters for testing, and there are other possible technologies (HashiCorp Vault, etc.).

**Python**
Python is a widely-used general-purpose programming language. It is one of the [officially supported](https://aws.amazon.com/developer/tools/) programming languages for the AWS Software Development Kit (SDK), allowing you to import existing modules to perform actions against AWS services (such as creating S3 buckets).

Use-case(s) here:
- As the Lambda Function runtime
- As the wrapper script for ECS/Fargate tasks being invoked by Step Functions

You don't need to know Python to use this demo. If you have any scripting experience, you should be able to read the code to understand what it does. For your own use, any supported language can be used. It is recommended to leverage a language the [AWS SDK supports](https://aws.amazon.com/developer/tools/).

**Bash**
Bash is a common shell on Linux and popularly used for shell scripting.

Use-case(s) here:
- As many existing operations tasks are written in languages like Bash, this demo will show how to continue leveraging them.

I would personally encourage learning a language like Python or Node to take advantage of reusable modules and object-oriented approaches.

Note: AWS Lambda does not natively offer a runtime for Bash. If you wish to run Bash scripts in Lambda, you can [create a custom runtime](https://docs.aws.amazon.com/lambda/latest/dg/runtimes-walkthrough.html) for this.

**AWS Cloud Development Kit**
The [AWS Cloud Development Kit](https://aws.amazon.com/cdk/) (CDK) allows you to take a programmatic approach to modeling applications and infrastructure in AWS. Unlike declarative template-based methods like AWS CloudFormation and Teraform, CDK can synthesize an environment using common programming languages.

Use-case(s) here:
- This demo is a CDK-based application that generates and executes CloudFormation templates

It is required to install the [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) to run this demo, but not to use the actual pieces once deployed. It is recommended to run through the [Working with the AWS CDK in Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html) page.

**AWS CloudFormation**
AWS [CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) is an infrastructure-as-code service and template language for modeling your AWS environment declaratively.

Use-case(s) here:
- The AWS CDK generates and deploys CloudFormation Templates (CFTs) to create this demo

Optional to learn for this demo.

**Docker**
A technology for creating portable, self contained application containers that include a minimal OS and all required libraries to execute the workload.

Use-case(s) here:
- The ECS/Fargate task is deployed as a Docker image.

Optional to know for running this demo, but required if following this workflow. It is recommended to understand how Docker works, especially when creating your own containers to deploy.  For this demo, the Docker container is automatically built and deployed by the CDK. You can adjust the existing files in the CDK project's docker/mysql-worker folder and run a `cdk deploy` without having to interact with the Docker toolset directly.

# Using this Demo

Note of caution: as will be highlighted several times, the passing of parameters into the task (such as user/password) are for demonstration purposes, but pose a security risk as they will be logged and retrievable by anyone with rights to read the logs or job status. Once comfortable with the services in use, you'll want to leverage AWS Parameter Store or such to store the values. An example for how this would work is also included.


## Deploying the infrastructure

### Pre-requisites

If you wish to see the "db_backup" job actually take a database backup and send it to S3, then:

1. You need an S3 bucket to exist before running the task. After running `cdk deploy` you will need to grant the ECS Task Execution role rights to write to that S3 bucket.
2. You need an RDS MySql instance and database existing. After running `cdk deploy` you will need to add the ECS/Fargate security group to the RDS security group allowing ingress port 3306 traffic.
3. You will need to ensure the subnets chosen for this demo are able to route traffic to the RDS instance's subnets (if they're separate).

You can run the `cdk deploy` as described below without these. There are also steps to do a "dry run" execution of the tasks, like "db_backup", which triggers the task with a dummy flag that skips the actual calls for connecting to things RDS and S3. The "dry run" method allows you to see the infrastructure in place and how it would work, without creating/connecting to upstream systems/services. 

### Installing the AWS Cloud Development Kit (CDK)

Please follow the public guide [Working with the AWS CDK in Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)

### Getting the demo code

Perform a Git checkout of this repository.

### Adjusting the demo to your environment

#### Update settings.yml

All of the customizable settings are in the file `settings.yml`. Below are the sections to adjust.

Target VPC:
```
global: 
  target_vpc: &target_vpc vpc-076e905b3e931d519
```
Adjust `target_vpc` to be the VPC ID where ECS/Fargate should configure its tasks for connectivity. This needs to be a VPC with routable access to the MySQL instance the tasks will connect to.

ECS/Fargate Task:
```
tasks:
  fargate:
    mysql_worker: # the backup/restore task
      name: MySqlWorkerTask
      image_path: "docker/mysql-worker" # place all docker build files here
```
You may leave the above as is. For reference, the subfolder "docker" contains the docker files/scripts for packaging up into images. The docker/mysql-worker folder contains the demo code that runs in ECS/Fargate for this example (CDK handles the Docker build and push to ECR automatically).

Parameters: This section is NOT for production use/tracking of settings and ONLY for ease of demo creation. It is present here as the CDK will create for you these values in AWS Systems Manager Parameter Store. In practice, you should manage Parameter Store separaretly and more securely (usernames and passwords should never be commited to Git). 

You may omit using this section and instead manually create the appropriate Parameter Store values (just be sure to update the ECS Task Role with appropriate rights to your key paths)
```
# parameters: Top level path
#   databases: section for tasks that need db-related info
#     db_name: db name (the database within RDS)
#       env_name: the environment, combined with the db_name this is the unique db combo used for task lookups
parameters:  # The values for tasks to pull from ParameterStore instead of feeding in directly
  databases:
    mydatabase: # key heading, demo code will look for heading/env
      demo:   # calling this demo environment "demo", could be dev, prod, etc.
        db_host: "MyAuroraMySqlCluster.cluster-XXX.us-east-1.rds.amazonaws.com"
        db_port: "3306"
        db_name: "mydatabase"
        db_user: "myuser"
        db_pass: "mypassword"
        s3_bucket: "mys3bucket"
        s3_path: "mys3path"
```
Adjust the above values to represent the MySQL instance that you will target with this demo and the S3 bucket where you wish to store the backups. ***If you prefer*** *(and is more secure) let CDK deploy dummy values and then go to the AWS Console / Systems Manager / Parameter Store and adjust there. This will have CDK create the proper permissions while you avoid storing creditials in clear text here.*

Note: the section under `databases:` is headed by the name of the database itself, in this case `mydatabase` is the database name. The section under that, `demo:` in this case, is an environment flag. These two together form the unique entry for the task to perform a lookup against in Parameter Store (at databases/databasename/env) for retrieving the values.

For the password-change Lambda (TBD):
```
  database_users:
    classicmodels: # key heading, demo code will look for heading/env
      demo: # calling this demo env "demo", could be dev, prod, etc.
        mary: # user name
          password: "Password02"
          grant: "GRANT ALL PRIVILEGES TO 'mary'@'%';" # Yes, there are much better ways to do this whole section :)
        frank:
          password: "Password03"
          grant: "GRANT ALL PRIVILEGES TO 'frank'@'%';"
```
Adjust as desired. Note: again, this is NOT best practice for storing credentials and is solely for making the demo easier to work with.

### Update S3 permissions

Skip if just running the demo with the "dryrun" values.

This demo does not create an S3 bucket for you. The steps below allow the Fargate task to access an existing bucket. If you do not already have an S3 bucket, then create one first.

1. In the `cdk deploy` output, look for the line `ECS Task Role:`. 
2. In the AWS Console, go to IAM / Roles and edit the role listed by that output. 
3. Choose to add permissions and either create a new policy or create an in-line policy. Add the following, changing `MYBUCKET` to the actual bucket name:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:DeleteObjectTagging",
                "s3:GetObjectRetention",
                "s3:DeleteObjectVersion",
                "s3:GetObjectVersionTagging",
                "s3:GetObjectAttributes",
                "s3:RestoreObject",
                "s3:DeleteObjectVersionTagging",
                "s3:GetObjectLegalHold",
                "s3:GetObjectVersionAttributes",
                "s3:GetObjectVersionTorrent",
                "s3:PutObject",
                "s3:GetObjectAcl",
                "s3:GetObject",
                "s3:GetObjectTorrent",
                "s3:AbortMultipartUpload",
                "s3:GetObjectVersionAcl",
                "s3:GetObjectTagging",
                "s3:PutObjectTagging",
                "s3:GetObjectVersionForReplication",
                "s3:DeleteObject",
                "s3:GetObjectVersion"
            ],
            "Resource": [
                "arn:aws:s3:::MYBUCKET/*",
                "arn:aws:s3:::MYBUCKET"
            ]
        }
    ]
}
```

### Update MySQL Security Group

Skip if just running the demo with the "dryrun" values.

This demo does not create an RDS/MySQL instance for you. The steps below add rights from the Fargate task to an existing instance.

1. In the `cdk deploy` output, look for the line `Fargate Security Group:`.
2. In the AWS Console, go to RDS / Databases and click on the database instance you're targetting this demo towards.
3. Under "Connectivity and Security" in the bottom pane, look for "VPC Security Groups".
4. Click on the security group associated with your RDS instance.
5. Edit the inbound rules and add a rule for TCP port 3306 from the security group ID from the CDK output (step 1 above).

## Testing the examples

### Triggering the "db backup" job directly from ECS/Fargate

#### What the job does

Before running the below example, understand what is happening. Open the AWS Console and go to Elastic Container Service. 

Under "Clusters" you will see one called "ServerlessOpsCluster-XXX". This is the ECS cluster the demo will use. Click through and review the configuration of the cluster. There will be nothing listed in the "Tasks" pane of the cluster until an active task is kicked off in the steps below.

Click on "Task Definitions" from the left-hand side. You will see one called "ServerlessOpsTasksStackMySqlWorkerTaskMysqlWorkerEcsXXXX". This is the definition for the MySQL backup task below. Click on this task and you should see another entry ending in a colon and number. These are "revisions". You can, at any time, call a task with a specific :# designation to run that version (more below). If you edit the CDK project's mysqlworker and deploy again, you'll see new versions show up here.

Click on the task definition. The `Task role` is the IAM role used by the ECS/Fargate container to access AWS services (such as uploading to S3). This is the role you adjusted to add rights to your S3 bucket above. The `Task execution role` is used by the ECS service to orchestrate the Fargate task (such as pulling docker images from ECR and pushing logs to CloudWatch).

Scroll down to "Container Definitions". Here, you'll see `MySqlWorkerContainer`. This is the container that will run the actual MySQL backup logic. Expand it. If you wish, you can have the same container used in different Task Definitions and adjusting the settings to suit the job. One method is to leverage the `Environment Variables` section to set what should be done. We leave this blank for the demo as we're going to pass these in (or pull from Parameter Store) so that the same task can be used for any number of database instances.

If you wish, click "Create new revision" to see all the settings you can define.

When finished, cancel out of the AWS console sections and open the code repository for this demo.

The container image you just saw listed in the Task Definition in the AWS console was built by CDK and pushed to ECR for you. The code on the image is the [worker.py](docker/mysql-worker/worker.py) from the `docker/mysql-worker` folder in this repo. Take a look at the file as each section is documented. A high level flow of what it does is:

1. ECS/Fargate sets environment variables as defined in the `run-task` call you'll see below.
2. ECS/Fargate invokes worker.py as the entrypoint.
3. Worker.py checks if required environment variables are set. If required ones are missing, it aborts. If required ones are present, but optional ones are not, it checks Parameter Store.
4. Once worker.py has the proper variables initialized, it branches based on the job-type requested (`db_backup` is the only one coded for this demo, but you can see how to add more calls). Best practice is to keep the tasks single-purpose or group task types that have the same requirements/dependencies. In this case, a `db_backup` and `db_restore` would likely have identical dependencies/resource requirements and only differ in settings, so they make sense to leverage the same container.
5. In the backup portion, worker.py spawns a shell to execute a pre-existing [db-backup.sh](docker/mysql-worker/db_backup.sh) Bash script. This shows how Python can be used as a wrapper, allowing you to leverage the AWS SDK (boto, for Python) to handle the AWS logic, and re-use existing shell scripts for specific tasks. The output of the Bash script is captured and fed back to ECS/Fargate for streaming to CloudWatch Logs.

Now, for the fun part:

#### Invoking ECS/Fargate From the AWS CLI

As you'll see, passing in the parameters each time can be cumbersome (especially for the Console method next) and **highly insecure**. This is being shown for testing purposes and to highlight what StepFunctions will be handling for you in the subsequent example.

This demo only supports passing all of the parameters when calling ECS/Fargate directly as those will use local ENV VARs within the ECS container. For the subsequent StepFunction and API Gateway invocations, only passing the job, db name, and db env are supported and will lookup using Parameter Store. 

If you wish to leverage Parameter Store instead in this example, ensure you have the proper values set (see "Adjusting the Demo for Your Environment" above) and follow the second code snippet example.

Anatomy of the calls used:

```
aws ecs run-task \ # The AWS CLI call to run an ECS task
  --cluster "XXX" \ # The ECS cluster to use (listed in CDK output)
  --task-definition "XXX" \ # The ECS task definition to call (listed in CDK output)
  --launch-type "FARGATE" \ # Run this as a serverless task
  --network-configuration "awsvpcConfiguration={subnets=[subnet-id1,subnet-id2],securityGroups=[sg-XXX],assignPublicIp=DISABLED}" \ # The networking configuration to use (you should choose private subnets from your VPC, and the security group listed in the `cdk deploy` output).
  --count 1 \ # Only run 1 of these tasks
  --overrides '{"containerOverrides": \ # Settings to run the task with, specifically our environment variables, see below
```

Anatomy of the `--overrides` section:
```
  [
    {
        "name": "MysqlWorkerContainer", # Container created for the task
        "environment": [ # ENV VARs to pass in
            {
                "name": "TASK_TOKEN_ENV_VARIABLE", # Used when called via StepFunctions, see that section for more info 
                "value": "localtest" # Use "localtest" for this example
            },{
                "name": "JOB_NAME", # See `worker.py` for branching strategy 
                "value": "db_backup" # For now, only `db_backup` is supported
            },{
                "name": "DB_HOST", # The MySQL instance FQDN
                "value": "MyAuroraMySqlCluster.cluster-XXX.us-east-1.rds.amazonaws.com" # For a dry-run without touching MySQL, use "dummy-dryrun" as the DB_HOST
            },{
                "name": "DB_NAME", # The MySQL DB to use
                "value": "classicmodels"
            },{
                "name": "DB_USER", # The MySQL user to use 
                "value": "admin"
            },{
                "name": "DB_PASS", # Password for above user
                "value": "XXX"
            },{
                "name": "DB_PORT", # The MySQL port used
                "value": "3306"
            },{
                "name": "S3_BUCKET", # Where to copy the backup
                "value": "MyBucket"
            },{
                "name": "S3_PATH", # Where in above bucket to place the backup
                "value": "testing"
            }
        ]
    }
```

1. Passing in all parameters directly (uses local ENV VARs in ECS/Fargate instead of Parameter Store calls). Be sure to specify appropriate subnets and security group in the `--network-definition` and adjust the `--overrides` portion below as needed:

```
aws ecs run-task \
  --cluster "ServerlessOpsCluster-ServerlessOpsCluster1FEF9222-Ne70UFGTXgmX" \
  --task-definition "ServerlessOpsTasksStackMySqlWorkerTaskMysqlWorkerEcsTask0E4C8206:9" \
  --launch-type "FARGATE" \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-0f1edafd33509f1e1,subnet-014b84600e1b97b0e,subnet-07b102797a74ec0ae],securityGroups=[sg-091789f7a26942807],assignPublicIp=DISABLED}" \
  --count 1 \
  --overrides '{"containerOverrides": [{"name": "MysqlWorkerContainer", "environment": [{"name": "TASK_TOKEN_ENV_VARIABLE", "value": "localtest"},{"name": "JOB_NAME", "value": "db_backup"},{"name": "DB_HOST", "value": "MyAuroraMySqlCluster.cluster-XXX.us-east-1.rds.amazonaws.com"},{"name": "DB_NAME", "value": "classicmodels"},{"name": "DB_USER", "value": "admin"},{"name": "DB_PASS", "value": "Password01"},{"name": "DB_PORT", "value": "3306"},{"name": "S3_BUCKET", "value": "serverlessops-db-backups"},{"name": "S3_PATH", "value": "testing"}]}]}'
```

2. Using Parameter Store instead:

```
aws ecs run-task \
  --cluster "ServerlessOpsCluster-ServerlessOpsCluster1FEF9222-Ne70UFGTXgmX" \
  --task-definition "ServerlessOpsTasksStackMySqlWorkerTaskMysqlWorkerEcsTask0E4C8206" \
  --launch-type "FARGATE" \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-0f1edafd33509f1e1,subnet-014b84600e1b97b0e,subnet-07b102797a74ec0ae],securityGroups=[sg-091789f7a26942807],assignPublicIp=DISABLED}" \
  --count 1 \
  --overrides '{"containerOverrides": [{"name": "MysqlWorkerContainer", "environment": [{"name": "TASK_TOKEN_ENV_VARIABLE", "value": "localtest"},{"name": "JOB_NAME", "value": "db_backup"},{"name": "DB_NAME", "value": "classicmodels"},{"name": "DB_ENV", "value": "demo"}]}]}'
```


Checking the status:



#### From the AWS Console

*This walkthrough is meant to show how to execute manually. It is not intended as how the task should normally be run since you'll be specifying parameters each time and the console method would be cumbersome.*

As you'll see, specifying the parameters each time is cumbersome. This walkthrough shows what the StepFunction does for you using generalized tasks and passing in what is needed to take action. Should you wish to rely on calling ECS directly and not use a StepFunction, you can create a TaskDefinition for each job and define the relevant parameters as part of that. This is NOT recommended as it would lead to a definition-per-job, but would be less required to input for kicking off each.

1. Open AWS Console
2. Switch to ECS service
3. Under "Clusters" choose "ServerlessOpsCluster-XXX" (where -XXX is the unique string appended to your deployment)
4. Navigate to "Tasks"
5. Choose "Run new task"
6. Configure:
   1. Launch Type: Fargate
   2. Operating System Family: Linux
   3. Task Definition: ServerlessOpsStackMySqlWorkerTask
   4. Revison: Latest
   5. Platform Version: Latest
   6. Cluster: ServerlessOpsCluster-XXX
   7. Number of Tasks: 1
   8. Task Group: blank
   9. Cluster VPC: choose the one you specified when deploying this demo
   10. Subnets: choose one specified when deploying this demo
   11. Security Groups: Select Existing and choose "ServerlessOpsTasksStack-MySqlWorkerTask..."
   12. Auto Assign Public IP: disabled
   13. Advanced Options: leave alone
   14. Container Overrides: here is where you'd specify what the StepFunction invocation, or a CLI invocation, would provide. In "Environment Variable Overrides" enter:
       1.  Key: TASK_TOKEN_ENV_VARIABLE, Value: localtest (this tells the task not to report back to StepFunction
       2.  Key: JOB_NAME, Value: db_backup
       3.  Key: DB_NAME, Value: classicmodels
       4.  Key: DB_HOST, Value: (the output from the CDK run)
       5.  Key: DB_PORT, Value: 3306
       6.  Key: DB_USER, Value: admin
       7.  Key: DB_PASS, Value: Password01
       8.  Key: S3_BUCKET, Value: (the S3 bucket you chose)
       9.  Key: S3_PATH, Value: (key prefix you prefer, i.e. "backups", or "backups/same-value-as-DB_HOST" etc.>
   15. Click "Run Task"



### Triggering the "db backup" job's StepFunction

[This section in progress]

#### From the AWS CLI

#### From the AWS Console

### Triggering the "db backup" job via API Gateway

[This section in progress]

#### From the AWS CLI

#### From the AWS Console