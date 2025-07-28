import discord
from app.utils import load_roles, save_roles
from app.decorators import admin_only, allowed_channel_only


def register_misc_commands(bot):
    @bot.slash_command(name='commands', description='List all available AWS commands')
    @allowed_channel_only()
    @admin_only()
    async def list_commands(interaction: discord.Interaction):
        embed = discord.Embed(title="AWS Bot Commands", color=discord.Color.green())
        embed.add_field(name="Configure AWS account with cloudcommander", value="`/setup-role`,`/view-role`,`/remove-role` ", inline=False)
        embed.add_field(name="Your Region", value="`/set-region`,`/view-region`, `/switch-region`, `/reset-region` ", inline=False)
        embed.add_field(name="EC2", value="`/ec2-list`, `/ec2-start`, `/ec2-stop`, `/ec2-metrics`", inline=False)
        embed.add_field(name="EBS", value="`/ebs-list`", inline=False)
        embed.add_field(name="RDS", value="`/rds-list`, `/rds-start`, `/rds-stop`, `/rds-metrics`", inline=False)
        embed.add_field(name="S3", value="`/s3-list`, `/s3-metrics`", inline=False)
        embed.add_field(name="Lambda", value="`/lambda-list`, `/lambda-metrics`", inline=False)
        embed.add_field(name="CloudFormation", value="`/cf-list`, `/cf-describe`", inline=False)
        embed.add_field(name="CloudWatch", value="`/cloudwatch-summary`", inline=False)
        embed.add_field(name="Networking", value="`/network-status`", inline=False)
        embed.add_field(name="Billing & Cost", value="`/billing-summary`", inline=False)
        embed.add_field(name="Leave the server", value="`/leave-server`", inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.slash_command(name="leave-server", description="Bot will clean up and leave server.")
    @discord.default_permissions(administrator=True)
    async def leave_server(interaction: discord.Interaction):
        await interaction.response.send_message(
            "Cleanup Done.CloudCommander will leave the server shortly.",
            ephemeral=True
        )
        guild_id = str(interaction.guild.id)
        roles = load_roles()
        guild_data = roles.get(guild_id, {})
        channel_id = guild_data.get("designated_channel")
        if channel_id:
            try:
                channel = interaction.guild.get_channel(int(channel_id))
                if channel:
                    await channel.delete(reason="Cleanup before leaving server.")
            except:
                pass
        admin_role_id = guild_data.get("admin_role_id")
        if admin_role_id:
            try:
                role = discord.utils.get(interaction.guild.roles, id=int(admin_role_id))
                if role:
                    await role.delete(reason="Cleanup before leaving server.")
            except:
                pass
        user_role_id = guild_data.get("user_role_id")
        if user_role_id:
            try:
                role = discord.utils.get(interaction.guild.roles, id=int(user_role_id))
                if role:
                    await role.delete(reason="Cleanup before leaving server.")
            except:
                pass
        if guild_id in roles:
            del roles[guild_id]
            save_roles(roles)
        try:
            await interaction.guild.leave()
        except:
            pass
