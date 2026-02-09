from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct


class AwsServerlessApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda function
        # Using HTTP API (cheaper) instead of REST API
        api_handler = _lambda.Function(
            self,
            "ApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            memory_size=128,  # Minimum memory (cheapest option)
        )

        # Create CloudWatch Log Group with retention (cost optimization)
        # This must be created after the function to reference its name
        log_group = logs.LogGroup(
            self,
            "ApiHandlerLogGroup",
            log_group_name=f"/aws/lambda/{api_handler.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,  # Keep logs for 1 week
            removal_policy=RemovalPolicy.DESTROY,  # Delete logs when stack is deleted
        )

        # Create HTTP API (cheaper than REST API)
        # HTTP API costs $1.00 per million requests vs REST API's $3.50
        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            description="Serverless API Gateway HTTP API",
            # CORS configuration (uncomment if needed)
            # cors_preflight=apigwv2.CorsPreflightOptions(
            #     allow_origins=["*"],
            #     allow_methods=[apigwv2.CorsHttpMethod.GET, apigwv2.CorsHttpMethod.POST],
            #     allow_headers=["*"],
            #     max_age=Duration.days(1),
            # ),
        )

        # Add Lambda integration to HTTP API
        lambda_integration = apigw_integrations.HttpLambdaIntegration(
            "LambdaIntegration",
            handler=api_handler,
        )

        # Add routes to the API
        http_api.add_routes(
            path="/",
            methods=[apigwv2.HttpMethod.GET],
            integration=lambda_integration,
        )

        # Add a /hello route as example
        http_api.add_routes(
            path="/hello",
            methods=[apigwv2.HttpMethod.GET, apigwv2.HttpMethod.POST],
            integration=lambda_integration,
        )

        # Output the API URL
        CfnOutput(
            self,
            "ApiUrl",
            value=http_api.url or "Deploying...",
            description="HTTP API Gateway URL",
        )
