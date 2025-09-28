import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import math
import random
from PIL import Image, ImageDraw, ImageFont
import io
import sqlite3
from typing import Dict, List, Tuple, Optional
import asyncio
import colorsys

class WheelSection:
    """Represents a single section of the wheel"""
    def __init__(self, name: str, percentage: float, color: str):
        self.name = name
        self.percentage = percentage
        self.color = self._parse_color(color)
    
    def _parse_color(self, color: str) -> str:
        """Parse color input to hex format"""
        color = color.lower().strip()
        
        # Predefined colors
        color_map = {
            'red': '#FF0000', 'blue': '#0000FF', 'green': '#00FF00',
            'yellow': '#FFFF00', 'orange': '#FFA500', 'purple': '#800080',
            'pink': '#FFC0CB', 'cyan': '#00FFFF', 'magenta': '#FF00FF',
            'lime': '#00FF00', 'navy': '#000080', 'teal': '#008080',
            'olive': '#808000', 'maroon': '#800000', 'gray': '#808080',
            'silver': '#C0C0C0', 'black': '#000000', 'white': '#FFFFFF'
        }
        
        if color in color_map:
            return color_map[color]
        
        # Check if it's already a hex color
        if color.startswith('#') and len(color) == 7:
            try:
                int(color[1:], 16)  # Validate hex
                return color.upper()
            except ValueError:
                pass
        
        # Default to random color if invalid
        return f"#{random.randint(0, 0xFFFFFF):06X}"
    
    def to_dict(self) -> dict:
        """Convert section to dictionary for storage"""
        return {
            'name': self.name,
            'percentage': self.percentage,
            'color': self.color
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create section from dictionary"""
        return cls(data['name'], data['percentage'], data['color'])

class WheelDatabase:
    """Database handler for wheel persistence"""
    def __init__(self, db_path: str = "wheels.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wheels (
                guild_id INTEGER PRIMARY KEY,
                sections TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_wheel(self, guild_id: int, sections: List[WheelSection]):
        """Save wheel configuration for a guild"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sections_data = json.dumps([section.to_dict() for section in sections])
        
        cursor.execute('''
            INSERT OR REPLACE INTO wheels (guild_id, sections) VALUES (?, ?)
        ''', (guild_id, sections_data))
        
        conn.commit()
        conn.close()
    
    def load_wheel(self, guild_id: int) -> List[WheelSection]:
        """Load wheel configuration for a guild"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT sections FROM wheels WHERE guild_id = ?', (guild_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            sections_data = json.loads(result[0])
            return [WheelSection.from_dict(data) for data in sections_data]
        return []

class WheelRenderer:
    """Handles wheel image generation and rendering"""
    def __init__(self):
        self.image_size = (800, 800)
        self.center = (400, 400)
        self.radius = 350
    
    def create_wheel_image(self, sections: List[WheelSection], winner: Optional[str] = None) -> io.BytesIO:
        """Create a wheel image with the given sections"""
        # Create image with transparent background
        img = Image.new('RGBA', self.image_size, (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Draw outer circle border
        draw.ellipse([
            self.center[0] - self.radius - 5, 
            self.center[1] - self.radius - 5,
            self.center[0] + self.radius + 5, 
            self.center[1] + self.radius + 5
        ], outline='black', width=5)
        
        if not sections:
            # Draw empty wheel
            draw.ellipse([
                self.center[0] - self.radius, 
                self.center[1] - self.radius,
                self.center[0] + self.radius, 
                self.center[1] + self.radius
            ], fill='lightgray', outline='black', width=2)
            
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            text = "Empty Wheel"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text((
                self.center[0] - text_width // 2,
                self.center[1] - text_height // 2
            ), text, fill='black', font=font)
        else:
            # Calculate angles for each section
            current_angle = 0
            
            # Load font
            try:
                font = ImageFont.truetype("arial.ttf", 16)
                small_font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            for section in sections:
                # Calculate section angle in degrees
                section_angle = (section.percentage / 100) * 360
                
                # Highlight winner section
                outline_color = 'red' if winner and section.name == winner else 'black'
                outline_width = 4 if winner and section.name == winner else 2
                
                # Draw pie slice
                self._draw_pie_slice(
                    draw, 
                    current_angle, 
                    current_angle + section_angle,
                    section.color,
                    outline_color,
                    outline_width
                )
                
                # Add text label
                text_angle = math.radians(current_angle + section_angle / 2)
                text_radius = self.radius * 0.7
                
                text_x = self.center[0] + text_radius * math.cos(text_angle)
                text_y = self.center[1] + text_radius * math.sin(text_angle)
                
                # Prepare text
                text = f"{section.name}\n{section.percentage}%"
                
                # Calculate text position (center it)
                lines = text.split('\n')
                total_height = len(lines) * 20
                
                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=small_font if i == 1 else font)
                    text_width = bbox[2] - bbox[0]
                    
                    line_x = text_x - text_width // 2
                    line_y = text_y - total_height // 2 + i * 20
                    
                    # Add text background for readability
                    draw.rectangle([
                        line_x - 2, line_y - 2,
                        line_x + text_width + 2, line_y + 18
                    ], fill=(255, 255, 255, 180))
                    
                    draw.text((line_x, line_y), line, 
                            fill='black', font=small_font if i == 1 else font)
                
                current_angle += section_angle
        
        # Draw center circle
        center_radius = 30
        draw.ellipse([
            self.center[0] - center_radius,
            self.center[1] - center_radius,
            self.center[0] + center_radius,
            self.center[1] + center_radius
        ], fill='white', outline='black', width=3)
        
        # Draw pointer
        self._draw_pointer(draw)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer
    
    def _draw_pie_slice(self, draw, start_angle: float, end_angle: float, 
                       fill_color: str, outline_color: str, outline_width: int):
        """Draw a pie slice on the wheel"""
        draw.pieslice([
            self.center[0] - self.radius,
            self.center[1] - self.radius,
            self.center[0] + self.radius,
            self.center[1] + self.radius
        ], start_angle, end_angle, fill=fill_color, outline=outline_color, width=outline_width)
    
    def _draw_pointer(self, draw):
        """Draw the pointer at the top of the wheel"""
        pointer_size = 20
        pointer_points = [
            (self.center[0], self.center[1] - self.radius - 10),
            (self.center[0] - pointer_size, self.center[1] - self.radius + pointer_size),
            (self.center[0] + pointer_size, self.center[1] - self.radius + pointer_size)
        ]
        draw.polygon(pointer_points, fill='red', outline='darkred', width=2)

class ChanceWheelBot(commands.Bot):
    """Main Discord bot class for the chance wheel"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.database = WheelDatabase()
        self.renderer = WheelRenderer()
        self.wheels: Dict[int, List[WheelSection]] = {}
    
    async def setup_hook(self):
        """Setup hook called when bot starts"""
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f'{self.user} has landed!')
        print(f'Bot is in {len(self.guilds)} servers')
    
    def get_wheel_sections(self, guild_id: int) -> List[WheelSection]:
        """Get wheel sections for a guild"""
        if guild_id not in self.wheels:
            self.wheels[guild_id] = self.database.load_wheel(guild_id)
        return self.wheels[guild_id]
    
    def save_wheel_sections(self, guild_id: int, sections: List[WheelSection]):
        """Save wheel sections for a guild"""
        self.wheels[guild_id] = sections
        self.database.save_wheel(guild_id, sections)
    
    def calculate_total_percentage(self, sections: List[WheelSection]) -> float:
        """Calculate total percentage of all sections"""
        return sum(section.percentage for section in sections)

# Create bot instance
bot = ChanceWheelBot()

@bot.tree.command(name="createwheel", description="Start creating a new wheel (clears existing wheel)")
async def create_wheel(interaction: discord.Interaction):
    """Create a new wheel for the server"""
    guild_id = interaction.guild_id
    
    # Clear existing wheel
    bot.save_wheel_sections(guild_id, [])
    
    embed = discord.Embed(
        title="🎡 New Wheel Created!",
        description="Your wheel has been created! Use `/addsection` to add sections to your wheel.",
        color=0x00FF00
    )
    embed.add_field(
        name="Next Steps:",
        value="• Use `/addsection <name> <percentage> <color>` to add sections\n"
              "• Use `/listsections` to view your current wheel\n"
              "• Use `/spin` when ready to spin the wheel!",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addsection", description="Add a section to the wheel")
async def add_section(interaction: discord.Interaction, name: str, percentage: float, color: str):
    """Add a section to the wheel"""
    guild_id = interaction.guild_id
    sections = bot.get_wheel_sections(guild_id)
    
    # Validation
    if percentage <= 0 or percentage > 100:
        await interaction.response.send_message(
            "❌ Percentage must be between 0.1 and 100!", ephemeral=True
        )
        return
    
    # Check if name already exists
    if any(section.name.lower() == name.lower() for section in sections):
        await interaction.response.send_message(
            f"❌ A section with name '{name}' already exists!", ephemeral=True
        )
        return
    
    # Check total percentage
    current_total = bot.calculate_total_percentage(sections)
    if current_total + percentage > 100:
        await interaction.response.send_message(
            f"❌ Adding this section would exceed 100% total! Current total: {current_total}%", 
            ephemeral=True
        )
        return
    
    # Add section
    new_section = WheelSection(name, percentage, color)
    sections.append(new_section)
    bot.save_wheel_sections(guild_id, sections)
    
    new_total = bot.calculate_total_percentage(sections)
    
    embed = discord.Embed(
        title="✅ Section Added!",
        description=f"Added '{name}' to the wheel",
        color=int(new_section.color[1:], 16)
    )
    embed.add_field(name="Section", value=name, inline=True)
    embed.add_field(name="Percentage", value=f"{percentage}%", inline=True)
    embed.add_field(name="Color", value=new_section.color, inline=True)
    embed.add_field(name="Total Percentage", value=f"{new_total}%", inline=False)
    
    if new_total < 100:
        embed.add_field(
            name="Remaining", 
            value=f"{100 - new_total}% remaining to allocate", 
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="removesection", description="Remove a section from the wheel")
async def remove_section(interaction: discord.Interaction, name: str):
    """Remove a section from the wheel"""
    guild_id = interaction.guild_id
    sections = bot.get_wheel_sections(guild_id)
    
    # Find and remove section
    section_to_remove = None
    for section in sections:
        if section.name.lower() == name.lower():
            section_to_remove = section
            break
    
    if not section_to_remove:
        await interaction.response.send_message(
            f"❌ No section found with name '{name}'!", ephemeral=True
        )
        return
    
    sections.remove(section_to_remove)
    bot.save_wheel_sections(guild_id, sections)
    
    new_total = bot.calculate_total_percentage(sections)
    
    embed = discord.Embed(
        title="🗑️ Section Removed!",
        description=f"Removed '{section_to_remove.name}' from the wheel",
        color=0xFF4444
    )
    embed.add_field(name="Remaining Sections", value=len(sections), inline=True)
    embed.add_field(name="Total Percentage", value=f"{new_total}%", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsection", description="Edit an existing section")
async def edit_section(interaction: discord.Interaction, name: str, 
                      new_percentage: float, new_color: str):
    """Edit an existing section"""
    guild_id = interaction.guild_id
    sections = bot.get_wheel_sections(guild_id)
    
    # Find section
    section_to_edit = None
    for section in sections:
        if section.name.lower() == name.lower():
            section_to_edit = section
            break
    
    if not section_to_edit:
        await interaction.response.send_message(
            f"❌ No section found with name '{name}'!", ephemeral=True
        )
        return
    
    # Validation
    if new_percentage <= 0 or new_percentage > 100:
        await interaction.response.send_message(
            "❌ Percentage must be between 0.1 and 100!", ephemeral=True
        )
        return
    
    # Check total percentage (excluding current section)
    current_total = bot.calculate_total_percentage(sections) - section_to_edit.percentage
    if current_total + new_percentage > 100:
        await interaction.response.send_message(
            f"❌ This change would exceed 100% total! Current total without this section: {current_total}%", 
            ephemeral=True
        )
        return
    
    # Update section
    old_color = section_to_edit.color
    section_to_edit.percentage = new_percentage
    section_to_edit.color = section_to_edit._parse_color(new_color)
    
    bot.save_wheel_sections(guild_id, sections)
    
    new_total = bot.calculate_total_percentage(sections)
    
    embed = discord.Embed(
        title="✏️ Section Edited!",
        description=f"Updated '{name}'",
        color=int(section_to_edit.color[1:], 16)
    )
    embed.add_field(name="New Percentage", value=f"{new_percentage}%", inline=True)
    embed.add_field(name="New Color", value=section_to_edit.color, inline=True)
    embed.add_field(name="Total Percentage", value=f"{new_total}%", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="listsections", description="List all sections in the current wheel")
async def list_sections(interaction: discord.Interaction):
    """List all sections in the wheel"""
    guild_id = interaction.guild_id
    sections = bot.get_wheel_sections(guild_id)
    
    if not sections:
        await interaction.response.send_message(
            "❌ No sections in the wheel! Use `/addsection` to add some.", ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🎡 Current Wheel Sections",
        description=f"Total: {len(sections)} sections",
        color=0x0099FF
    )
    
    total_percentage = bot.calculate_total_percentage(sections)
    
    for i, section in enumerate(sections, 1):
        embed.add_field(
            name=f"{i}. {section.name}",
            value=f"**{section.percentage}%** • {section.color}",
            inline=True
        )
    
    embed.add_field(
        name="📊 Total Percentage",
        value=f"{total_percentage}% / 100%",
        inline=False
    )
    
    if total_percentage < 100:
        embed.add_field(
            name="⚠️ Warning",
            value=f"{100 - total_percentage}% remaining - wheel may not work properly until 100%",
            inline=False
        )
    
    # Generate and attach wheel image
    wheel_image = bot.renderer.create_wheel_image(sections)
    file = discord.File(wheel_image, filename="wheel_preview.png")
    embed.set_image(url="attachment://wheel_preview.png")
    
    await interaction.response.send_message(embed=embed, file=file)

@bot.tree.command(name="ping", description="Test if the bot is working")
async def ping(interaction: discord.Interaction):
    """Simple test command to verify bot is working"""
    embed = discord.Embed(
        title="🏓 Pong!",
        description="Bot is online and working!",
        color=0x00FF00
    )
    embed.add_field(name="Server", value=interaction.guild.name, inline=True)
    embed.add_field(name="User", value=interaction.user.mention, inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="spin", description="Spin the wheel and get a random result!")
async def spin_wheel(interaction: discord.Interaction):
    """Spin the wheel and announce the winner"""
    guild_id = interaction.guild_id
    sections = bot.get_wheel_sections(guild_id)
    
    if not sections:
        await interaction.response.send_message(
            "❌ No sections in the wheel! Use `/addsection` to add some.", ephemeral=True
        )
        return
    
    total_percentage = bot.calculate_total_percentage(sections)
    
    if total_percentage < 100:
        await interaction.response.send_message(
            f"⚠️ Wheel is only {total_percentage}% complete! Add more sections to reach 100%.",
            ephemeral=True
        )
        return
    
    # Defer response for processing time
    await interaction.response.defer()
    
    # Calculate winner based on weighted random selection
    rand_num = random.uniform(0, total_percentage)
    current_sum = 0
    winner = None
    
    for section in sections:
        current_sum += section.percentage
        if rand_num <= current_sum:
            winner = section.name
            break
    
    # Fallback (shouldn't happen)
    if not winner:
        winner = sections[0].name
    
    # Generate wheel image with winner highlighted
    wheel_image = bot.renderer.create_wheel_image(sections, winner)
    file = discord.File(wheel_image, filename="wheel_result.png")
    
    # Create result embed
    embed = discord.Embed(
        title="🎉 Wheel Spin Result!",
        description=f"**🎯 Winner: {winner}**",
        color=0xFFD700
    )
    
    # Find winner section for additional info
    winner_section = next(s for s in sections if s.name == winner)
    embed.add_field(
        name="Winning Section Details",
        value=f"**Probability:** {winner_section.percentage}%\n**Color:** {winner_section.color}",
        inline=False
    )
    
    embed.set_image(url="attachment://wheel_result.png")
    embed.set_footer(text="🎡 Spin again anytime with /spin!")
    
    await interaction.followup.send(embed=embed, file=file)

# Error handling
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle slash command errors"""
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏰ Command is on cooldown! Try again in {error.retry_after:.2f} seconds.",
            ephemeral=True
        )
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command!",
            ephemeral=True
        )
    else:
        print(f"Error in command: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An unexpected error occurred! Please try again.",
                ephemeral=True
            )

if __name__ == "__main__":
    # Bot token should be set as environment variable
    token = os.getenv('DISCORD_BOT_TOKEN')
    
    if not token:
        print("❌ Please set the DISCORD_BOT_TOKEN environment variable!")
        print("Example: export DISCORD_BOT_TOKEN='your_bot_token_here'")
        exit(1)
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Invalid bot token! Please check your DISCORD_BOT_TOKEN.")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")