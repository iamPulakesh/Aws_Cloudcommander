import discord
from app.utils import get_user_role_arn, get_user_region, format_aws_error
from app.aws_clients import get_assumed_clients
from app.decorators import admin_only, allowed_channel_only
from datetime import datetime, timedelta

def register_s3_commands(bot):
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
            embed = discord.Embed(title="\U0001FAA3 S3 Buckets", color=discord.Color.blue())
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
