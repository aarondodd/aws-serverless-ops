from webbrowser import get
import boto3
import os
import subprocess
import time
import json
import sys

"""
Demo wrapper script to show working with AWS StepFunctions and AWS ECS/Fargate tasks 
leveraging existing operations scripts (Bash, in this case).

Logic:
AWS StepFunction is called defining:
  - Type of task to run (db_backup or db_restore)
  - Required attributes (DB info and S3 paths, VPC networking so task can reach the database)
  - Task token (generated by StepFunction) so this script can report back its status
AWS ECS task then:
  - reads in the passed variables (set as ENV variables on task launch by StepFunction)
  - branches appropriately (back or restore)
  - dumps MySQL DB (only supported engine for this demo) locally (call Bash script also gzips it)
  - uploads the dump to S3
  - reports success or failure back to the calling StepFunction

Demo limitations:
As this is to show the flow and functionality, below are some areas to consider before extending this for production.
- Local storage: Tasks start with ~20G of storage, although up to ~200G can be specified (varies as the total also includes the size of the container image)
- Tasks support EFS attachments, it may be desirable to add at least a single-zone EFS for dumps to write to before being uploaded to S3
  - If using EFS, add logic to delete the dump after its uploaded to save costs
- Timeouts: StepFunctions by default wait 1 year for the task complete before terminating it. Any issues with this task may cause the SF to persist that long.
  - For the demo, the associated StepFunction has been set to time out after 600 seconds. If a backup takes longer than 600 seconds, you can increase the timeout or see below:
  - StepFunctions support a heartbeat for the task to send back letting it know its still in progress. This should be used before implementing demo workflow fully.
- Status: as this task calls the mysql commands, it is not tracking the progress of the job for reporting back (it does capture STDOUT/STDERR)
  - If a task is long running, i.e. a large backup, capturing the mysql output and determing a status and ETA may be useful if you want the callers to be able to see progress.
  - Such status could then be reported, such as to DynamoDB, so that an associated "get_status" API call can be performed by those invoking this function

Best practices changes:
- The functions here would likely be common to more tasks and should be modules imported by this worker.py instead of written here.
- For a production deployment, the use of passing in the ENV vars (user/pass/etc) should only be for debugging. Use Parameter Store, Secrets Manager, DynamoDB, or some other means of querying for values instead.
"""



def send_error(error_cause, error_msg):
    """Send error back to calling StepFunction"""

     # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html#SFN.Client.send_task_failure
    if stepfunction_token != "localtest":
        print("Sending error to StepFunction")
        client = boto3.client('stepfunctions')
        response = client.send_task_failure(
            taskToken=stepfunction_token,
            error=str(error_msg),  # Since passing in "e" for debugging of the exception, ensure these are strings
            cause=str(error_cause)
        )
        print(f"Error has occured, aborting. Cause: {error_cause}, message: {error_msg}")
        sys.exit(1)
    else:
        print(f"Reporting error to Stepfunction skipped as token passed is a tester: {stepfunction_token}")
        print(f"Error has occured, aborting. Cause: {error_cause}, message: {error_msg}")
        sys.exit(1)

def send_success(output):
    """Send success and output back to calling StepFunction"""

    # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html#SFN.Client.send_task_success
    if stepfunction_token != "localtest":
        print("Sending success back to StepFunction")
        client = boto3.client('stepfunctions')
        response = client.send_task_success(
            taskToken=stepfunction_token,
            output=json.dumps(output)
        )
    else:
        print(f"Stepfunction status skipped as token passed was a tester: {stepfunction_token}")

# def send_heartbeat():
    #"""Send keep-alive back to calling StepFunction so this task isn't forcibly killed if reaching time-out setting"""
    # TBD, will be needed if this will be a long running task AND if StepFunction is configured with a timeout.
    #client = boto3.client('stepfunctions')
    #response = client.send_task_heartbeat(
    #    taskToken=stepfunction_token
    #)


def get_parameter(keyname):
    """Get a value from Parameter Store"""
    ssm = boto3.client('ssm')
    try:
        response = ssm.get_parameter(Name=keyname,WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        send_error(e, "Error trying to retrieve parameter " + keyname + " from Parameter Store")


def db_backup(db_host, db_port, db_user, db_pass, db_name, s3_bucket, s3_path):
    """Perform MySQL backup"""
    errors = ""
    timestamp = time.strftime('%Y-%m-%d-%I')


    if db_host != "dummy-dryrun":
        """
        In this example, the ops team is re-using existing scripts, for which Python is just a wrapper.
        Calling a subprocess for the bash script and polling for it to end
        For errorhandling to work, ensure the bash script properly exits zero/nonzero
        """
        process = subprocess.Popen(['bash', './db_backup.sh', db_host, db_port, db_user, db_pass, db_name, s3_bucket, s3_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while True:
            outs = process.stdout.readline()
            errs = process.stderr.readline()
            if outs:
                print(outs.strip())
            if errs:
                print(errs.strip())
                errors = errors + errs.strip()

            result = process.poll()
            if result is not None:
                break
        if process.returncode != 0:
            send_error("db_backup script encounter errors", errors)
        else:
            output['status']="job complete"
            output['message']="Database " + db_name + " from host " + db_host + " backed up on " + timestamp
            send_success(output)
    else:
        output['status']="job complete"
        output['message']="Dry run flag passed, no backup performed."
        send_success(output)

# Main logic when called
if __name__=="__main__":
    """
    Get common required ENV variables
    In all workflows, the following ENV vars are always required:
    - TASK_TOKEN_ENV_VARIABLE: the StepFunction-generated token to send output/error/status back in
      For debugging, pass in "localtest" as the value. To forgoe StepFunction use, remove all references
      to the value
    - DB_NAME: the name of the database to backup. If relying on ParameterStore, this, in conjunction with
      "DB_ENV" make up the unique path for ParameterStore lookups (see lower in the script for details).
    If using ParameterStore (recommended), only the above 3 mentioned ENV vars are needed.
    For debugging, you can call ECS/Fargate or the StepFunction passing in the following as well (NOT FOR PROD USE, INSECURE)
    - DB_HOST: the DNS name of the RDS instance (demo assumes you have routing and Security Groups properly configured). Pass in "dummy-dryrun" to skip calls to MySql for testing the ECS/Fargate invocation itself.
    - DB_PORT: the port RDS listens on (3306 by default)
    - DB_USER: the user with rights to perform the db operations
    - DB_PASS: password for the above user
    - S3_BUCKET: the S3 bucket to store the backup (demo assumes you've granted the Fargate Task Role rights)
    - S3_PATH: the prefix for where on the S3 bucket to store the backup
    """
    try:
        stepfunction_token = os.environ['TASK_TOKEN_ENV_VARIABLE']
    except:
        print("Environment variable TASK_TOKEN_ENV_VARIABLE is missing, aborting.")
        print("To execute without using a StepFunction, set TASK_TOKEN_ENV_VARIABLE to 'localtest' or edit this script.")
        sys.exit(1)

    try:
        job_name = os.environ['JOB_NAME']
        #print(f"DEBUG: job name is {job_name}")
    except Exception as e:
        print("Environment variable JOB_NAME is missing, aborting")
        send_error(e, "Environment variable JOB_NAME is missing, aborting")
        #sys.exit(1)

    # Initializing the output dictionary (I hate blank messages when debugging)
    output = {
        "status": "none yet",
        "message": "output initialized, not populated"
    }

    # Parse job name and branch appropriately
    if job_name.lower() == 'db_backup':
        try: # get required env vars
            db_name = os.environ['DB_NAME'] 

        except Exception as e:
            # print("Error trying to get env var DB_NAME")
            send_error(e, "Required parameters (DB_NAME) were not set, task aborted")

        try:
            # if passed in, use env vars, useful for debugging but you should rely on Parameter Store, 
            # otherwise anyone with rights to read the execution status or logs can see the values passed in
            db_host = os.environ['DB_HOST']
            db_port = os.environ['DB_PORT']
            db_name = os.environ['DB_NAME']
            db_user = os.environ['DB_USER']
            db_pass = os.environ['DB_PASS']
            s3_bucket = os.environ['S3_BUCKET']
            s3_path = os.environ['S3_PATH']

        except:
            # If no env vars, get from parameter store (for productionizing this, maybe make this the default).
            print("No env vars for DB info, checking Parameter Store")
            try:
                try: # get required env vars
                    db_env = os.environ['DB_ENV'] # expecting something like dev/prod/demo, this would be part of the keypath below (in case we have the same database in different environments)
                except Exception as e:
                    # print("Error trying to get env var DB_ENV")
                    send_error(e, "Required parameters (DB_ENV) were not set, task aborted")
                
                # Hard-coding the Parameter Store keypath for now. Using /serverlessops/databases as root and then 
                # /databasename/env as the path holding the rest of the values. Assumption is dbname/env should be unique.
                keybase = "/serverlessops/databases/" + db_name + "/" + db_env 
                
                db_host = get_parameter(keybase + "/db_host")
                db_port = get_parameter(keybase + "/db_port")
                db_user = get_parameter(keybase + "/db_user")
                db_pass = get_parameter(keybase + "/db_pass")
                s3_bucket = get_parameter(keybase + "/s3_bucket")
                s3_path = get_parameter(keybase +  "/s3_path")

            except Exception as e:
                print("issue using parameter store")
                send_error(e, "Error trying to get Parameter Store entries")

        # Do the backup
        print("Calling db backup logic")
        db_backup(db_host, db_port, db_user, db_pass, db_name, s3_bucket, s3_path)
    
    elif job_name.lower() == 'db_restore':
        """
        # Just an example showing we can combine related types of tasks. I.e., if backup and restore
        # used the same libraries/scripts/etc and only parameters changed, we could use one container
        # for both
        """
        print("asked to restore but this isn't coded yet")
        send_error("Unwritten function called", "Not implemented")
    else:
        # abort logic and send error to SF
        print("no valid job mentioned")
        send_error("Invalid job name", "A required JOB_NAME env variable was not set, valid values are: db_backup, db_restore")
