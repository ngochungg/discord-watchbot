import json
import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
import psutil
import platform
import datetime

from cogs.utils.notification_msg import NotificationMsg
from cogs.utils.get_bar import Bar

ALERT_CHANNEL_ID = int(os.getenv("NOTIFICATION_CHANNEL_ID", 0))

class MonitorBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_config()
        self.check_system_status.start()

    def cog_unload(self):
        self.check_system_status.cancel()

    def load_config(self):
        with open('config.json', 'r') as f:
            self.config = json.load(f)

    @app_commands.command(name="status", description="Check Homelab stats at San Jose")
    async def status(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=False)

        # Take system metrics using psutil
        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        uname = platform.uname()
        
        # Create an embed message to display the system status
        embed = NotificationMsg.info_msg(
            title="🖥️ San Jose Node",
            description="System status"
        )

        storage_info = []
        for disk_config in self.config["disks"]:
            try:
                # Take information
                usage = psutil.disk_usage(disk_config['path'])
                percent = usage.percent
                name = disk_config['name']
                
                # Display
                line = f"{name.ljust(10)}: {str(percent).rjust(5)}% | [{Bar.get_bar(percent)}]"
                storage_info.append(line)
            
            except Exception:
                storage_info.append(f"{disk_config['name'].ljust(10)}: Error reading disk")
            
        storage_info = "```\n" + "\n".join(storage_info) + "\n```"
        
        embed.add_field(name="🌐 OS", value=f"{uname.system} {uname.release}", inline=False)
        embed.add_field(name="🔥 CPU Usage", value=f"{cpu_usage}%\n{Bar.get_bar(cpu_usage)}", inline=True)
        embed.add_field(name="🧠 RAM", value=f"{ram.percent}% ({ram.used//1048576}MB / {ram.total//1048576}MB)\n[{Bar.get_bar(ram.percent)}]", inline=True)
        embed.add_field(name="💾 Storage Status", value=storage_info, inline=False)
        
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await interaction.followup.send(embed=embed)

    @tasks.loop(hours=1)
    async def check_system_status(self):

        if not self.bot.is_ready():
            return
        
        # Check if alert channel is available
        channel = self.bot.get_channel(ALERT_CHANNEL_ID)
        if not channel:
            print(f"Alert channel with ID {ALERT_CHANNEL_ID} not found.")
            return
        
        # 1. Check CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_limit = self.config['system']['cpu_threshold']

        if cpu_usage > cpu_limit - 20:
            embed = NotificationMsg.warning_msg(
                title="⚠️ **CPU Usage Warning**",
                description=f"CPU usage is at {cpu_usage}%. Please monitor your system."
            )
            await channel.send(embed=embed)

        elif cpu_usage > cpu_limit:
            embed = NotificationMsg.error_msg(
                title="🔥 **High CPU Usage**",
                description=f"CPU usage is at {cpu_usage}%. Please check your system."
            )
            await channel.send(embed=embed)

        # 2. Check RAM usage
        ram = psutil.virtual_memory().percent
        ram_limit = self.config['system']['ram_threshold']
        if ram > ram_limit - 20:
            embed = NotificationMsg.warning_msg(
                title="⚠️ **RAM Usage Warning**",
                description=f"RAM usage is at {ram}%. Please monitor your system."
            )
            await channel.send(embed=embed)
        
        elif ram > ram_limit:
            embed = NotificationMsg.error_msg(
                title="🧠 **High RAM Usage**",
                description=f"RAM usage is at {ram}%. Please check your system."
            )
            await channel.send(embed=embed)
        
        # 3. Check Disk usage
        for disk in self.config["disks"]:
            name = disk["name"]
            path = disk["path"]
            threshold = disk["threshold"]
            disk_usage = psutil.disk_usage(path=path)

            if disk_usage.percent > threshold:
                embed = NotificationMsg.error_msg(
                    title=f"💾 **High Disk Usage ({name})**",
                    description=f"Disk usage for {name} is at {disk_usage.percent}%. Please check your system."
                )
                await channel.send(embed=embed)

    @check_system_status.before_loop
    async def before_check_system_status(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(MonitorBot(bot))