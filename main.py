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
# 載入 Token & 初始化
# =====================
load_dotenv()
TOKEN = os.getenv("bot_token")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
TERMINAL_VERSION = "THE INDEX TERMINAL v12.0"

# =====================
# SQLite 資料庫（優化版）
# =====================
conn = sqlite3.connect("index_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    completed INTEGER DEFAULT 0,
    disobeyed INTEGER DEFAULT 0,
    stability INTEGER DEFAULT 100
);

CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    command TEXT,
    deviation REAL,
    deadline TEXT,
    status TEXT DEFAULT '待執行',
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
""")
conn.commit()

# =====================
# 工具函式（封裝成 class）
# =====================
class Database:
    @staticmethod
    async def execute(query: str, params: tuple = ()):
        def _run():
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        return await asyncio.to_thread(_run)

    @staticmethod
    async def fetchone(query: str, params: tuple = ()):
        def _run():
            cursor.execute(query, params)
            return cursor.fetchone()
        return await asyncio.to_thread(_run)

    @staticmethod
    async def fetchall(query: str, params: tuple = ()):
        def _run():
            cursor.execute(query, params)
            return cursor.fetchall()
        return await asyncio.to_thread(_run)

# =====================
# 指令池（已擴充到 50 個）
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
    user = await Database.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not user:
        await Database.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        user = (user_id, 0, 0, 100)

    disobeyed = user[2]
    stability = user[3]

    now = datetime.datetime.now()
    hour = now.hour
    time_mode = "day" if 6 <= hour < 18 else "night"
    difficulty = "high" if stability >= 85 else "normal"

    major_chance = 0.12 if time_mode == "night" else 0.08
    major_chance += 0.05 if stability >= 90 else 0

    is_major = random.random() < major_chance

    if is_major:
        command_text = random.choice(MAJOR_COMMANDS)
        deviation = round(random.uniform(35, 65) + disobeyed * 7, 2)
    else:
        location = random.choice(DAY_LOCATIONS if time_mode == "day" else NIGHT_LOCATIONS)
        time_trigger = random.choice(TIME_DAY if time_mode == "day" else TIME_NIGHT)
        action = random.choice(HIGH_LEVEL_ACTIONS if difficulty == "high" else NEUTRAL_ACTIONS)
        command_text = f"{time_trigger}前往{location}，{action}。"
        deviation = round(random.uniform(6, 28) + disobeyed * 4.5, 2)

    deadline = now + datetime.timedelta(minutes=random.randint(5, 12))

    cmd_id = await Database.execute("""
        INSERT INTO commands (user_id, command, deviation, deadline, status)
        VALUES (?, ?, ?, ?, '待執行')
    """, (user_id, command_text, deviation, deadline.isoformat()))

    return command_text, deviation, deadline, is_major, cmd_id

# =====================
# 按鈕互動 View
# =====================
class CommandView(ui.View):
    def __init__(self, user_id: int, cmd_id: int):
        super().__init__(timeout=720)  # 12 分鐘
        self.user_id = user_id
        self.cmd_id = cmd_id

    @ui.button(label="✅ 服從", style=discord.ButtonStyle.green)
    async def obey(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("這不是你的指令。", ephemeral=True)

        await Database.execute(
            "UPDATE commands SET status='已完成' WHERE id=?", (self.cmd_id,)
        )
        await Database.execute(
            "UPDATE users SET completed = completed + 1, stability = stability + 8 "
            "WHERE user_id=?", (self.user_id,)
        )

        await interaction.response.edit_message(
            content="```ansi\n[2;32m【系統確認】指令已服從　穩定度 +8[0m```",
            view=None
        )
        self.stop()

    @ui.button(label="❌ 違抗", style=discord.ButtonStyle.red)
    async def disobey(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("這不是你的指令。", ephemeral=True)

        await Database.execute(
            "UPDATE commands SET status='已違抗' WHERE id=?", (self.cmd_id,)
        )
        await Database.execute(
            "UPDATE users SET disobeyed = disobeyed + 1, stability = stability - 18 "
            "WHERE user_id=?", (self.user_id,)
        )

        await interaction.response.edit_message(
            content="```ansi\n[2;31m【警告】違抗紀錄已上傳　穩定度 -18[0m```",
            view=None
        )
        self.stop()

# =====================
# Slash 指令
# =====================
@bot.tree.command(name="指令", description="生成食指命令")
@app_commands.describe(member="要下達指令的目標")
async def give_command(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()

    # 終端機開機動畫
    boot = [
        "▓▒░ INITIALIZING INDEX TERMINAL ░▒▓",
        "讀取偏移資料……",
        "同步命運線……",
        "計算軌跡偏差……",
        "連接觀測節點……",
        "解析目標識別碼……",
        "▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒"
    ]
    msg = await interaction.followup.send("```啟動中...```")
    for line in boot:
        await asyncio.sleep(0.5)
        await msg.edit(content=f"```{line}```")

    cmd_text, deviation, deadline, is_major, cmd_id = await generate_command(member.id)

    unix = int(deadline.timestamp())

    # 重大指令警告動畫
    if is_major:
        warnings = ["████████████████████", "⚠ CRITICAL OFFSET DETECTED ⚠", "命運線崩壞警報", "重新計算中..."]
        for w in warnings:
            await asyncio.sleep(0.7)
            await msg.edit(content=f"```{w}```")

    color = discord.Color.dark_red() if is_major else discord.Color.dark_grey()
    embed = discord.Embed(title="⚠ 重大指令" if is_major else "食指命令", 
                          description=cmd_text, color=color)
    embed.add_field(name="目標", value=member.mention, inline=False)
    embed.add_field(name="偏移值", value=f"`{deviation}%`", inline=False)
    embed.add_field(name="截止時間", value=f"<t:{unix}:F> (<t:{unix}:R>)", inline=False)
    embed.set_footer(text=TERMINAL_VERSION)

    await msg.edit(content=None, embed=embed, view=CommandView(member.id, cmd_id))

@bot.tree.command(name="狀態", description="查看個人穩定度與階級")
@app_commands.describe(member="要查詢的成員（預設自己）")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    user = await Database.fetchone("SELECT * FROM users WHERE user_id=?", (target.id,))
    if not user:
        return await interaction.response.send_message("該成員尚未被索引。", ephemeral=True)

    stability = user[3]
    disobeyed = user[2]

    rank = "完美指向者" if stability >= 95 and disobeyed == 0 else \
           "高位執行者" if stability >= 80 else \
           "標準執行者" if stability >= 60 else \
           "偏移觀測體" if stability >= 40 else \
           "重大偏移個體" if stability > 0 else "待清除異常"

    embed = discord.Embed(title=f"📋 {target.name} 的索引檔案", color=discord.Color.blue())
    embed.add_field(name="穩定度", value=f"`{stability}%`", inline=True)
    embed.add_field(name="違抗次數", value=f"`{disobeyed}` 次", inline=True)
    embed.add_field(name="當前階級", value=f"**{rank}**", inline=False)
    embed.set_footer(text=TERMINAL_VERSION)

    await interaction.response.send_message(embed=embed)

# =====================
# 逾期自動扣分
# =====================
@tasks.loop(seconds=30)
async def check_deadlines():
    now = datetime.datetime.now().isoformat()
    overdue = await Database.fetchall(
        "SELECT id, user_id FROM commands WHERE deadline < ? AND status = '待執行'",
        (now,)
    )
    for cmd_id, user_id in overdue:
        await Database.execute(
            "UPDATE users SET stability = stability - 12 WHERE user_id=?", (user_id,)
        )
        await Database.execute(
            "UPDATE commands SET status='逾期' WHERE id=?", (cmd_id,)
        )

# =====================
# 啟動
# =====================
@bot.event
async def on_ready():
    await bot.tree.sync()
    check_deadlines.start()
    print(f"✅ {TERMINAL_VERSION} 已成功連線並啟動")

bot.run(TOKEN)
