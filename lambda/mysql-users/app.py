# import urllib.request
import os
import boto3
import json
import sys
import logging
#import rds_config
import pymysql


"""
Example Lambda Function for issuing a MySql query. The example call creates a user
with all privileges.

Requires:
- VPC connectivity (to subnets with routing to the DB instance)
- Parameter Store entries (see/adjust below for assumed path)
- IAM role with rights (AWSLambdaVPCExecution managed policy and rights to read 
  the Parameter Store entries)
  
Usage:
- Ensure Lambda timeout is appropriate (default of 3 seconds is likely too short)
- Pass in the following payload with appropriate values (first two should be in 
  Parameter Store as mentioned above):

    {
      "db_name": "yourdbname",
      "db_env": "yourdbenv",
      "update_user": "someusername",
      "update_pass": "somepassword"
    }

Deviations from best practices:
On Purpose:
- The PyMySQL connection should usually be outside the handler function so that 
  it can be resued on future invocations (Lambda retains the execution environment
  for reuse, which is anything outside "def handler"). In this example, the Function
  is generic to be used against any number of MySQL instances, so having an
  established connection wouldn't be appropriate.
For demo simplicity:
- The logger.info call is overused and should be severely scaled back for production
  use to avoid sensitive information leakage to logfiles.
- The DB password in Parameter Store here is not a SecureString, but should be.
- The username and password passed in for this function to update in MySQL is not
  encrypted, but should be.
- There is now a Lambda Extension for ParameterStore that can be leveraged instead
  of the boto (Python SDK) calls used here, but the boto method has been kept for
  simplicity (the "def get_parameter() function is used elsewhere in this demo stack)

Recommended enhancements
- If using StepFunctions (recommended), the "get_parameters" could be its own Lambda
  Function invoked before this one in the workflow and pass the lookups here. This
  would 1/ reduce the complexity of this Lambda Function, 2/ allow for more granular
  IAM permissions (the MySQL function shouldn't have more rights than needed), 3/
  offload error handling more to the StepFunction.
"""

aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("Function initializing.")

def get_parameter(keyname):
    """Get a value from Parameter Store"""
    logger.info("Asked to get the value of " + keyname) # Potentially remove this, as the keynames will be saved in Cloudwatch Logs
    ssm = boto3.client('ssm')
    try:
        response = ssm.get_parameter(Name=keyname,WithDecryption=True)
        # logger.info("Got back value " + response['Parameter']['Value']) # Uncomment only for debugging
        return response['Parameter']['Value']
    except Exception as e:
        logger.error("ERROR: Unexpected error: Could not retrieve Parameter Store value " + keypath)
        logger.error(e)
        sys.exit()


# This Lambda function is a modification of
# - https://docs.aws.amazon.com/lambda/latest/dg/services-rds-tutorial.html


def handler(event, context):
    logger.info("Lambda handler function invoked")
    
    
    # From below, the handler will build /serverlessops/databases/... path to keys
    logger.info("Setting variables.")
    try:
        db_name = event['db_name']
        db_env = event['db_env']
        logger.info("Asked to use database " + db_name + " in environment " + db_env)
    except Exception as e:
        logger.error("ERROR: Expected 'db_name' and 'db_env' but did not receive both.")
        logger.error(e)
        sys.exit()
    
    # Set the user/pass we're asked to create/update
    try:
        update_user = event['update_user']
        update_pass = event['update_pass']
    except Exception as e:
        logger.error("ERROR: Was not given 'update_user' or 'update_pass' values.")
        logger.error(e)
        sys.exit()
    
    # Build the parameter store paths for the DB server info needed
    logger.info("Building the Parameter Store paths")
    paramstore_base_path = "/serverlessops/databases"
    paramstore_path = paramstore_base_path + "/" + db_name + "/" + db_env
    paramstore_db_host = paramstore_path + "/db_host"
    paramstore_db_port = paramstore_path + "/db_port"
    paramstore_db_user = paramstore_path + "/db_user"
    paramstore_db_pass = paramstore_path + "/db_pass"
    
    # Get the parameters
    logger.info("Calling the get_parameter function to retrieve values from Parameter Store")
    db_host = get_parameter(paramstore_db_host)
    db_port = get_parameter(paramstore_db_port)
    db_user = get_parameter(paramstore_db_user)
    db_pass = get_parameter(paramstore_db_pass)

    # New user query string
    add_user_string = "CREATE USER '" + update_user + "'@'%' IDENTIFIED BY '" + update_pass + "';"
    grant_user_string = "GRANT ALL PRIVILEGES ON " + db_name + ".* TO '" + update_user + "'@'%';"
    # logger.info("Add user string: " + add_user_string) # Uncomment only for debugging only
    # logger.info("Grant user string: " + grant_user_string) # Uncomment only for debugging
    
    # Connect to MySQL
    logger.info("Beginning MySQL work.")
    try:
        conn = pymysql.connect(host=db_host, port=int(db_port), user=db_user, passwd=db_pass, db=db_name, connect_timeout=5)
        logger.info("Connection to RDS MySQL instance succeeded")
    except pymysql.MySQLError as e:
        logger.error("ERROR: Unexpected error: Could not connect to MySQL instance.")
        logger.error(e)
        sys.exit()
    

    try:
        with conn.cursor() as cur:
            cur.execute(add_user_string)
            cur.execute(grant_user_string)
            cur.execute("FLUSH PRIVILEGES;")
            conn.commit()
            logger.info("Query to MySQL succeeded.")
    except pymysql.MySQLError as e:
        logger.error("ERROR: Unexpected error: Query failed.")
        logger.error(e)
        sys.exit()

    for row in cur:
        print(f"Added row {row}")
        logger.info("Added row: " + row)


    return "Added user " + update_user + " to database " + db_name + " on host " + db_host