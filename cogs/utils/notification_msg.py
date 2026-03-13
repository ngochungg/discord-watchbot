import discord

class NotificationMsg:
    def __init__(self, title: str, description: str):
        self.title = title
        self.description = description

    @staticmethod
    def error_msg(title: str, description: str) -> discord.Embed:
        # Tạo một Embed thực thụ
        embed = discord.Embed(
            title=f"🚨 {title}",
            description=f"```\n{description}\n```",
            color=discord.Color.red()
        )
        return embed
    
    @staticmethod
    def warning_msg(title: str, description: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=f"```\n{description}\n```",
            color=discord.Color.orange()
        )
        return embed
    
    @staticmethod
    def success_msg(title: str, description: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"✅ {title}",
            description=f"```\n{description}\n```",
            color=discord.Color.green()
        )
        return embed
    
    @staticmethod
    def info_msg(title: str, description: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"{title}",
            description=f"```\n{description}\n```",
            color=discord.Color.blue()
        )
        return embed
    