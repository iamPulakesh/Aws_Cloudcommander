import discord
from app.utils import get_user_role_arn, get_user_region, format_aws_error
from app.aws_clients import get_assumed_clients
from app.decorators import admin_only, allowed_channel_only
from datetime import datetime, timedelta

def register_rds_commands(bot):
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
            await interaction.followup.send(embed=embed, ephemeral=True)
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
            await interaction.followup.send(embed=discord.Embed(description=f" Started `{db_id}`", color=discord.Color.green()), ephemeral=True)
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
            await interaction.followup.send(embed=discord.Embed(description=f" Stopped `{db_id}`", color=discord.Color.red()), ephemeral=True)
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
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)
