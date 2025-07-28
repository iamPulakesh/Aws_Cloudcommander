import discord
from utils import load_roles, save_roles, get_user_region
from decorators import admin_only, allowed_channel_only


def register_region_commands(bot):
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
