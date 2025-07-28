import discord
from app.utils import load_roles, save_roles

ADMIN_ROLE = "CloudCommanderUser"

def register_onboarding_events(bot):
    @bot.event
    async def on_ready():
        print(f' Logged in as {bot.user} (ID: {bot.user.id})')

    @bot.event
    async def on_guild_join(guild):
        admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE)
        if not admin_role:
            admin_role = await guild.create_role(name=ADMIN_ROLE, permissions=discord.Permissions.none(),color=discord.Color.blue())
        existing = discord.utils.get(guild.text_channels, name="cloud-commander")
        if existing:
            channel = existing
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            channel = await guild.create_text_channel("cloud-commander", overwrites=overwrites)
        roles = load_roles()
        roles.setdefault(str(guild.id), {})
        roles[str(guild.id)]["designated_channel"] = str(channel.id)
        roles[str(guild.id)]["admin_role_id"] = str(admin_role.id)
        save_roles(roles)
        setup_msg = await channel.send(embed=discord.Embed(
            title="\U0001F44B Welcome, Cloud Commander \u2601\uFE0F",
            description=(
                "You’ve just opened a portal to your AWS universe.\n"
                "Admins, assign the `CloudCommanderAdmin` role to users who should have bot access.\n\n"
                "• Use `/setup-role <arn>` to link your AWS IAM role.\n"
                "• Use `/view-role` to check roles.\n"
                "• Use `/remove-role` to unlink.\n\n"
                "Use `/commands` to list all available commands."
            ),
            color=discord.Color.green()
        ))
        await setup_msg.pin()
