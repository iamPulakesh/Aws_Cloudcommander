import os
import discord
from discord.ext import tasks
from datetime import datetime
from app.utils import get_user_role_arn, get_user_region, format_aws_error
from app.aws_clients import get_assumed_clients
from app.decorators import admin_only, allowed_channel_only

# This will store the last notified cost threshold in memory
last_notified_cost = 0

# Set to keep track of which guilds have alerts enabled
enabled_alert_guilds = set()

def register_alert_commands(bot):
    @bot.slash_command(name="setup-alert", description="Enable AWS billing alerts for this server.")
    @allowed_channel_only()
    @admin_only()
    async def setup_alert_command(interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message(embed=discord.Embed(description="This command must be run in a server.", color=discord.Color.red()), ephemeral=True)
            return
        guild_id = guild.id
        if guild_id in enabled_alert_guilds:
            await interaction.response.send_message(embed=discord.Embed(description="AWS billing alerts are already enabled for this server!", color=discord.Color.green()), ephemeral=True)
            return
        setup_alerts(bot, guild_id)
        enabled_alert_guilds.add(guild_id)
        await interaction.response.send_message(embed=discord.Embed(description="AWS billing alerts are now enabled for this server!", color=discord.Color.green()),
            ephemeral=True
        )

async def get_total_cost(role_arn, region):
    ce = get_assumed_clients(role_arn, region)['ce']
    now = datetime.utcnow()
    start = now.replace(day=1).strftime('%Y-%m-%d')
    end = now.strftime('%Y-%m-%d')
    response = ce.get_cost_and_usage(
        TimePeriod={'Start': start, 'End': end},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )
    total = float(response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])
    return total

def setup_alerts(bot, guild_id):
    @tasks.loop(minutes=60)  # hourly
    async def billing_alert_task():
        global last_notified_cost
        guild = bot.get_guild(guild_id)
        if not guild:
            return
        channel = discord.utils.get(guild.text_channels, name="cloud-commander")
        if not channel:
            return
        # Use the first user in the guild as the context for role lookup
        member = next(iter(guild.members), None)
        if not member:
            return
        role_arn = get_user_role_arn(guild.id, channel.id, member.id)
        if not role_arn:
            await channel.send("No IAM role configured for this server. Please set up a role to enable billing alerts.")
            return
        region = get_user_region(guild.id, channel.id, member.id)
        if not region:
            await channel.send("No AWS region configured for this server. Please set up a region to enable billing alerts.")
            return
        try:
            total = await get_total_cost(role_arn, region)
            threshold = int(total)
            if threshold > last_notified_cost:
                await channel.send(f"⚠️ AWS cost alert: You have crossed ${threshold:.2f} this month!")
                last_notified_cost = threshold
        except Exception as e:
            await channel.send(f"Error checking AWS cost: {format_aws_error(e)}")
    billing_alert_task.start()
