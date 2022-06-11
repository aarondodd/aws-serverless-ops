#!/bin/bash
# This does the local bootstrapping needed for me to run the CDK.
# Specifically, it accomodates my SSO integration with the AWS CLI. 
# Adjust as needed.

# Ensure this is sourced, not executed directly
[[ "${BASH_SOURCE[0]}" == "${0}" ]] && echo "script ${BASH_SOURCE[0]} is not being sourced, call as '. login.sh' or 'source login.sh' instead." && exit

# Activate the python virtual environment
source .venv/bin/activate

# CDK doesn't support SSO login, using yawsso plugin to sync credentials and setting my profile as default
function aws_login () {
    aws sso login --profile acd && yawsso --profile acd
    export AWS_PROFILE=acd
    export CDK_DEFAULT_ACCOUNT=266138714515
    export CDK_DEFAULT_REGION=us-east-1
}

if command -v yawsso; then
    aws_login
else
    pip install yawsso
    aws_login
fi