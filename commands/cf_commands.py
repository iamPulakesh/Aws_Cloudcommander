import discord
from utils import get_user_role_arn, get_user_region, format_aws_error
from aws_clients import get_assumed_clients
from decorators import admin_only, allowed_channel_only

def register_cf_commands(bot):
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
            await interaction.followup.send(embed=embed, ephemeral=True)
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
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)
