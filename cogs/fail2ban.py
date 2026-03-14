import os
import discord
from discord.ext import commands
from aiohttp import web

from cogs.utils.notification_msg import NotificationMsg

FAIL2BAN_CHANNEL_ID = int(os.getenv("FAIL2BAN_CHANNEL_ID", 0))
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

class Fail2Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = FAIL2BAN_CHANNEL_ID
        self.port = 5000
        self.server_task = None

        self.server_task = self.bot.loop.create_task(self.start_web_server())

    async def start_web_server(self):

        # Create a web server using aiohttp
        app = web.Application()
        app.router.app_post('alert', self.handle_alert)

        runner = web.AppRunner(app)
        await runner.setup()

        # Only listen on localhost
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()

        print(f"Fail2Ban web server started on http://localhost:{self.port}")

    async def handle_alert(self, request):
        try:
            data = await request.json()
            alert_type = data.get('type', 'System')
            message = data.get("message", "No content")
            status = data.get("status", "info")

            channel = self.bot.get_channel(self.channel_id)
            if channel:
                if status == "error":
                    embed = NotificationMsg.error_msg(
                        title=f"{alert_type}", description=message
                    )
                else:
                    embed = NotificationMsg.warning_msg(
                        title=f"{alert_type}", 
                        description=message
                    )
                await channel.send(embed=embed)

            return web.Response(status=200, text="Alert sent to Discord")
                
        except Exception as e:
            print(f"Error processing alert: {e}")
            return web.Response(status=500, text=f"Error: {e}")

    def cog_unload(self):
        if self.server_task:
            self.server_task.cancel()
            self.bot.loop.create_task(self.server_task.cancel())
        print("Fail2Ban web server stopped")

async def setup(bot):
    await bot.add_cog(Fail2Ban(bot))