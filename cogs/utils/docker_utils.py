import discord
import re
import docker
from .notification_msg import NotificationMsg

class DockerUtils:
    
    @staticmethod
    def strip_ansi_codes(text):
        """
        Removes ANSI escape codes (terminal colors) to ensure 
        logs are clean and readable on Discord.
        """
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    @staticmethod # Added staticmethod decorator to allow direct class calls
    async def get_container_logs(client, container_name):
        """
        Fetches the last 20 lines of logs for a specific container,
        cleans them, and returns a Discord Embed.
        """
        try:
            container = client.containers.get(container_name)
            
            # Fetch last 20 lines (tail=20) from Docker
            raw_logs = container.logs(tail=20, stdout=True, stderr=True).decode('utf-8')
            
            # Use the static method via class name to strip terminal colors
            clean_logs = DockerUtils.strip_ansi_codes(raw_logs).strip()
            
            if not clean_logs:
                clean_logs = "No log output found for this container."
                
            # Discord has a character limit for embeds. 
            # We truncate to the last 2000 characters to prevent errors.
            final_logs = clean_logs if len(clean_logs) < 2000 else "..." + clean_logs[-2000:]
            
            embed = discord.Embed(
                title=f"📋 Logs: {container_name}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.description = f"```log\n{final_logs}\n```"
            embed.set_footer(text="Showing latest lines • San Jose Node")
            
            return True, embed
            
        except Exception as e:
            # Return a formatted error message if log retrieval fails
            error_embed = NotificationMsg.error_msg(
                title="Log Fetch Failed",
                description=f"Could not retrieve logs for `{container_name}`: {str(e)}"
            )
            return False, error_embed
        
class QuickLogView(discord.ui.View):
    """
    A persistent view containing a button to quickly view logs 
    from an automated alert message.
    """
    def __init__(self, container_name, client):
        super().__init__(timeout=None) # No timeout so the button remains active
        self.container_name = container_name
        self.client = client
        
    @discord.ui.button(label="View logs", style=discord.ButtonStyle.secondary, emoji="📋")
    async def view_log(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Callback for the 'View logs' button. 
        Calls the static DockerUtils method and sends an ephemeral response.
        """
        # Call the static method directly. 
        # Do NOT pass 'self' as an argument here.
        success, embed = await DockerUtils.get_container_logs(self.client, self.container_name)
        
        # Respond only to the user who clicked the button (ephemeral)
        await interaction.response.send_message(embed=embed, ephemeral=True)