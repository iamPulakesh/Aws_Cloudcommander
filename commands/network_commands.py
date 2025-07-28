import discord
from app.utils import get_user_role_arn, get_user_region, format_aws_error
from app.aws_clients import get_assumed_clients
from app.decorators import admin_only, allowed_channel_only

def register_network_commands(bot):
    @bot.slash_command(name='network-status', description='Show complete network info')
    @admin_only()
    @allowed_channel_only()
    async def network_status(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        role_arn = get_user_role_arn(interaction.guild_id, interaction.channel_id, interaction.user.id)
        if not role_arn:
            await interaction.followup.send(
                embed=discord.Embed(description=" No IAM role configured.", color=discord.Color.red()), ephemeral=True)
            return
        try:
            region = get_user_region(interaction.guild_id, interaction.channel_id, interaction.user.id)
            ec2 = get_assumed_clients(role_arn, region)['ec2']
            vpcs = ec2.describe_vpcs().get('Vpcs', [])
            subnets = ec2.describe_subnets().get('Subnets', [])
            route_tables = ec2.describe_route_tables().get('RouteTables', [])
            sgs = ec2.describe_security_groups().get('SecurityGroups', [])
            nacls = ec2.describe_network_acls().get('NetworkAcls', [])
            embed = discord.Embed(title=" Network Status", color=discord.Color.dark_blue())
            embed.add_field(
                name=" VPCs",
                value="\n".join([f"ID:`{v['VpcId']}` CIDR:({v['CidrBlock']})" for v in vpcs]) or "None",
                inline=False
            )
            embed.add_field(
                name=" Subnets",
                value="\n".join([f"ID:`{s['SubnetId']}` ({s['VpcId']})" for s in subnets[:5]]) + ("\n..." if len(subnets) > 5 else "") if subnets else "None",
                inline=False
            )
            embed.add_field(
                name=" Route Tables",
                value="\n".join([f"ID:`{r['RouteTableId']}` ({r['VpcId']})" for r in route_tables]) or "None",
                inline=False
            )
            embed.add_field(
                name=" Security Groups",
                value="\n".join([f"ID:`{sg['GroupId']}` Name:({sg['GroupName']}) | ({sg['VpcId']})" for sg in sgs[:5]]) + ("\n..." if len(sgs) > 5 else "") if sgs else "None",
                inline=False
            )
            embed.add_field(
                name=" NACLs",
                value="\n".join([f"ID:`{n['NetworkAclId']}` ({n['VpcId']})" for n in nacls]) or "None",
                inline=False
            )
            await interaction.followup.send(embed=embed,ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(description=format_aws_error(e), color=discord.Color.red()), ephemeral=True)
