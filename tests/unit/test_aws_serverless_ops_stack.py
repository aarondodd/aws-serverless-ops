import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_serverless_ops.aws_serverless_ops_stack import AwsServerlessOpsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_serverless_ops/aws_serverless_ops_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsServerlessOpsStack(app, "aws-serverless-ops")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
