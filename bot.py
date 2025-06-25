import os
import json
import discord
import pathlib
from dotenv import load_dotenv
import boto3
from datetime import datetime, timedelta
from functools import wraps

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ROLE = "CloudCommanderUser"

# aws role assumption helper
def get_assumed_clients(role_arn, region):
    sts = boto3.client('sts')
    assumed = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="DiscordBotSession"
    )
    creds = assumed['Credentials']

    services = ['ec2', 'cloudwatch', 's3', 'rds', 'lambda', 'cloudformation']
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

def format_aws_error(e):
    if isinstance(e, TypeError) and 'RoleArn' in str(e):
        return " No IAM role set. Use `/setup-role` to register your AWS role before using this command."

    if hasattr(e, 'response'):
        err = e.response.get('Error', {})
        code = err.get('Code')
        if code in ['AccessDenied', 'UnauthorizedOperation']:
            return (
                " Cloud Commander does not have permission to perform this action.\n"
                "Please attach the required IAM policy to your IAM role and try again."
            )
        return f" AWS Error: {err.get('Message', 'An unknown AWS error occurred.')}"
    
    return f" Unexpected Error: {str(e)}"

def admin_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            roles = load_roles()
            guild_id = str(interaction.guild_id)
            admin_role_id = roles.get(guild_id, {}).get("admin_role_id")

            if not admin_role_id:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=" Admin role not configured yet.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return

            role = discord.utils.get(interaction.guild.roles, id=int(admin_role_id))
            if role not in interaction.user.roles:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="🚫 Access denied. You are not authorized to execute this command.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return

            await func(interaction, *args, **kwargs)
        return wrapper
    return decorator


def allowed_channel_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            guild_id = str(interaction.guild_id)
            channel_id = str(interaction.channel_id)
            roles = load_roles()
            allowed = roles.get(guild_id, {}).get("designated_channel")
            if str(channel_id) != allowed:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="⚠️ Please use Cloud Commander in the designated channel only.",
                        color=discord.Color.orange()
                    ), ephemeral=True)
                return
            await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def load_roles():
    path = pathlib.Path("roles.json")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_roles(data):
    with open("roles.json", "w") as f:
        json.dump(data, f, indent=4)

def get_user_role_arn(guild_id, channel_id, user_id):
    roles = load_roles()
    user_data = roles.get(str(guild_id), {}).get(str(channel_id), {}).get(str(user_id))
    
    if isinstance(user_data, list): 
        return user_data[0] if user_data else None
    return user_data.get("roles", [None])[0]

def get_user_region(guild_id, channel_id, user_id):
    roles = load_roles()
    user_data = roles.get(str(guild_id), {}).get(str(channel_id), {}).get(str(user_id))
    
    if isinstance(user_data, list):
        return "us-east-1"
    
    return user_data.get("region", "us-east-1")


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f' Logged in as {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_guild_join(guild):

    admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE)
    if not admin_role:
        admin_role = await guild.create_role(name=ADMIN_ROLE, permissions=discord.Permissions.none(),color=discord.Color.blue())
    
    existing = discord.utils.get(guild.text_channels, name="cloud-commander")
    if existing:
        channel = existing
    else:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        channel = await guild.create_text_channel("cloud-commander", overwrites=overwrites)
    
    #save channel and role ID in json
    roles = load_roles()
    roles.setdefault(str(guild.id), {})
    roles[str(guild.id)]["designated_channel"] = str(channel.id)
    roles[str(guild.id)]["admin_role_id"] = str(admin_role.id)
    save_roles(roles)

    setup_msg = await channel.send(embed=discord.Embed(
        title="👋 Welcome, Cloud Commander ☁️",
        description=(
            "You’ve just opened a portal to your AWS universe.\n"
            "Admins, assign the `CloudCommanderAdmin` role to users who should have bot access.\n\n"
            "• Use `/setup-role <arn>` to link your AWS IAM role.\n"
            "• Use `/view-role` to check roles.\n"
            "• Use `/remove-role` to unlink.\n\n"
            "Use `/commands` to list all available commands."
        ),
        color=discord.Color.green()
    ))
    await setup_msg.pin()

@bot.slash_command(name='commands', description='List all available AWS commands')
@allowed_channel_only()
@admin_only()
async def list_commands(interaction: discord.Interaction):

    embed = discord.Embed(title="AWS Bot Commands", color=discord.Color.green())
    embed.add_field(name="Configure AWS account with cloudcommander", value="`/setup-role`,`/view-role`,`/remove-role` ", inline=False)
    embed.add_field(name="Your Region", value="`/set-region`,`/view-region`, `/switch-region`, `/reset-region` ", inline=False)
    embed.add_field(name="EC2", value="`/ec2-list`, `/ec2-start`, `/ec2-stop`, `/ec2-metrics`", inline=False)
    embed.add_field(name="EBS", value="`/ebs-list`", inline=False)
    embed.add_field(name="RDS", value="`/rds-list`, `/rds-start`, `/rds-stop`, `/rds-metrics`", inline=False)
    embed.add_field(name="S3", value="`/s3-list`, `/s3-metrics`", inline=False)
    embed.add_field(name="Lambda", value="`/lambda-list`, `/lambda-metrics`", inline=False)
    embed.add_field(name="CloudFormation", value="`/cf-list`, `/cf-describe`", inline=False)
    embed.add_field(name="CloudWatch", value="`/cloudwatch-summary`", inline=False)
    embed.add_field(name="Networking", value="`/network-status`", inline=False)
    embed.add_field(name="Leave the server", value="`/leave-server`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.slash_command(name="leave-server", description="Bot will clean up and leave server.")
@discord.default_permissions(administrator=True)
async def leave_server(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Cleanup Done.CloudCommander will leave the server shortly.",
        ephemeral=True
    )

    guild_id = str(interaction.guild.id)
    roles = load_roles()
    guild_data = roles.get(guild_id, {})

    channel_id = guild_data.get("designated_channel")
    if channel_id:
        try:
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                await channel.delete(reason="Cleanup before leaving server.")
        except:
            pass

    admin_role_id = guild_data.get("admin_role_id")
    if admin_role_id:
        try:
            role = discord.utils.get(interaction.guild.roles, id=int(admin_role_id))
            if role:
                await role.delete(reason="Cleanup before leaving server.")
        except:
            pass

    user_role_id = guild_data.get("user_role_id")
    if user_role_id:
        try:
            role = discord.utils.get(interaction.guild.roles, id=int(user_role_id))
            if role:
                await role.delete(reason="Cleanup before leaving server.")
        except:
            pass

    if guild_id in roles:
        del roles[guild_id]
        save_roles(roles)

    try:
        await interaction.guild.leave()
    except:
        pass
   

@bot.slash_command(name='set-region', description='Set your default AWS region for this channel')
@admin_only()
@allowed_channel_only()
async def set_region(interaction: discord.Interaction, region: str):
    await interaction.response.defer(ephemeral=True)

    guild_id = str(interaction.guild_id)
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)

    roles = load_roles()
    user_data = roles.setdefault(guild_id, {}).setdefault(channel_id, {}).setdefault(user_id, {})

    if isinstance(user_data, list): 
        roles[guild_id][channel_id][user_id] = {"roles": user_data, "region": region}
    else:
        user_data["region"] = region

    save_roles(roles)
    await interaction.followup.send(
        embed=discord.Embed(
            title="AWS Region Set",
            description=f"Your default region has been set to `{region}`.",
            color=discord.Color.green()
        ),
        ephemeral=True)

@bot.slash_command(name='view-region', description='View your default AWS region for this channel')
@admin_only()
@allowed_channel_only()
async def view_region(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
    await interaction.followup.send(
        embed=discord.Embed(
            title="Your AWS Region",
            description=f"Your current region is set to: `{region}`",
            color=discord.Color.blurple()
        ),
        ephemeral=True
    )

@bot.slash_command(name='switch-region', description='Switch to another AWS region for this channel')
@admin_only()
@allowed_channel_only()
async def switch_region(interaction: discord.Interaction, region: str):
    await interaction.response.defer(ephemeral=True)

    guild_id = str(interaction.guild_id)
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)

    roles = load_roles()
    user_data = roles.setdefault(guild_id, {}).setdefault(channel_id, {}).setdefault(user_id, {})

    if isinstance(user_data, list):
        roles[guild_id][channel_id][user_id] = {"roles": user_data, "region": region}
    else:
        user_data["region"] = region

    save_roles(roles)
    await interaction.followup.send(
        embed=discord.Embed(
            title="AWS Region Switched",
            description=f"You are now using the region: `{region}`.",
            color=discord.Color.blue()
        ),
        ephemeral=True)

@bot.slash_command(name='reset-region', description='Remove your saved AWS region for this channel')
@admin_only()
@allowed_channel_only()
async def reset_region(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild_id = str(interaction.guild_id)
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)

    roles = load_roles()
    user_data = roles.get(guild_id, {}).get(channel_id, {}).get(user_id)

    if isinstance(user_data, dict) and "region" in user_data:
        del user_data["region"]
        save_roles(roles)
        await interaction.followup.send(
            embed=discord.Embed(
                title="AWS Region Reset",
                description="Your saved region has been removed.",
                color=discord.Color.orange()
            ), ephemeral=True)
    else:
        await interaction.followup.send(
            embed=discord.Embed(
                description="You don't have a region set to reset.",
                color=discord.Color.orange()
            ), ephemeral=True)

@bot.slash_command(name='setup-role', description='Register your AWS IAM role ARN for this channel')
@admin_only()
@allowed_channel_only()
async def setup_role(interaction: discord.Interaction, role_arn: str):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)

    roles = load_roles()
    roles.setdefault(guild_id, {}).setdefault(channel_id, {}).setdefault(user_id, [])

    if role_arn not in roles[guild_id][channel_id][user_id]:
        roles[guild_id][channel_id][user_id].append(role_arn)
        save_roles(roles)

    await interaction.followup.send(
        embed=discord.Embed(
            title="Role Registered",
            description=f"Your role was saved for this channel.",
            color=discord.Color.green()
        ), ephemeral=True)

@bot.slash_command(name='view-role', description='See your AWS role(s) for this channel')
@admin_only()
@allowed_channel_only()
async def view_role(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)

    roles = load_roles()
    user_data = roles.get(guild_id, {}).get(channel_id, {}).get(user_id)

    if not user_data:
        await interaction.followup.send(
            embed=discord.Embed(description="You have no IAM roles registered in this channel.", color=discord.Color.orange()),
            ephemeral=True)
        return

    if isinstance(user_data, list):
        arns = user_data
    else:
        arns = user_data.get("roles", [])

    if not arns:
        await interaction.followup.send(
            embed=discord.Embed(description="You have no IAM roles registered in this channel.", color=discord.Color.orange()),
            ephemeral=True)
        return

    embed = discord.Embed(title="Your Registered IAM Roles", color=discord.Color.blue())
    for i, arn in enumerate(arns):
        embed.add_field(name=f"Role {i+1}", value=arn, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.slash_command(name='remove-role', description='Remove all your IAM roles from this channel')
@admin_only()
@allowed_channel_only()
async def remove_role(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = str(interaction.guild_id)
    channel_id = str(interaction.channel_id)
    user_id = str(interaction.user.id)

    roles = load_roles()
    user_roles = roles.get(guild_id, {}).get(channel_id, {})
    if user_id in user_roles:
        del user_roles[user_id]
        save_roles(roles)
        await interaction.followup.send(
            embed=discord.Embed(description="Your roles have been removed from this channel.", color=discord.Color.red()),
            ephemeral=True)
    else:
        await interaction.followup.send(
            embed=discord.Embed(description="You have no registered roles to remove.", color=discord.Color.orange()),
            ephemeral=True)

@bot.slash_command(name='ec2-list', description='List all EC2 instances')
@admin_only()
@allowed_channel_only()
async def list_ec2_instances(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(
            embed=discord.Embed(description="No IAM role configured for this server.", color=discord.Color.red()),
            ephemeral=True)
        return

    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        ec2 = clients['ec2']
        reservations = ec2.describe_instances().get('Reservations', [])

        if not reservations:
            await interaction.followup.send(
                embed=discord.Embed(description="No EC2 instances found.", color=discord.Color.orange()),
                ephemeral=True)
            return

        embed = discord.Embed(title="EC2 Instances", color=discord.Color.gold())
        for r in reservations:
            for i in r['Instances']:
                instance_id = i['InstanceId']
                state = i['State']['Name']
                name = next((t['Value'] for t in i.get('Tags', []) if t['Key'] == 'Name'), 'Unnamed')
                embed.add_field(name=name, value=f"ID: `{instance_id}`\nStatus: **{state}**", inline=False)

        await interaction.followup.send(embed=embed,ephemeral=True)

    except Exception as e:
        await interaction.followup.send(
            embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()),
            ephemeral=True)


@bot.slash_command(name='ec2-start', description='Start an EC2 instance')
@admin_only()
@allowed_channel_only()
async def ec2_start(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        ec2 = clients['ec2']
        response = ec2.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [name]}])
        instance = next((i for r in response['Reservations'] for i in r['Instances']), None)
        if not instance:
            await interaction.followup.send(embed=discord.Embed(description=f" Instance `{name}` not found", color=discord.Color.red()), ephemeral=True)
            return
        instance_id = instance['InstanceId']
        ec2.start_instances(InstanceIds=[instance_id])
        await interaction.followup.send(embed=discord.Embed(description=f" Started `{name}`", color=discord.Color.green()),ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='ec2-stop', description='Stop an EC2 instance')
@admin_only()
@allowed_channel_only()
async def ec2_stop(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        ec2 = clients['ec2']
        response = ec2.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [name]}])
        instance = next((i for r in response['Reservations'] for i in r['Instances']), None)
        if not instance:
            await interaction.followup.send(embed=discord.Embed(description=f" Instance `{name}` not found", color=discord.Color.red()), ephemeral=True)
            return
        instance_id = instance['InstanceId']
        ec2.stop_instances(InstanceIds=[instance_id])
        await interaction.followup.send(embed=discord.Embed(description=f" Stopped `{name}`", color=discord.Color.red()),ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='ec2-metrics', description='Show EC2 CloudWatch metrics')
@admin_only()
@allowed_channel_only()
async def ec2_metrics(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        ec2 = clients['ec2']
        cloudwatch = clients['cloudwatch']
        response = ec2.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [name]}])
        instance = next((i for r in response['Reservations'] for i in r['Instances']), None)
        if not instance:
            await interaction.followup.send(embed=discord.Embed(description=f" Instance `{name}` not found", color=discord.Color.red()), ephemeral=True)
            return

        instance_id = instance['InstanceId']
        end = datetime.utcnow()
        start = end - timedelta(hours=1)

        metrics = [
            "CPUUtilization", "NetworkIn", "NetworkOut",
            "DiskReadBytes", "DiskWriteBytes", "DiskReadOps", "DiskWriteOps",
            "NetworkPacketsIn", "NetworkPacketsOut"
        ]

        unit_map = {
            "CPUUtilization": "%",
            "NetworkIn": "KB",
            "NetworkOut": "KB",
            "DiskReadBytes": "KB",
            "DiskWriteBytes": "KB",
            "DiskReadOps": "ops",
            "DiskWriteOps": "ops",
            "NetworkPacketsIn": "pkts",
            "NetworkPacketsOut": "pkts"
        }

        embed = discord.Embed(title=f"📊 EC2 Metrics for `{name}`", color=discord.Color.dark_green())

        for metric in metrics:
            stats = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName=metric,
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start,
                EndTime=end,
                Period=300,
                Statistics=['Average']
            )
            datapoints = stats.get('Datapoints', [])
            avg = round(datapoints[-1]['Average'], 2) if datapoints else 0

            unit = unit_map.get(metric, "")
            if "Bytes" in metric:
                avg = round(avg / 1024, 2)

            embed.add_field(name=metric, value=f"**{avg} {unit}**", inline=True)

        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='ebs-list', description='List EBS Volumes')
@admin_only()
@allowed_channel_only()
async def ebs_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        ec2 = clients['ec2']
        volumes = ec2.describe_volumes().get('Volumes', [])
        if not volumes:
            await interaction.followup.send(embed=discord.Embed(description=" No EBS volumes found.", color=discord.Color.orange()), ephemeral=True)
            return
        embed = discord.Embed(title=" EBS Volumes", color=discord.Color.light_grey())
        for v in volumes[:20]:
            vol_id = v['VolumeId']
            state = v['State']
            size = v['Size']
            vol_type = v['VolumeType']
            attachments = v.get('Attachments', [])
            attached_to = attachments[0]['InstanceId'] if attachments else "Not attached"
            embed.add_field(
                name=f"Volume: `{vol_id}`",
                value=(
                    f" State: **{state}**\n"
                    f" Size: **{size} GiB**\n"
                    f" Type: **{vol_type}**\n"
                    f" Attached To: `{attached_to}`"
                ),
                inline=False
            )
        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='rds-list', description='List RDS instances')
@admin_only()
@allowed_channel_only()
async def rds_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        rds = get_assumed_clients(role_arn, region)['rds']
        instances = rds.describe_db_instances().get('DBInstances', [])
        if not instances:
            await interaction.followup.send(embed=discord.Embed(description=" No RDS instances found.", color=discord.Color.orange()), ephemeral=True)
            return
        embed = discord.Embed(title=" RDS Instances", color=discord.Color.purple())
        for db in instances:
            embed.add_field(name=db['DBInstanceIdentifier'], value=f"Status: **{db['DBInstanceStatus']}**", inline=False)
        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='rds-start', description='Start an RDS instance')
@admin_only()
@allowed_channel_only()
async def rds_start(interaction: discord.Interaction, db_id: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        rds = get_assumed_clients(role_arn, region)['rds']
        rds.start_db_instance(DBInstanceIdentifier=db_id)
        await interaction.followup.send(embed=discord.Embed(description=f" Started `{db_id}`", color=discord.Color.green()),ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='rds-stop', description='Stop an RDS instance')
@admin_only()
@allowed_channel_only()
async def rds_stop(interaction: discord.Interaction, db_id: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        rds = get_assumed_clients(role_arn, region)['rds']
        rds.stop_db_instance(DBInstanceIdentifier=db_id)
        await interaction.followup.send(embed=discord.Embed(description=f" Stopped `{db_id}`", color=discord.Color.red()),ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='rds-metrics', description='Show RDS CloudWatch metrics')
@admin_only()
@allowed_channel_only()
async def rds_metrics(interaction: discord.Interaction, db_id: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        cloudwatch = clients['cloudwatch']
        end = datetime.utcnow()
        start = end - timedelta(hours=1)

        metrics = [
            "CPUUtilization", "DatabaseConnections", "FreeStorageSpace",
            "ReadIOPS", "WriteIOPS", "ReadLatency", "WriteLatency"
        ]

        unit_map = {
            "CPUUtilization": "%",
            "DatabaseConnections": "conns",
            "FreeStorageSpace": "GiB",
            "ReadIOPS": "ops",
            "WriteIOPS": "ops",
            "ReadLatency": "ms",
            "WriteLatency": "ms"
        }

        embed = discord.Embed(title=f" RDS Metrics for `{db_id}`", color=discord.Color.dark_orange())

        for metric in metrics:
            stats = cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName=metric,
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=start,
                EndTime=end,
                Period=300,
                Statistics=['Average']
            )
            datapoints = stats.get('Datapoints', [])
            avg = datapoints[-1]['Average'] if datapoints else 0

            if metric == "FreeStorageSpace":
                avg = round(avg / (1024 ** 3), 2)
            else:
                avg = round(avg, 2)

            unit = unit_map.get(metric, "")
            value_display = f"**{avg} {unit}**"

            embed.add_field(name=metric, value=value_display, inline=True)

        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='s3-list', description='List all S3 buckets')
@admin_only()
@allowed_channel_only()
async def s3_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        s3 = get_assumed_clients(role_arn, region)['s3']
        buckets = s3.list_buckets().get('Buckets', [])
        if not buckets:
            await interaction.followup.send(embed=discord.Embed(description=" No S3 buckets found.", color=discord.Color.orange()), ephemeral=True)
            return
        embed = discord.Embed(title="🪣 S3 Buckets", color=discord.Color.blue())
        for b in buckets:
            embed.add_field(name=b['Name'], value="", inline=False)
        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='s3-metrics', description='Show S3 CloudWatch metrics')
@admin_only()
@allowed_channel_only()
async def s3_metrics(interaction: discord.Interaction, bucket_name: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        s3 = clients['s3']
        cloudwatch = clients['cloudwatch']

        try:
            s3.head_bucket(Bucket=bucket_name)
        except s3.exceptions.NoSuchBucket:
            await interaction.followup.send(embed=discord.Embed(description=f" Bucket `{bucket_name}` not found.", color=discord.Color.red()), ephemeral=True)
            return
        except Exception as e:
            if "403" in str(e):
                await interaction.followup.send(embed=discord.Embed(description=f" Access denied to bucket `{bucket_name}`", color=discord.Color.red()), ephemeral=True)
                return

        end = datetime.utcnow()
        start = end - timedelta(days=1)
        embed = discord.Embed(title=f" S3 Metrics for `{bucket_name}`", color=discord.Color.dark_blue())

        metrics = [
            ("BucketSizeBytes", "StandardStorage", "Size"),
            ("NumberOfObjects", "AllStorageTypes", "Object Count")
        ]

        for metric, storage_type, label in metrics:
            stats = cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName=metric,
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': storage_type}
                ],
                StartTime=start,
                EndTime=end,
                Period=86400,
                Statistics=['Average']
            )
            points = stats.get('Datapoints', [])
            avg = points[-1]['Average'] if points else 0
            if metric == "BucketSizeBytes":
                if avg >= 1024 ** 3:
                    value_display = f"{round(avg / (1024 ** 3), 2)} GB"
                elif avg >= 1024 ** 2:
                    value_display = f"{round(avg / (1024 ** 2), 2)} MB"
                else:
                    value_display = f"{round(avg / 1024, 2)} KB"
            else:
                value_display = f"{int(avg):,}"

            embed.add_field(name=label, value=value_display, inline=False)

        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='lambda-list', description='List Lambda functions')
@admin_only()
@allowed_channel_only()
async def lambda_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        lambda_client = get_assumed_clients(role_arn, region)['lambda']
        functions = lambda_client.list_functions().get('Functions', [])
        if not functions:
            await interaction.followup.send(embed=discord.Embed(description=" No Lambda functions found.", color=discord.Color.orange()), ephemeral=True)
            return
        embed = discord.Embed(title="⚡ Lambda Functions", color=discord.Color.gold())
        for func in functions[:10]:
            name = func['FunctionName']
            runtime = func['Runtime']
            last_modified = func['LastModified']
            embed.add_field(name=name, value=f"Runtime: **{runtime}**\nModified: `{last_modified[:10]}`", inline=False)
        if len(functions) > 10:
            embed.add_field(name="...", value=f"And {len(functions) - 10} more", inline=False)
        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='lambda-metrics', description='Show Lambda CloudWatch metrics')
@admin_only()
@allowed_channel_only()
async def lambda_metrics(interaction: discord.Interaction, function_name: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        clients = get_assumed_clients(role_arn, region)
        lambda_client = clients['lambda']
        cloudwatch = clients['cloudwatch']

        try:
            lambda_client.get_function(FunctionName=function_name)
        except lambda_client.exceptions.ResourceNotFoundException:
            await interaction.followup.send(embed=discord.Embed(description=f" Lambda function `{function_name}` not found.", color=discord.Color.red()), ephemeral=True)
            return

        end = datetime.utcnow()
        start = end - timedelta(hours=1)
        metrics = ["Duration", "Invocations", "Errors", "Throttles", "ConcurrentExecutions"]
        embed = discord.Embed(title=f" Lambda Metrics for `{function_name}`", color=discord.Color.dark_gold())

        for metric in metrics:
            data = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName=metric,
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start,
                EndTime=end,
                Period=300,
                Statistics=['Average'] if metric == 'Duration' else ['Sum']
            )
            points = data.get('Datapoints', [])

            if metric == 'Duration':
                value = round(points[-1]['Average'], 2) if points else 0
                value_display = f"Avg: **{value}ms**"
            else:
                value = round(points[-1]['Sum'], 2) if points else 0
                value_display = f"Total: **{int(value)}**"

            embed.add_field(name=metric, value=value_display, inline=True)

        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='network-status', description='Show complete network info')
@admin_only()
@allowed_channel_only()
async def network_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(
            embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        ec2 = get_assumed_clients(role_arn, region)['ec2']
        vpcs = ec2.describe_vpcs().get('Vpcs', [])
        subnets = ec2.describe_subnets().get('Subnets', [])
        route_tables = ec2.describe_route_tables().get('RouteTables', [])
        sgs = ec2.describe_security_groups().get('SecurityGroups', [])
        nacls = ec2.describe_network_acls().get('NetworkAcls', [])

        embed = discord.Embed(title=" Network Status", color=discord.Color.dark_blue())

        embed.add_field(
            name=" VPCs",
            value="\n".join([f"ID:`{v['VpcId']}` CIDR:({v['CidrBlock']})" for v in vpcs]) or "None",
            inline=False
        )
        embed.add_field(
            name=" Subnets",
            value="\n".join([f"ID:`{s['SubnetId']}` ({s['VpcId']})" for s in subnets[:5]]) + ("\n..." if len(subnets) > 5 else "") if subnets else "None",
            inline=False
        )
        embed.add_field(
            name=" Route Tables",
            value="\n".join([f"ID:`{r['RouteTableId']}` ({r['VpcId']})" for r in route_tables]) or "None",
            inline=False
        )
        embed.add_field(
            name=" Security Groups",
            value="\n".join([f"ID:`{sg['GroupId']}` Name:({sg['GroupName']}) | ({sg['VpcId']})" for sg in sgs[:5]]) + ("\n..." if len(sgs) > 5 else "") if sgs else "None",
            inline=False
        )
        embed.add_field(
            name=" NACLs",
            value="\n".join([f"ID:`{n['NetworkAclId']}` ({n['VpcId']})" for n in nacls]) or "None",
            inline=False
        )

        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='cf-list', description='List CloudFormation stacks')
@admin_only()
@allowed_channel_only()
async def cf_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(
            embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        cf = get_assumed_clients(role_arn, region)['cf']
        stacks = cf.describe_stacks().get('Stacks', [])
        if not stacks:
            await interaction.followup.send(embed=discord.Embed(description=" No CloudFormation stacks found.", color=discord.Color.orange()), ephemeral=True)
            return
        embed = discord.Embed(title=" CloudFormation Stacks", color=discord.Color.teal())
        for s in stacks[:10]:
            embed.add_field(
                name=s['StackName'],
                value=f"Status: **{s['StackStatus']}**\nCreated: `{s['CreationTime'].strftime('%Y-%m-%d')}`",
                inline=False
            )
        if len(stacks) > 10:
            embed.add_field(name="...", value=f"And {len(stacks) - 10} more", inline=False)
        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(
            embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

@bot.slash_command(name='cf-describe', description='Describe a CloudFormation stack')
@admin_only()
@allowed_channel_only()
async def cf_describe(interaction: discord.Interaction, stack_name: str):
    await interaction.response.defer(ephemeral=True)
    role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
    if not role_arn:
        await interaction.followup.send(
            embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
        return
    try:
        region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
        cf = get_assumed_clients(role_arn, region)['cf']
        response = cf.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]

        embed = discord.Embed(title=f" Stack: `{stack_name}`", color=discord.Color.teal())
        embed.add_field(name="Status", value=stack['StackStatus'], inline=True)
        embed.add_field(name="Created On", value=stack['CreationTime'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
        embed.add_field(name="Description", value=stack.get('Description', '—'), inline=False)

        outputs = stack.get('Outputs', [])
        if outputs:
            for o in outputs:
                embed.add_field(name=o['OutputKey'], value=o['OutputValue'], inline=False)

        await interaction.followup.send(embed=embed,ephemeral=True)
    except Exception as e:
        await interaction.followup.send(
            embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)

bot.run(TOKEN)
