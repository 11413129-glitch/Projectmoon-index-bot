# =====================
# THE INDEX TERMINAL v13.0
# =====================

from dotenv import load_dotenv
import os
import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import random
import datetime
import sqlite3
import asyncio

# =====================
# 載入 Token
# =====================

load_dotenv()
TOKEN = os.getenv("bot_token")

TERMINAL_VERSION = "THE INDEX TERMINAL v13.0"

# =====================
# Discord 初始化
# =====================

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# =====================
# SQLite 初始化
# =====================

conn = sqlite3.connect("index_data.db", check_same_thread=False)

def clamp(value, min_v=0, max_v=100):
    return max(min_v, min(max_v, value))

class Database:

    @staticmethod
    async def execute(query: str, params: tuple = ()):
        def _run():
            cur = conn.cursor()
            cur.execute(query, params)
            conn.commit()
            return cur.lastrowid
        return await asyncio.to_thread(_run)

    @staticmethod
    async def fetchone(query: str, params: tuple = ()):
        def _run():
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()
        return await asyncio.to_thread(_run)

    @staticmethod
    async def fetchall(query: str, params: tuple = ()):
        def _run():
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()
        return await asyncio.to_thread(_run)

# 建表
async def init_db():
    await Database.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        completed INTEGER DEFAULT 0,
        disobeyed INTEGER DEFAULT 0,
        stability INTEGER DEFAULT 100
    )
    """)
    await Database.execute("""
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        command TEXT,
        deviation REAL,
        deadline TEXT,
        status TEXT DEFAULT '待執行'
    )
    """)

# =====================
# 指令池
# =====================

DAY_LOCATIONS = [f"城市區域{i}" for i in range(1, 51)]
NIGHT_LOCATIONS = [f"夜間區域{i}" for i in range(1, 51)]
NEUTRAL_ACTIONS = [f"進行觀測行為{i}" for i in range(1, 51)]
HIGH_LEVEL_ACTIONS = [f"干涉命運節點{i}" for i in range(1, 51)]
TIME_DAY = [f"白晝時間點{i}" for i in range(1, 51)]
TIME_NIGHT = [f"夜晚時間點{i}" for i in range(1, 51)]
MAJOR_COMMANDS = [f"執行重大偏移行動{i}。" for i in range(1, 51)]

# =====================
# 生成指令
# =====================

async def generate_command(user_id: int):

    user = await Database.fetchone(
        "SELECT completed, disobeyed, stability FROM users WHERE user_id=?",
        (user_id,)
    )

    if not user:
        await Database.execute(
            "INSERT INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        completed, disobeyed, stability = 0, 0, 100
    else:
        completed, disobeyed, stability = user

    now = datetime.datetime.utcnow()
    hour = now.hour

    is_day = 6 <= hour < 18
    difficulty_high = stability >= 85

    # 改良重大指令機率（更平衡）
    major_chance = 0.06
    if not is_day:
        major_chance += 0.05
    major_chance += min(disobeyed * 0.02, 0.12)

    is_major = random.random() < major_chance

    if is_major:
        command_text = random.choice(MAJOR_COMMANDS)
        deviation = round(random.uniform(35, 65) + disobeyed * 5, 2)
    else:
        location = random.choice(DAY_LOCATIONS if is_day else NIGHT_LOCATIONS)
        time_trigger = random.choice(TIME_DAY if is_day else TIME_NIGHT)
        action = random.choice(HIGH_LEVEL_ACTIONS if difficulty_high else NEUTRAL_ACTIONS)
        command_text = f"{time_trigger}前往{location}，{action}。"
        deviation = round(random.uniform(8, 28) + disobeyed * 3, 2)

    deadline = now + datetime.timedelta(minutes=random.randint(5, 12))

    cmd_id = await Database.execute("""
        INSERT INTO commands (user_id, command, deviation, deadline)
        VALUES (?, ?, ?, ?)
    """, (user_id, command_text, deviation, deadline.isoformat()))

    return command_text, deviation, deadline, is_major, cmd_id

# =====================
# View
# =====================

class CommandView(ui.View):

    def __init__(self, user_id: int, cmd_id: int):
        super().__init__(timeout=720)
        self.user_id = user_id
        self.cmd_id = cmd_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的指令。", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        await Database.execute(
            "UPDATE commands SET status='逾期' WHERE id=? AND status='待執行'",
            (self.cmd_id,)
        )

    @ui.button(label="✅ 服從", style=discord.ButtonStyle.green)
    async def obey(self, interaction: discord.Interaction, button: ui.Button):

        await Database.execute(
            "UPDATE commands SET status='已完成' WHERE id=?",
            (self.cmd_id,)
        )

        await Database.execute("""
            UPDATE users
            SET completed = completed + 1,
                stability = MIN(100, stability + 8)
            WHERE user_id=?
        """, (self.user_id,))

        await interaction.response.edit_message(
            content="```ansi\n[2;32m【系統確認】指令已服從　穩定度 +8[0m```",
            view=None
        )

    @ui.button(label="❌ 違抗", style=discord.ButtonStyle.red)
    async def disobey(self, interaction: discord.Interaction, button: ui.Button):

        await Database.execute(
            "UPDATE commands SET status='已違抗' WHERE id=?",
            (self.cmd_id,)
        )

        await Database.execute("""
            UPDATE users
            SET disobeyed = disobeyed + 1,
                stability = MAX(0, stability - 18)
            WHERE user_id=?
        """, (self.user_id,))

        await interaction.response.edit_message(
            content="```ansi\n[2;31m【警告】違抗紀錄已上傳　穩定度 -18[0m```",
            view=None
        )

# =====================
# Slash Commands
# =====================

@bot.tree.command(name="指令", description="生成食指命令")
async def give_command(interaction: discord.Interaction, member: discord.Member):

    await interaction.response.defer()

    msg = await interaction.followup.send("```INITIALIZING...```")

    cmd_text, deviation, deadline, is_major, cmd_id = await generate_command(member.id)

    unix = int(deadline.timestamp())

    color = discord.Color.dark_red() if is_major else discord.Color.dark_grey()

    embed = discord.Embed(
        title="⚠ 重大指令" if is_major else "食指命令",
        description=cmd_text,
        color=color
    )

    embed.add_field(name="目標", value=member.mention, inline=False)
    embed.add_field(name="偏移值", value=f"`{deviation}%`", inline=True)
    embed.add_field(name="截止時間", value=f"<t:{unix}:F> (<t:{unix}:R>)", inline=False)
    embed.set_footer(text=TERMINAL_VERSION)

    await msg.edit(embed=embed, content=None,
                   view=CommandView(member.id, cmd_id))

@bot.tree.command(name="狀態", description="查看穩定度")
async def profile(interaction: discord.Interaction, member: discord.Member = None):

    target = member or interaction.user

    user = await Database.fetchone(
        "SELECT stability, disobeyed FROM users WHERE user_id=?",
        (target.id,)
    )

    if not user:
        return await interaction.response.send_message("尚未建立索引資料。", ephemeral=True)

    stability, disobeyed = user

    rank = (
        "完美指向者" if stability >= 95 and disobeyed == 0 else
        "高位執行者" if stability >= 80 else
        "標準執行者" if stability >= 60 else
        "偏移觀測體" if stability >= 40 else
        "重大偏移個體" if stability > 0 else
        "待清除異常"
    )

    embed = discord.Embed(
        title=f"{target.name} 的索引檔案",
        color=discord.Color.blue()
    )

    embed.add_field(name="穩定度", value=f"`{stability}%`")
    embed.add_field(name="違抗次數", value=f"`{disobeyed}` 次")
    embed.add_field(name="階級", value=f"**{rank}**", inline=False)
    embed.set_footer(text=TERMINAL_VERSION)

    await interaction.response.send_message(embed=embed)

# =====================
# 逾期扣分
# =====================

@tasks.loop(seconds=30)
async def check_deadlines():

    now = datetime.datetime.utcnow().isoformat()

    overdue = await Database.fetchall("""
        SELECT id, user_id FROM commands
        WHERE deadline < ? AND status='待執行'
    """, (now,))

    for cmd_id, user_id in overdue:

        await Database.execute("""
            UPDATE users
            SET stability = MAX(0, stability - 12)
            WHERE user_id=?
        """, (user_id,))

        await Database.execute("""
            UPDATE commands SET status='逾期'
            WHERE id=?
        """, (cmd_id,))

# =====================
# 啟動
# =====================

@bot.event
async def on_ready():
    await init_db()
    await bot.tree.sync()
    check_deadlines.start()
    print(f"✅ {TERMINAL_VERSION} 已啟動")

bot.run(TOKEN)
