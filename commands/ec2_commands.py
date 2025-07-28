import discord
from app.utils import get_user_role_arn, get_user_region, format_aws_error
from app.aws_clients import get_assumed_clients
from decorators import admin_only, allowed_channel_only
from datetime import datetime, timedelta


def register_ec2_commands(bot):
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
            await interaction.followup.send(embed=embed, ephemeral=True)
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
            await interaction.followup.send(embed=discord.Embed(description=f" Started `{name}`", color=discord.Color.green()), ephemeral=True)
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
            await interaction.followup.send(embed=discord.Embed(description=f" Stopped `{name}`", color=discord.Color.red()), ephemeral=True)
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
            embed = discord.Embed(title=f"\U0001F4CA EC2 Metrics for `{name}`", color=discord.Color.dark_green())
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
