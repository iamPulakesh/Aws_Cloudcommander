import discord
from app.utils import get_user_role_arn, get_user_region, format_aws_error
from app.aws_clients import get_assumed_clients
from app.decorators import admin_only, allowed_channel_only
from datetime import datetime

def register_billing_commands(bot):
    @bot.slash_command(name='billing-summary', description='View current month\'s AWS cost breakdown')
    @admin_only()
    @allowed_channel_only()
    async def billing_summary(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
        if not role_arn:
            await interaction.followup.send(
                embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
            return
        try:
            region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
            ce = get_assumed_clients(role_arn, region)['ce']
            now = datetime.utcnow()
            start = now.replace(day=1).strftime('%Y-%m-%d')
            end = now.strftime('%Y-%m-%d')
            response = ce.get_cost_and_usage(
                TimePeriod={'Start': start, 'End': end},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            embed = discord.Embed(title=f" AWS Billing Summary ({start} to {end})", color=discord.Color.green())
            total = 0.0
            for group in response['ResultsByTime'][0]['Groups']:
                service = group['Keys'][0]
                amount = float(group['Metrics']['UnblendedCost']['Amount'])
                total += amount
                embed.add_field(name=service, value=f"${amount:.2f}", inline=False)
            embed.add_field(name="**Total Cost**", value=f"**${total:.2f}**", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)
