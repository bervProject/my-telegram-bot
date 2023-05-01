from aws_cdk import (
    Stack,
    Duration,
    CfnParameter,
    CfnOutput,
    RemovalPolicy,
    aws_ecr as ecr,
    aws_secretsmanager as secretsmanager,
)
import aws_cdk.aws_apprunner_alpha as apprunner

from constructs import Construct

'''
Stack for Infra
'''
class TelegramBotInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        ecr_bot = ecr.Repository.from_repository_name(
            self, "telegram-bot-ecr", "telegram-bot")
        image_tag = CfnParameter(
            self, "imageTag", type="String", description="Target tag")
        app_runner_output = apprunner.Service(self, "telegram-bot-apprunner",
                                              source=apprunner.Source.from_ecr(
                                                  repository=ecr_bot,
                                                  image_configuration=apprunner.ImageConfiguration(port=80),
                                                  tag_or_digest=image_tag.value_as_string
                                              ))
        secrets = secretsmanager.Secret.from_secret_name_v2(self, "secret-telegram-bot", "dev/telegramBot")
        app_runner_output.add_secret("TELEGRAM_TOKEN", apprunner.Secret.from_secrets_manager(secret=secrets, field="TELEGRAM_TOKEN"))
        app_runner_output.add_secret("SECRET_KEY", apprunner.Secret.from_secrets_manager(secret=secrets, field="SECRET_KEY"))
        app_runner_output.add_secret("CLIENT_SECRET", apprunner.Secret.from_secrets_manager(secret=secrets, field="CLIENT_SECRET"))
        app_runner_output.add_secret("CLIENT_ID", apprunner.Secret.from_secrets_manager(secret=secrets, field="CLIENT_ID"))
        app_runner_output.add_environment_variable("PUBLIC_URL", app_runner_output.service_url)
        CfnOutput(self, "apprunner-url", value=app_runner_output.service_url)


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
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.RETAIN,
            image_tag_mutability=ecr.TagMutability.MUTABLE,
            encryption=ecr.RepositoryEncryption.KMS)
        ecr_bot.add_lifecycle_rule(max_image_age=Duration.days(7),
                                   rule_priority=1,
                                   tag_status=ecr.TagStatus.UNTAGGED)
        CfnOutput(self, "telegram-bot-ecr-output", value=ecr_bot.repository_arn)
