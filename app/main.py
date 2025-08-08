import os
import discord
from dotenv import load_dotenv
from commands.alerts import setup_alerts, register_alert_commands
from commands.onboarding import register_onboarding_events
from commands.misc_commands import register_misc_commands
from commands.region_commands import register_region_commands
from commands.role_commands import register_role_commands
from commands.ec2_commands import register_ec2_commands
from commands.rds_commands import register_rds_commands
from commands.s3_commands import register_s3_commands
from commands.lambda_commands import register_lambda_commands
from commands.cf_commands import register_cf_commands
from commands.ebs_commands import register_ebs_commands
from commands.network_commands import register_network_commands
from commands.billing_commands import register_billing_commands

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = discord.Bot(intents=intents)

# Register events and commands
register_onboarding_events(bot)
register_misc_commands(bot)
register_region_commands(bot)
register_role_commands(bot)
register_ec2_commands(bot)
register_rds_commands(bot)
register_s3_commands(bot)
register_lambda_commands(bot)
register_cf_commands(bot)
register_ebs_commands(bot)
register_network_commands(bot)
register_billing_commands(bot)
register_alert_commands(bot)

bot.run(TOKEN)
