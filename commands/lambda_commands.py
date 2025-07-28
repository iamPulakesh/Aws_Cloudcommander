import discord
from utils import get_user_role_arn, get_user_region, format_aws_error
from aws_clients import get_assumed_clients
from decorators import admin_only, allowed_channel_only
from datetime import datetime, timedelta

def register_lambda_commands(bot):
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
            embed = discord.Embed(title="\u26A1 Lambda Functions", color=discord.Color.gold())
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
