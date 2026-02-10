from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_logs as logs,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_sqs as sqs,
    aws_s3_notifications as s3n,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
)
from constructs import Construct


class VideoProcessingStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        stage: str = "dev",
        **kwargs,
    ) -> None:
        """Stack for the serverless API, parameterised by environment stage.

        The `stage` parameter is used to namespace resource names so that we can
        deploy multiple isolated environments (dev/stage/prod) into the same
        AWS account and region, or across multiple accounts, without name
        collisions.
        """
        super().__init__(scope, construct_id, **kwargs)

        self.stage = stage

        # Create DynamoDB table (FREE TIER: 25 GB storage, 25 WCU, 25 RCU)
        # No VPC needed - DynamoDB is accessible from Lambda without VPC
        items_table = dynamodb.Table(
            self,
            "ItemsTable",
            table_name=f"api-items-{stage}",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
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
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
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

        # ===== VIDEO PROCESSING SETUP (Free Tier) =====

        # S3 bucket for raw video uploads (FREE TIER: 5 GB storage, 2K PUT requests/month)
        videos_bucket = s3.Bucket(
            self,
            "VideosBucket",
            bucket_name=f"video-processing-raw-{stage}-{self.account}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            # Block public access for security
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # CORS configuration to allow browser uploads
            # Note: OPTIONS is automatically handled by S3 for CORS preflight requests
            cors=[
                s3.CorsRule(
                    allowed_origins=["*"],  # Allow all origins (presigned URLs are secure)
                    allowed_methods=[
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.HEAD,
                        s3.HttpMethods.GET,
                    ],
                    allowed_headers=["*"],
                    exposed_headers=["ETag", "x-amz-server-side-encryption", "x-amz-request-id"],
                    max_age=3000,
                )
            ],
        )

        # DynamoDB table for job tracking (FREE TIER: 25 GB storage, 25 WCU, 25 RCU)
        jobs_table = dynamodb.Table(
            self,
            "JobsTable",
            table_name=f"video-jobs-{stage}",
            partition_key=dynamodb.Attribute(name="job_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
        )

        # SQS queue for video processing jobs (FREE TIER: 1M requests/month)
        processing_queue = sqs.Queue(
            self,
            "ProcessingQueue",
            queue_name=f"video-processing-{stage}",
            visibility_timeout=Duration.minutes(5),  # Lambda timeout
            retention_period=Duration.days(4),  # Keep messages for 4 days
        )

        # ===== LAMBDA PROCESSOR (ACTIVE) =====
        # Lambda function for video processing (triggered by SQS)
        # FREE TIER: 1M requests/month, 400K GB-seconds
        processor_lambda = _lambda.Function(
            self,
            "VideoProcessor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="processor.lambda_handler",
            code=_lambda.Code.from_asset(
                "lambda",
                bundling={
                    "image": _lambda.Runtime.PYTHON_3_12.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
                    ],
                },
            ),
            timeout=Duration.minutes(5),  # Match SQS visibility timeout
            memory_size=512,  # More memory for "processing"
            environment={
                "JOBS_TABLE_NAME": jobs_table.table_name,
                "VIDEOS_BUCKET_NAME": videos_bucket.bucket_name,
                "PROCESSING_QUEUE_URL": processing_queue.queue_url,
            },
        )

        # Grant permissions
        videos_bucket.grant_read(processor_lambda)
        jobs_table.grant_read_write_data(processor_lambda)
        # Note: processor_lambda is invoked by Step Functions, not directly by SQS

        # Create CloudWatch Log Group for processor
        processor_log_group = logs.LogGroup(
            self,
            "ProcessorLogGroup",
            log_group_name=f"/aws/lambda/{processor_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ===== ECS SETUP (UNUSED - KEPT FOR REFERENCE) =====
        # The following ECS code is commented out but kept for reference.
        # To use ECS instead of Lambda, uncomment this section and update Step Functions.

        # # ECR repository for Docker image
        # ecr_repo = ecr.Repository(
        #     self,
        #     "ProcessorEcrRepo",
        #     repository_name=f"video-processor-{stage}",
        #     removal_policy=RemovalPolicy.DESTROY,
        #     image_scan_on_push=True,
        # )
        #
        # # ECS Cluster (Fargate)
        # ecs_cluster = ecs.Cluster(
        #     self,
        #     "VideoProcessingCluster",
        #     cluster_name=f"video-processing-{stage}",
        # )
        #
        # # ECS Task Definition
        # task_definition = ecs.FargateTaskDefinition(
        #     self,
        #     "ProcessorTaskDefinition",
        #     memory_limit_mib=2048,  # 2 GB
        #     cpu=1024,  # 1 vCPU
        # )
        #
        # # Container definition
        # container = task_definition.add_container(
        #     "ProcessorContainer",
        #     image=ecs.ContainerImage.from_ecr_repository(
        #         ecr_repo,
        #         tag="latest",
        #     ),
        #     logging=ecs.LogDrivers.aws_logs(
        #         stream_prefix="video-processor",
        #         log_group=logs.LogGroup(
        #             self,
        #             "ProcessorLogGroup",
        #             log_group_name=f"/ecs/video-processor-{stage}",
        #             retention=logs.RetentionDays.ONE_WEEK,
        #             removal_policy=RemovalPolicy.DESTROY,
        #         ),
        #     ),
        #     environment={
        #         "JOBS_TABLE_NAME": jobs_table.table_name,
        #         "VIDEOS_BUCKET_NAME": videos_bucket.bucket_name,
        #     },
        # )
        #
        # # Grant permissions to task role
        # videos_bucket.grant_read(task_definition.task_role)
        # jobs_table.grant_read_write_data(task_definition.task_role)
        #
        # # ECS Service (Fargate) - will be triggered by Step Functions, not always running
        # # We create a service but it will scale to 0 when idle
        # ecs_service = ecs.FargateService(
        #     self,
        #     "ProcessorService",
        #     cluster=ecs_cluster,
        #     task_definition=task_definition,
        #     desired_count=0,  # Start with 0 tasks, scale based on queue
        #     assign_public_ip=True,  # Fargate needs public IP for internet access
        # )
        #
        # # Autoscaling based on SQS queue depth
        # scaling_target = ecs_service.auto_scale_task_count(
        #     min_capacity=0,  # Can scale to 0 when idle
        #     max_capacity=10,  # Max 10 concurrent tasks
        # )
        #
        # # Scale based on SQS queue depth (approximate number of messages)
        # scaling_target.scale_on_metric(
        #     "QueueDepthScaling",
        #     metric=processing_queue.metric_approximate_number_of_messages_visible(),
        #     scaling_steps=[
        #         autoscaling.ScalingInterval(upper=0, change=0),  # No tasks if queue empty
        #         autoscaling.ScalingInterval(lower=1, change=+1),  # 1 task per message
        #         autoscaling.ScalingInterval(lower=5, change=+2),  # Add 2 tasks per 5 messages
        #     ],
        #     adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
        # )

        # ===== STEP FUNCTIONS STATE MACHINE =====

        # Step 1: Wait for S3 upload (check if file exists)
        wait_for_upload = sfn.Wait(
            self,
            "WaitForUpload",
            time=sfn.WaitTime.duration(Duration.seconds(5)),
            comment="Wait for S3 upload to complete",
        )

        # Step 2: Invoke Lambda Processor
        invoke_lambda = sfn_tasks.LambdaInvoke(
            self,
            "InvokeProcessorLambda",
            lambda_function=processor_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "s3_bucket": sfn.JsonPath.string_at("$.s3_bucket"),
                    "s3_key": sfn.JsonPath.string_at("$.s3_key"),
                }
            ),
            result_path="$.lambda_result",
        )

        # Step 3: Success state
        success = sfn.Succeed(
            self,
            "ProcessingComplete",
            comment="Video processing completed successfully",
        )

        # Step 4: Failure state
        failure = sfn.Fail(
            self,
            "ProcessingFailed",
            error="ProcessingError",
            cause="Video processing failed",
        )

        # Define state machine
        definition = wait_for_upload.next(invoke_lambda).next(success)

        # Add error handling
        invoke_lambda.add_catch(
            failure,
            errors=["States.ALL"],  # Catch all errors
            result_path="$.error",
        )

        # Create Step Functions state machine
        state_machine = sfn.StateMachine(
            self,
            "VideoProcessingStateMachine",
            state_machine_name=f"video-processing-{stage}",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.minutes(30),
            comment="Orchestrates video processing workflow using Lambda",
        )

        # Grant Step Functions permission to invoke Lambda
        processor_lambda.grant_invoke(state_machine.role)

        # ===== ECS STEP FUNCTIONS CODE (UNUSED - KEPT FOR REFERENCE) =====
        # The following Step Functions code uses ECS instead of Lambda.
        # To use ECS, uncomment this section and comment out the Lambda invocation above.

        # # Step 2: Run ECS Task
        # run_ecs_task = sfn_tasks.EcsRunTask(
        #     self,
        #     "RunEcsTask",
        #     cluster=ecs_cluster,
        #     task_definition=task_definition,
        #     launch_target=sfn_tasks.EcsFargateLaunchTarget(),
        #     integration_pattern=sfn.IntegrationPattern.RUN_JOB,
        #     container_overrides=[
        #         sfn_tasks.ContainerOverride(
        #             container_definition=container,
        #             environment=[
        #                 sfn_tasks.TaskEnvironmentVariable(
        #                     name="JOB_ID",
        #                     value=sfn.JsonPath.string_at("$.job_id"),
        #                 ),
        #                 sfn_tasks.TaskEnvironmentVariable(
        #                     name="S3_BUCKET",
        #                     value=sfn.JsonPath.string_at("$.s3_bucket"),
        #                 ),
        #                 sfn_tasks.TaskEnvironmentVariable(
        #                     name="S3_KEY",
        #                     value=sfn.JsonPath.string_at("$.s3_key"),
        #                 ),
        #             ],
        #         )
        #     ],
        #     result_path="$.ecs_result",
        # )
        #
        # # Define state machine with ECS
        # definition = (
        #     wait_for_upload
        #     .next(run_ecs_task)
        #     .next(success)
        # )
        #
        # # Add error handling
        # run_ecs_task.add_catch(
        #     failure,
        #     errors=["States.TaskFailed"],
        #     result_path="$.error",
        # )
        #
        # # Grant Step Functions permission to run ECS tasks
        # state_machine.role.add_to_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.ALLOW,
        #         actions=[
        #             "ecs:RunTask",
        #             "ecs:StopTask",
        #             "ecs:DescribeTasks",
        #         ],
        #         resources=[task_definition.task_definition_arn],
        #     )
        # )
        #
        # state_machine.role.add_to_policy(
        #     iam.PolicyStatement(
        #         effect=iam.Effect.ALLOW,
        #         actions=["iam:PassRole"],
        #         resources=[task_definition.task_role.role_arn],
        #     )
        # )

        # S3 event notification: When video is uploaded, send message to SQS
        # Note: We filter to only trigger on files in the uploads/ directory to avoid
        # processing other S3 operations. The step_function_trigger Lambda will
        # extract the job_id from the S3 key path.
        videos_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(processing_queue),
            s3.NotificationKeyFilter(
                prefix="uploads/"
            ),  # Only trigger on files in uploads/ directory
        )

        # Lambda function to trigger Step Functions from SQS
        step_function_trigger = _lambda.Function(
            self,
            "StepFunctionTrigger",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="step_function_trigger.lambda_handler",
            code=_lambda.Code.from_asset(
                "lambda",
                bundling={
                    "image": _lambda.Runtime.PYTHON_3_12.bundling_image,
                    "command": [
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
                    ],
                },
            ),
            timeout=Duration.minutes(1),
            memory_size=256,
            environment={
                "STATE_MACHINE_ARN": state_machine.state_machine_arn,
                "JOBS_TABLE_NAME": jobs_table.table_name,
            },
        )

        # Grant permissions
        state_machine.grant_start_execution(step_function_trigger)
        jobs_table.grant_read_write_data(step_function_trigger)
        processing_queue.grant_consume_messages(step_function_trigger)

        # Trigger Lambda from SQS queue
        step_function_trigger.add_event_source(
            lambda_event_sources.SqsEventSource(
                processing_queue,
                batch_size=1,
                max_batching_window=Duration.seconds(5),
            )
        )

        # Grant API handler permissions for job management
        jobs_table.grant_read_write_data(api_handler)
        videos_bucket.grant_write(api_handler)  # For presigned URLs
        state_machine.grant_start_execution(api_handler)  # Allow API to start Step Functions

        # Update API handler environment
        api_handler.add_environment("JOBS_TABLE_NAME", jobs_table.table_name)
        api_handler.add_environment("VIDEOS_BUCKET_NAME", videos_bucket.bucket_name)
        api_handler.add_environment("PROCESSING_QUEUE_URL", processing_queue.queue_url)
        api_handler.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)

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

        # Video processing job routes
        http_api.add_routes(
            path="/jobs",
            methods=[apigwv2.HttpMethod.POST],
            integration=lambda_integration,
        )

        http_api.add_routes(
            path="/jobs/{id}",
            methods=[apigwv2.HttpMethod.GET],
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

        # Video processing outputs
        CfnOutput(
            self,
            "VideosBucketName",
            value=videos_bucket.bucket_name,
            description="S3 bucket for raw video uploads",
        )

        CfnOutput(
            self,
            "JobsTableName",
            value=jobs_table.table_name,
            description="DynamoDB table for job tracking",
        )

        CfnOutput(
            self,
            "ProcessingQueueUrl",
            value=processing_queue.queue_url,
            description="SQS queue for video processing",
        )

        CfnOutput(
            self,
            "StateMachineArn",
            value=state_machine.state_machine_arn,
            description="Step Functions state machine ARN",
        )

        CfnOutput(
            self,
            "ProcessorLambdaArn",
            value=processor_lambda.function_arn,
            description="Lambda function ARN for video processing",
        )

        # ===== ECS OUTPUTS (UNUSED - KEPT FOR REFERENCE) =====
        # Uncomment these if using ECS instead of Lambda:
        #
        # CfnOutput(
        #     self,
        #     "EcrRepositoryUri",
        #     value=ecr_repo.repository_uri,
        #     description="ECR repository URI for Docker image",
        # )
        #
        # CfnOutput(
        #     self,
        #     "EcsClusterName",
        #     value=ecs_cluster.cluster_name,
        #     description="ECS cluster name",
        # )
        #
        # CfnOutput(
        #     self,
        #     "EcsServiceName",
        #     value=ecs_service.service_name,
        #     description="ECS service name",
        # )
