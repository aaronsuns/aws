from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
)
from constructs import Construct


class AwsServerlessApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB table (FREE TIER: 25 GB storage, 25 WCU, 25 RCU)
        # No VPC needed - DynamoDB is accessible from Lambda without VPC
        items_table = dynamodb.Table(
            self,
            "ItemsTable",
            table_name="api-items",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # On-demand pricing (free tier eligible)
            removal_policy=RemovalPolicy.DESTROY,  # For testing
            point_in_time_recovery=False,  # Disable for cost savings
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,  # Optional: for future stream processing
        )

        # Create Lambda function (no VPC needed for DynamoDB)
        api_handler = _lambda.Function(
            self,
            "ApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset(
                "lambda",
                bundling={
                    "image": _lambda.Runtime.PYTHON_3_12.bundling_image,
                    "command": [
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ],
                },
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "ITEMS_TABLE_NAME": items_table.table_name,
            },
        )

        # Grant Lambda permission to read/write DynamoDB table
        items_table.grant_read_write_data(api_handler)

        # Create CloudWatch Log Group with retention
        log_group = logs.LogGroup(
            self,
            "ApiHandlerLogGroup",
            log_group_name=f"/aws/lambda/{api_handler.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create HTTP API with CORS enabled for UI
        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            description="Serverless API Gateway HTTP API with DynamoDB",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.PUT,
                    apigwv2.CorsHttpMethod.DELETE,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_headers=["*"],
                max_age=Duration.days(1),
            ),
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

        # CRUD routes
        http_api.add_routes(
            path="/items",
            methods=[
                apigwv2.HttpMethod.GET,
                apigwv2.HttpMethod.POST,
            ],
            integration=lambda_integration,
        )

        http_api.add_routes(
            path="/items/{id}",
            methods=[
                apigwv2.HttpMethod.GET,
                apigwv2.HttpMethod.PUT,
                apigwv2.HttpMethod.DELETE,
            ],
            integration=lambda_integration,
        )

        # Create S3 bucket for UI hosting
        ui_bucket = s3.Bucket(
            self,
            "UiBucket",
            website_index_document="index.html",
            public_read_access=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,  # Auto-delete objects when bucket is deleted
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False,
            ),
        )

        # Create CloudFront distribution for UI (HTTPS + CDN)
        cloudfront_distribution = cloudfront.Distribution(
            self,
            "UiDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(ui_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
            ),
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # Use only North America and Europe (cheapest)
            comment="UI distribution for AWS Serverless API",
        )

        # Deploy UI files to S3 with CloudFront invalidation
        ui_deployment = s3_deployment.BucketDeployment(
            self,
            "UiDeployment",
            sources=[s3_deployment.Source.asset("ui")],
            destination_bucket=ui_bucket,
            distribution=cloudfront_distribution,  # Invalidate CloudFront cache on update
            distribution_paths=["/*"],  # Invalidate all paths
        )

        # Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=http_api.url or "Deploying...",
            description="HTTP API Gateway URL",
        )

        CfnOutput(
            self,
            "DynamoDBTableName",
            value=items_table.table_name,
            description="DynamoDB table name",
        )

        CfnOutput(
            self,
            "UiUrl",
            value=cloudfront_distribution.distribution_domain_name,
            description="CloudFront URL for UI",
        )

        CfnOutput(
            self,
            "UiS3Url",
            value=ui_bucket.bucket_website_url,
            description="S3 Website URL (fallback)",
        )
