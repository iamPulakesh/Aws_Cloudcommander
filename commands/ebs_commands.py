import discord
from app.utils import get_user_role_arn, get_user_region, format_aws_error
from app.aws_clients import get_assumed_clients
from app.decorators import admin_only, allowed_channel_only

def register_ebs_commands(bot):
    @bot.slash_command(name='ebs-list', description='List EBS Volumes')
    @admin_only()
    @allowed_channel_only()
    async def ebs_list(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
        if not role_arn:
            await interaction.followup.send(embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
            return
        try:
            region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
            clients = get_assumed_clients(role_arn, region)
            ec2 = clients['ec2']
            volumes = ec2.describe_volumes().get('Volumes', [])
            if not volumes:
                await interaction.followup.send(embed=discord.Embed(description=" No EBS volumes found.", color=discord.Color.orange()), ephemeral=True)
                return
            embed = discord.Embed(title=" EBS Volumes", color=discord.Color.light_grey())
            for v in volumes[:20]:
                vol_id = v['VolumeId']
                state = v['State']
                size = v['Size']
                vol_type = v['VolumeType']
                attachments = v.get('Attachments', [])
                attached_to = attachments[0]['InstanceId'] if attachments else "Not attached"
                embed.add_field(
                    name=f"Volume: `{vol_id}`",
                    value=(
                        f" State: **{state}**\n"
                        f" Size: **{size} GiB**\n"
                        f" Type: **{vol_type}**\n"
                        f" Attached To: `{attached_to}`"
                    ),
                    inline=False
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)
