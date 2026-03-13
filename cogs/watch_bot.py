import os
import json
import time
import docker
import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.utils.docker_utils import QuickLogView
from cogs.utils.dropdown_bar import DropdownBar
from cogs.utils.notification_msg import NotificationMsg

CONFIG_PATH = "monitored_services.json"
ALERT_CHANNEL_ID = int(os.getenv("NOTIFICATION_CHANNEL_ID", 0))
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
LAB_IP = os.getenv("LAB_IP")
SSH_USER = os.getenv("SSH_USER")

class WatchBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = None
        self.lab_ip = LAB_IP
        self.ssh_user = SSH_USER

        self.monitored_containers = self.load_monitored_services()
        if self.monitored_containers is None:
            self.monitored_containers = set()
            
        self.restart_history = {}
        self.cool_down_locks = {}

        self.auto_heal.start()
    
    def load_monitored_services(self):
        if os.path.exists(CONFIG_PATH):
            try:
                # Check if file is not empty before loading
                if os.path.getsize(CONFIG_PATH) > 0:
                    with open(CONFIG_PATH, "r") as f:
                        return set(json.load(f))
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Config file corrupted or empty. Resetting... Error: {e}")
                    
    def save_monitor_services(self):
        """Save the current set to JSON"""
        with open(CONFIG_PATH, "w") as f:
            json.dump(list(self.monitored_containers), f)
            
    def is_in_crash_loop(self, name):
        # Check if container restart over 3 times in 10 mins
        now = time.time()
        if name not in self.restart_history:
            self.restart_history[name] = []
            
        # Timestamp in 10mins (600s)
        self.restart_history[name] = [t for t in self.restart_history[name] if now - t < 600]
        
        return len(self.restart_history[name]) >= 3
    
    async def callback_func(self, container_name, action):
        
        # Ensure it;s a sete before operating
        if self.monitored_containers is None:
            self.monitored_containers = set()
        
        # This function is passed to the View to andle data
        if container_name in self.monitored_containers:
            self.monitored_containers.remove(container_name)
            status = "Disabled"
            
        else:
            self.monitored_containers.add(container_name)
            status = "Enabled"
            
        self.save_monitor_services()
        
        embed = NotificationMsg.success_msg(
            title="Monitoring Updated",
            description=f"Auto-heal for `{container_name}` is now **{status}**."
        )
        return True, embed
    
    def cog_unload(self):
        self.auto_heal.cancel()
        
    @tasks.loop(seconds=30)
    async def auto_heal(self):
        try:
            if not self.monitored_containers or not self.client:
                return
            
            channel = self.bot.get_channel(ALERT_CHANNEL_ID)
            now = time.time()
            
            for name in list(self.monitored_containers):
                
                # Check if services is lock by crash-loop
                if name in self.cool_down_locks and now < self.cool_down_locks[name]:
                    continue
                    
                try:
                    container = self.client.containers.get(name)
                    
                    # Check if container is not in the desired 'running'
                    if container.status != "running":
                        
                        if self.is_in_crash_loop(name):
                            self.cool_down_locks[name] = now + 3600 # Lock auto-heal in 1 hour
                            if channel:
                                embed = NotificationMsg.error_msg(
                                    title="CRITICAL: Crash-loop Detected",
                                    description=f"Service `{name}` restarted many times. \n**Auto-heal is stopped 1 hour** to protect server."
                                )
                                
                                # Send with View, Logs button
                                view = QuickLogView(name, self.client)
                                await channel.send(embed=embed, view=view)
                            continue
                        
                        # Perform the restart first
                        container.restart()
                        
                        if name not in self.restart_history:
                            self.restart_history[name] = []
                        self.restart_history[name].append(now)
                        
                        # Sync the local obj with Docker
                        container.reload()
                        
                        if channel:
                            embed = NotificationMsg.success_msg(
                                title=" Auto-Heal Executed",
                                description=f"Service `{name}` was down. It has been successfully restarted."
                            )
                        
                        else:
                            embed = NotificationMsg.error_msg(
                                title="🚨 Auto-Heal Failed",
                                description=f"Service `{name}` failed to recover. Current status: **{container.status}**."
                            )

                        await channel.send(embed=embed)          

                except docker.errors.NotFound:
                    self.monitored_containers.remove(name)
                    self.save_monitor_services()
                    print(f"Removed {name} from tracking: Container not found.")
                        
                except Exception as e:
                    print(f"Monitor error for {name}: {e}")
        except Exception as e:
            print(f"❌ Auto-heal Task Error: {e}")

    def connect_to_docker(self):
        try:
            ssh_url = f"ssh://{self.ssh_user}@{self.lab_ip}"
            client = docker.DockerClient(base_url=ssh_url, use_ssh_client=True,timeout=10)

            client.ping()
            self.client = client
            return True

        except Exception as e:
            print(f"❌ Cannot connect Docker Remote: {e}")
            self.client = None
            return False
                
    @app_commands.command(name="tracking", description="Manage Docker auto-healing services")
    async def tracking(self, interaction: discord.Interaction):
        # 1. Admin Check
        if interaction.user.id != ADMIN_ID:
            embed = NotificationMsg.error_msg(
                title="Permission Denied",
                description="You don't have permission to manage Docker containers."
            )
            
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)

        if not self.client:
            if not self.connect_to_docker():
                return await interaction.followup.send("❌ Cannot connect to Docker Engine.", ephemeral=True)

        # List container
        containers = self.client.containers.list(all=True)
        
        action_map = {
            "Toggle": (self.callback_func, None)
        }
        
        view = DropdownBar(
            containers,
            self.client,
            self.monitored_containers,
            action_map,
            mode="tracking"
        )
        await interaction.followup.send("🛡️ **Service Monitoring Dashboard**", view=view, ephemeral=True)
        
        view.message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(WatchBot(bot))