import os
import subprocess
import discord
import time
from discord import app_commands
from discord.ext import commands, tasks
from wakeonlan import send_magic_packet

from cogs.utils.notification_msg import NotificationMsg

LAB_IP = os.getenv("LAB_IP")
SSH_USER = os.getenv("SSH_USER")
BROADCAST_IP = os.getenv("BROADCAST_IP")
MAC_ADDRESS = os.getenv("LAB_MAC")
NOTIFICATION_CHANNEL_ID = int(os.getenv("NOTIFICATION_CHANNEL_ID", 0))

class PowerManager(commands.Cog):
    def __init__(self, bot):
      self.bot = bot
      self.broadcast_ip = BROADCAST_IP
      self.lab_ip = LAB_IP
      self.ssh_user = SSH_USER
      self.mac = MAC_ADDRESS
      self.is_online = True
      self.channel_id = NOTIFICATION_CHANNEL_ID
      self.health_check.start()

      self.restart_history = {}
      self.cool_down_locks = {}
      
    def cog_unload(self):
        self.health_check.cancel()
        
    def ping_host(self):
        # -c 1 for one packet, -W 1 for 1 second timeout
        try:
            output = subprocess.call(["ping", "-c", "1", "-W", "1", self.lab_ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output == 0
        
        except Exception as e:
            print(f"⚠️ Ping error for {self.lab_ip}: {e}")
            return False

    def is_in_crash_loop(self, name):
        # Check if container restart over 3 times in 10 mins
        now = time.time()
        if name not in self.restart_history:
            self.restart_history[name] = []
            
        # Timestamp in 10mins (600s)
        self.restart_history[name] = [t for t in self.restart_history[name] if now - t < 600]
        
        return len(self.restart_history[name]) >= 3
        
    @tasks.loop(seconds=60)
    async def health_check(self):
        try:
            await self.bot.wait_until_ready()

            channel = self.bot.get_channel(self.channel_id) or await self.safe_fetch_channel()
            if not channel: return
            
            currently_online = self.ping_host()
            now = time.time()
            name = "homelab"

            if self.is_online and not currently_online:
                embed = NotificationMsg.error_msg(
                    title="Critical Alert", 
                    description=f"Homelab ({self.lab_ip}) is **OFFLINE**!"
                )
                await channel.send(embed=embed)
            
            elif not self.is_online and currently_online:

                if name not in self.restart_history:
                    self.restart_history[name] = []
                self.restart_history[name].append(now)

                if self.is_in_crash_loop(name):
                    if name not in self.cool_down_locks or now > self.cool_down_locks[name]:
                        self.cool_down_locks[name] = now + 1800 # Lock auto-heal in 30 mins
                        crash_embed = NotificationMsg.error_msg(
                                title="CRITICAL: Crash-loop Detected",
                                description=f"Computer `{name}` restarted many times. \n**Auto-heal is stopped for 1 hour** to protect server."
                        )
                        # Send with View, Logs button
                        await channel.send(embed=crash_embed)

                # Just came back online
                success_embed = NotificationMsg.success_msg(
                    title="System Restored",
                    description=f"Homelab (`{self.lab_ip}`) is now online again."
                )
                await channel.send(embed=success_embed)

            self.is_online = currently_online
        
        except Exception as e:
            print(f"❌ Health Check Error: {e}")

    async def safe_fetch_channel(self):
        try:
            return await self.bot.fetch_channel(self.channel_id)
        except:
            return None

    @health_check.before_loop
    async def before_health_check(self):
        await self.bot.wait_until_ready()
        
    @app_commands.command(name="wake_up", description="Wake up homelab on the San Jose node")
    async def wake_up(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try :
            send_magic_packet(self.mac, ip_address=self.broadcast_ip, port=9)

            embed = NotificationMsg.success_msg(
                title="WOL Sent",
                description=f"Sent WOL signal to {self.mac}. Homelab should be booting..."
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error: {e}")
            await interaction.followup.send(content=f"Error: {e}")

    @app_commands.command(name="power_off", description="Power off homelab on the San Jose node")
    async def power_off(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        if not self.ping_host():
            embed = NotificationMsg.error_msg(
                title="Error",
                description="Homelab is not online."
            )
            return await interaction.followup.send(embed=embed)
        
        try:
            ssh_cmd = [
                "ssh", 
                "-o", "StrictHostKeyChecking=no", 
                "-o", "ConnectTimeout=5",
                f"{self.ssh_user}@{self.lab_ip}",
                "sudo -n poweroff"
            ]

            subprocess.run(ssh_cmd, check=True)

            self.is_online = False

            embed = NotificationMsg.success_msg(
                title="Power Off",
                description="Powering off homelab..."
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            crash_embed = NotificationMsg.error_msg(
                title="Error",
                description=f"Error: {e}"
            )
            await interaction.followup.send(embed=crash_embed)

async def setup(bot):
    await bot.add_cog(PowerManager(bot))
