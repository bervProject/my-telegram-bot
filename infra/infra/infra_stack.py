from aws_cdk import (
    Stack,
    Duration,
    Fn,
    CfnParameter,
    CfnOutput,
    RemovalPolicy,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as iam,
)

from constructs import Construct

'''
Stack for Infra
'''
class TelegramBotInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Parameters
        ecr_bot = ecr.Repository.from_repository_name(
            self, "telegram-bot-ecr", "telegram-bot")
        image_tag = CfnParameter(
            self, "imageTag", type="String", description="Target tag")
        secret_arn = CfnParameter(
            self, "secretArn", type="String",
            description="Full ARN of the Secrets Manager secret")

        # Task Execution Role - pull images, write logs, read secrets
        task_execution_role = iam.Role(
            self, "TelegramBotTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="TelegramBotEcsTaskExecutionRole",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy")
            ])
        task_execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
            resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/ecs/telegram-bot-express*"]))
        task_execution_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["secretsmanager:GetSecretValue"],
            resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:dev/telegramBot*"]))

        # Task Role - application runtime permissions
        task_role = iam.Role(
            self, "TelegramBotTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            role_name="TelegramBotEcsTaskRole")

        # Infrastructure Role - ECS Express Mode managed infrastructure
        infrastructure_role = iam.Role(
            self, "TelegramBotInfrastructureRole",
            assumed_by=iam.ServicePrincipal("ecs.amazonaws.com"),
            role_name="TelegramBotEcsInfrastructureRole",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSInfrastructureRoleforExpressGatewayServices")
            ])

        image_uri = f"{ecr_bot.repository_uri}:{image_tag.value_as_string}"

        # Secrets from Secrets Manager
        # valueFrom format for a JSON key in Secrets Manager:
        #   <secret-arn>:<json-key>::
        # Use Fn.sub so CloudFormation resolves the ARN parameter server-side
        # before ECS sees the value (avoids the SSM-path misinterpretation).
        express_secrets = [
            ecs.CfnExpressGatewayService.SecretProperty(
                name=name,
                value_from=Fn.sub(
                    "${SecretArn}:" + name + "::",
                    {"SecretArn": secret_arn.value_as_string}))
            for name in [
                "TELEGRAM_TOKEN",
                "SECRET_KEY",
                "CLIENT_SECRET",
                "CLIENT_ID",
                "PUBLIC_URL",
            ]
        ]

        # ECS Express Mode Service
        express_service = ecs.CfnExpressGatewayService(
            self, "TelegramBotExpressService",
            service_name="telegram-bot-express-service",
            execution_role_arn=task_execution_role.role_arn,
            infrastructure_role_arn=infrastructure_role.role_arn,
            task_role_arn=task_role.role_arn,
            cpu="256",
            memory="512",
            health_check_path="/",
            primary_container=ecs.CfnExpressGatewayService.ExpressGatewayContainerProperty(
                image=image_uri,
                container_port=80,
                environment=[
                    ecs.CfnExpressGatewayService.KeyValuePairProperty(
                        name="FLASK_ENV", value="production")
                ],
                secrets=express_secrets,
                aws_logs_configuration=ecs.CfnExpressGatewayService.ExpressGatewayServiceAwsLogsConfigurationProperty(
                    log_group="/aws/ecs/telegram-bot-express",
                    log_stream_prefix="telegram-bot")),
            scaling_target=ecs.CfnExpressGatewayService.ExpressGatewayScalingTargetProperty(
                auto_scaling_metric="REQUEST_COUNT_PER_TARGET",
                auto_scaling_target_value=20,
                min_task_count=1,
                max_task_count=3))

        express_service.node.add_dependency(task_execution_role)
        express_service.node.add_dependency(task_role)
        express_service.node.add_dependency(infrastructure_role)

        CfnOutput(self, "ServiceName", value=express_service.service_name or "telegram-bot-express-service")


'''
Stack for ECR
'''
class TelegramBotRepoStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        ecr_bot = ecr.Repository(
            self, "telegram-bot-ecr",
            repository_name="telegram-bot",
            image_scan_on_push=False,
            removal_policy=RemovalPolicy.RETAIN,
            image_tag_mutability=ecr.TagMutability.MUTABLE,
            encryption=ecr.RepositoryEncryption.KMS)
        ecr_bot.add_lifecycle_rule(max_image_age=Duration.days(7),
                                   rule_priority=1,
                                   tag_status=ecr.TagStatus.UNTAGGED)
        CfnOutput(self, "telegram-bot-ecr-output", value=ecr_bot.repository_arn)
