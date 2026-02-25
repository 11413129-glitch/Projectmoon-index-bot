from dotenv import load_dotenv
import os
import discord
from discord import app_commands
import random
import datetime
import sqlite3

# --- 讀取 Token ---
TOKEN = os.getenv("bot_token")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

TERMINAL_VERSION = "THE INDEX TERMINAL v8.0"

# =========================
# SQLite 永久資料庫
# =========================

conn = sqlite3.connect("index_data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    completed INTEGER DEFAULT 0,
    disobeyed INTEGER DEFAULT 0,
    stability INTEGER DEFAULT 100
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS commands (
    user_id INTEGER PRIMARY KEY,
    command TEXT,
    deviation REAL,
    deadline TEXT,
    status TEXT
)
""")

conn.commit()

# =========================
# 10000 完全隨機指令池
# =========================

PEOPLE = [f"person #{i}" for i in range(1,51)]
ITEMS = [f"item #{i}" for i in range(1,51)]
ANIMALS = [f"animal #{i}" for i in range(1,51)]
OBJECTS = [f"object #{i}" for i in range(1,51)]

COLORS = ["red","blue","green","yellow","orange","purple","black","white"]
TIMES = ["midnight","dawn","noon","evening","sunset","morning"]
NUMBERS = [random.randint(1,500) for _ in range(50)]
DISTANCES = [random.randint(1,500) for _ in range(50)]
MINUTES = [random.randint(1,20) for _ in range(50)]

TEMPLATES = [
    "Approach {person} holding {item} at {time}.",
    "Observe {animal} for {minutes} minutes.",
    "Move {distance1}m then {distance2}m and hide behind {object}.",
    "Shout at {person} {number} times.",
    "Wear a {color} ribbon and wait."
]

COMMAND_POOL = []
for _ in range(10000):
    template = random.choice(TEMPLATES)
    COMMAND_POOL.append(template.format(
        person=random.choice(PEOPLE),
        item=random.choice(ITEMS),
        animal=random.choice(ANIMALS),
        object=random.choice(OBJECTS),
        color=random.choice(COLORS),
        time=random.choice(TIMES),
        number=random.choice(NUMBERS),
        distance1=random.choice(DISTANCES),
        distance2=random.choice(DISTANCES),
        minutes=random.choice(MINUTES)
    ))

# =========================
# 工具函式
# =========================

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return (user_id, 0, 0, 100)
    return user

def update_user(user_id, completed, disobeyed, stability):
    cursor.execute("""
    UPDATE users SET completed=?, disobeyed=?, stability=?
    WHERE user_id=?
    """, (completed, disobeyed, stability, user_id))
    conn.commit()

def get_rank(stability, disobeyed):
    if stability >= 95 and disobeyed == 0:
        return "完美指向者"
    elif stability >= 80:
        return "高位執行者"
    elif stability >= 60:
        return "標準執行者"
    elif stability >= 40:
        return "偏移觀測體"
    elif stability > 0:
        return "重大偏移個體"
    else:
        return "待清除異常"

def generate_command(user_id):
    user = get_user(user_id)
    deviation = round(random.uniform(5,30) + user[2]*5,2)
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=random.randint(3,8))
    command_text = random.choice(COMMAND_POOL)

    cursor.execute("""
    INSERT OR REPLACE INTO commands
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        command_text,
        deviation,
        deadline.isoformat(),
        "待執行"
    ))
    conn.commit()

    return command_text, deviation, deadline

# =========================
# Slash Commands
# =========================

@tree.command(name="指令", description="生成食指命令")
async def command(interaction: discord.Interaction, member: discord.Member):

    command_text, deviation, deadline = generate_command(member.id)

    await interaction.response.send_message(f"""
[{TERMINAL_VERSION}]
目標：{member.name}

偏移值：{deviation}%

{command_text}

截止時間：{deadline.strftime("%H:%M:%S")}
""")

@tree.command(name="完成", description="完成命令")
async def complete(interaction: discord.Interaction):

    user = get_user(interaction.user.id)
    completed, disobeyed, stability = user[1], user[2], user[3]

    completed += 1
    stability = min(100, stability + 2)

    update_user(interaction.user.id, completed, disobeyed, stability)

    cursor.execute("UPDATE commands SET status='已完成' WHERE user_id=?", (interaction.user.id,))
    conn.commit()

    await interaction.response.send_message("命令執行成功。")

@tree.command(name="違抗", description="違抗命令")
async def disobey(interaction: discord.Interaction):

    user = get_user(interaction.user.id)
    completed, disobeyed, stability = user[1], user[2], user[3]

    disobeyed += 1
    stability -= 10
    if stability < 0:
        stability = 0

    update_user(interaction.user.id, completed, disobeyed, stability)

    await interaction.response.send_message("⚠ 偵測到違抗。")

@tree.command(name="狀態", description="查看狀態")
async def status(interaction: discord.Interaction):

    user = get_user(interaction.user.id)
    rank = get_rank(user[3], user[2])

    await interaction.response.send_message(f"""
階級：{rank}
完成：{user[1]}
違抗：{user[2]}
穩定度：{user[3]}
""", ephemeral=True)

# =========================

@client.event
async def on_ready():
    await tree.sync()
    print("Index Terminal v8 已啟動")

client.run(TOKEN)
