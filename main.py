from dotenv import load_dotenv
import os
import discord
from discord.ext import commands, tasks
import random
import datetime

# --- 讀取 .env Token ---
TOKEN = os.getenv("bot_token")  # .env 裡寫 bot_token=你的Token

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=">", intents=intents)

TERMINAL_VERSION = "THE INDEX TERMINAL v5.10"

# === 記憶體資料庫 ===
commands_db = {}
stats_db = {}

COMMAND_POOL = [
    "於黎明前前往指定區域。",
    "觀測目標行為並回報。",
    "在無人知曉下留下標記。",
    "干涉既定軌跡。",
    "等待，直到命運允許行動。",
    "對指定對象傳達沉默。",
    "刪除不必要的干涉者。"
]

# --- 使用者狀態 ---
def get_user_stats(user_id):
    if user_id not in stats_db:
        stats_db[user_id] = {
            "completed": 0,
            "disobeyed": 0,
            "stability": 100
        }
    return stats_db[user_id]

# --- 產生命令 ---
def generate_command(user_id):
    stats = get_user_stats(user_id)
    base_deviation = random.uniform(5, 30)
    deviation = round(base_deviation + stats["disobeyed"] * 5, 2)
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=random.randint(3, 8))
    data = {
        "command": random.choice(COMMAND_POOL),
        "deviation": deviation,
        "deadline": deadline,
        "status": "待執行"
    }
    commands_db[user_id] = data
    return data

# --- 指令發佈 ---
@bot.command()
async def 指令(ctx, member: discord.Member):
    data = generate_command(member.id)
    output = f"""
[{TERMINAL_VERSION}]
目標：{member.name}

> 正在計算命運軌跡...
> 偏移值：{data['deviation']}%

> 發佈指令：
{data['command']}

> 截止時間：
{data['deadline'].strftime("%H:%M:%S")}

> 狀態：待執行
"""
    await ctx.send(output)

# --- 標記完成 ---
@bot.command()
async def 完成(ctx):
    user_id = ctx.author.id
    if user_id not in commands_db:
        await ctx.send("\n未檢測到有效命令。\n")
        return
    data = commands_db[user_id]
    stats = get_user_stats(user_id)
    if data["status"] != "待執行":
        await ctx.send("\n命令已結束。\n")
        return
    data["status"] = "已完成"
    stats["completed"] += 1
    stats["stability"] = min(100, stats["stability"] + 2)
    await ctx.send(f"""
[{TERMINAL_VERSION}]
> 命令執行成功。
> 偏移穩定。
> 穩定度：{stats['stability']}
> 狀態更新：已完成
""")

# --- 標記違抗 ---
@bot.command()
async def 違抗(ctx):
    user_id = ctx.author.id
    if user_id not in commands_db:
        await ctx.send("\n未檢測到有效命令。\n")
        return
    data = commands_db[user_id]
    stats = get_user_stats(user_id)
    if data["status"] != "待執行":
        await ctx.send("\n命令已結束。\n")
        return
    data["status"] = "違抗"
    stats["disobeyed"] += 1
    stats["stability"] -= 10
    await ctx.send(f"""
[{TERMINAL_VERSION}]
⚠ 偵測到違抗行為。
⚠ 偏移急遽上升。
⚠ 穩定度下降至：{stats['stability']}
⚠ 已標記為觀測對象。
""")

# --- 查看個人狀態 ---
@bot.command()
async def 狀態(ctx):
    stats = get_user_stats(ctx.author.id)
    await ctx.send(f"""
[{TERMINAL_VERSION}]
完成次數：{stats['completed']}
違抗次數：{stats['disobeyed']}
穩定度：{stats['stability']}
""")

# --- 自動逾期檢查 ---
@tasks.loop(seconds=30)
async def check_deadlines():
    now = datetime.datetime.now()
    for user_id, data in list(commands_db.items()):
        if data["status"] == "待執行" and now > data["deadline"]:
            stats = get_user_stats(user_id)
            data["status"] = "違抗"
            stats["disobeyed"] += 1
            stats["stability"] -= 5

# --- 啟動 Bot ---
@bot.event
async def on_ready():
    print(f"食指命令分配系統 v5.1 已啟動：{bot.user}")
    check_deadlines.start()


bot.run(TOKEN)
