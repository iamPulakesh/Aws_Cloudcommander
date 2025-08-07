import discord
from functools import wraps
from app.utils import load_roles

def admin_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            roles = load_roles()
            guild_id = str(interaction.guild_id)
            admin_role_id = roles.get(guild_id, {}).get("admin_role_id")
            if not admin_role_id:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=" Admin role not configured yet.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            role = discord.utils.get(interaction.guild.roles, id=int(admin_role_id))
            if role not in interaction.user.roles:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="🚫 Access denied. You are not authorized to execute this command.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            await func(interaction, *args, **kwargs)
        return wrapper
    return decorator

def allowed_channel_only():
    def decorator(func):
        @wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            guild_id = str(interaction.guild_id)
            channel_id = str(interaction.channel_id)
            roles = load_roles()
            allowed = roles.get(guild_id, {}).get("designated_channel")
            if str(channel_id) != allowed:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="⚠️ Please use Cloud Commander in the designated channel only.",
                        color=discord.Color.orange()
                    ), ephemeral=True)
                return
            await func(interaction, *args, **kwargs)
        return wrapper
    return decorator
