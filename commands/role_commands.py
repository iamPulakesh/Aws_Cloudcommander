import discord
from app.utils import load_roles, save_roles, get_user_role_arn
from app.decorators import admin_only, allowed_channel_only


def register_role_commands(bot):
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
