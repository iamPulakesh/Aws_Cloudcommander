import boto3

def get_assumed_clients(role_arn, region):
    sts = boto3.client('sts')
    assumed = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="DiscordBotSession"
    )
    creds = assumed['Credentials']
    services = ['ec2', 'cloudwatch', 's3', 'rds', 'lambda', 'cloudformation', 'ce']
    return {
        'cf' if svc == 'cloudformation' else svc: boto3.client(
            svc,
            region_name=region,
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']
        )
        for svc in services
    }
