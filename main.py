# ── Project Moon Discord Bot vPrescript ──
from dotenv import load_dotenv
import os
import discord
from discord.ext import commands, tasks
import random
import datetime

# --- 讀取 .env Token ---
TOKEN = os.getenv("bot_token")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=">", intents=intents)

TERMINAL_VERSION = "THE INDEX TERMINAL v6.1"

# --- 記憶體資料庫 ---
commands_db = {}
stats_db = {}

# --- 完全隨機元素庫，每個庫 50 個 ---
PEOPLE = [f"person #{i}" for i in range(1,51)]
ITEMS = [f"item #{i}" for i in range(1,51)]
ANIMALS = [f"animal #{i}" for i in range(1,51)]
OBJECTS = [f"object #{i}" for i in range(1,51)]
COLORS = [
    "red","blue","green","yellow","orange","purple","black","white","scarlet","tan",
    "pink","grey","maroon","cyan","magenta","lime","olive","navy","teal","indigo",
    "violet","gold","silver","bronze","beige","peach","lavender","coral","turquoise",
    "amber","cream","chocolate","plum","rose","mustard","mint","apricot","charcoal",
    "cerulean","fuchsia","jade","sapphire","ruby","emerald","topaz","onyx","copper",
    "pearl","ivory","rust","burgundy"
]
TIMES = [
    "midnight","dawn","noon","evening","sunset","morning","twilight","late night",
    "pre-dawn","early morning","late morning","mid-morning","sunrise","midday",
    "afternoon","evening dusk","midnight quiet","mid-afternoon","evening prime",
    "twilight dusk","late evening","early dusk","late noon","pre-midnight","sunrise early",
    "morning prime","noonish","midnight hour","twilight hour","dawn light","morning fog",
    "evening calm","sunset bright","late afternoon","midday sun","pre-noon","mid-evening",
    "dusk light","twilight calm","late night fog","early morning mist","sunrise glow",
    "mid-morning light","noon bright","evening shadow","nightfall","pre-dawn light","dawn quiet"
]
NUMBERS = [random.randint(1,500) for _ in range(50)]
DISTANCES = [random.randint(1,500) for _ in range(50)]
MINUTES = [random.randint(1,20) for _ in range(50)]

# --- 指令模板 ---
SENTENCE_TEMPLATES = [
    "Take a step and go on a date with {person} holding {item}. Shortly, measure their height.",
    "Next time you are angry, scream at {person} {number} times.",
    "Without drawing attention to yourself, wait for the {number}th person you come across to leave.",
    "Wear a {color} ribbon and confirm that no one is watching and hide behind {object}. Do not check the time again.",
    "At {time}, walk slowly and grab hold of {person} and get their name, then ignore them entirely.",
    "If the {item} is missing, stop listening and eat only foods that are {color}. Return home directly after.",
    "Observe the closest {animal} from a distance for {minutes} minutes.",
    "Look at the nearest {object} and bind your wrists together for {minutes} minutes.",
    "While using a pack of {item}, avoid thinking about it and hop like a bunny to whoever notices you first.",
    "Walk {distance1} meters, then {distance2} meters in any direction, betray a friend without speaking.",
    "Pick up the {object} and carry it to {person} silently at {time}.",
    "Trace {animal} quietly, tie a {color} ribbon around {item}, and wait for {minutes} minutes.",
    "Approach {person} holding {object} and report their reaction immediately.",
    "Crouch behind {object} and observe {animal} until {time}.",
    "Move {distance1} meters, then {distance2} meters, then hide in {object} for {minutes} minutes."
]

# --- 生成一億條完整指令 ---
COMMAND_POOL = []
for _ in range(100000000):
    template = random.choice(SENTENCE_TEMPLATES)
    command = template.format(
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
    )
    COMMAND_POOL.append(command)

# --- 使用者狀態 ---
def get_user_stats(user_id):
    if user_id not in stats_db:
        stats_db[user_id] = {
            "completed": 0,
            "disobeyed": 0,
            "stability": 100
        }
    return stats_db[user_id]

# --- 階級系統 ---
def get_rank(stats):
    s = stats["stability"]
    d = stats["disobeyed"]
    if s >= 95 and d == 0:
        return "完美指向者"
    elif s >= 80:
        return "高位執行者"
    elif s >= 60:
        return "標準執行者"
    elif s >= 40:
        return "偏移觀測體"
    elif s > 0:
        return "重大偏移個體"
    else:
        return "待清除異常"

# --- 食指審判事件 ---
async def judgement_event(ctx, stats):
    outcome = random.randint(1,100)
    if outcome <= 50:
        stats["stability"] = 0
        await ctx.send("⚠ 食指審判啟動\n⚠ 判定結果：清除\n此個體將被完全標記。")
    elif outcome <= 85:
        stats["stability"] += 15
        await ctx.send("⚠ 食指審判啟動\n⚠ 判定結果：觀測延長\n給予一次修正機會。")
    else:
        stats["stability"] = 100
        stats["disobeyed"] = 0
        await ctx.send("⚠ 食指審判啟動\n⚠ 判定結果：完全重置\n軌跡已被重新校準。")

# --- 產生命令 ---
def generate_command(user_id):
    stats = get_user_stats(user_id)
    deviation = round(random.uniform(5,30) + stats["disobeyed"]*5,2)
    deadline = datetime.datetime.now() + datetime.timedelta(minutes=random.randint(3,8))
    command_text = random.choice(COMMAND_POOL)
    data = {
        "command": command_text,
        "deviation": deviation,
        "deadline": deadline,
        "status": "待執行"
    }
    commands_db[user_id] = data
    return data

# --- Discord 指令 ---
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

@bot.command()
async def 完成(ctx):
    user_id = ctx.author.id
    if user_id not in commands_db:
        await ctx.send("未檢測到有效命令。")
        return
    data = commands_db[user_id]
    stats = get_user_stats(user_id)
    if data["status"] != "待執行":
        await ctx.send("命令已結束。")
        return
    data["status"] = "已完成"
    stats["completed"] += 1
    stats["stability"] = min(100, stats["stability"] + 2)
    await ctx.send(f"[{TERMINAL_VERSION}]\n> 命令執行成功。\n> 偏移穩定。\n> 穩定度：{stats['stability']}\n> 狀態更新：已完成")

@bot.command()
async def 違抗(ctx):
    user_id = ctx.author.id
    if user_id not in commands_db:
        await ctx.send("未檢測到有效命令。")
        return
    data = commands_db[user_id]
    stats = get_user_stats(user_id)
    if data["status"] != "待執行":
        await ctx.send("命令已結束。")
        return
    data["status"] = "違抗"
    stats["disobeyed"] += 1
    stats["stability"] -= 10
    await ctx.send(f"[{TERMINAL_VERSION}]\n⚠ 偵測到違抗行為。\n⚠ 偏移急遽上升。\n⚠ 穩定度下降至：{stats['stability']}\n⚠ 已標記為觀測對象。")
    if stats["stability"] <= 20 or stats["disobeyed"] >= 5:
        await judgement_event(ctx, stats)

@bot.command()
async def 狀態(ctx):
    stats = get_user_stats(ctx.author.id)
    rank = get_rank(stats)
    msg = f"[{TERMINAL_VERSION}]\n階級：{rank}\n完成次數：{stats['completed']}\n違抗次數：{stats['disobeyed']}\n穩定度：{stats['stability']}"
    if stats["stability"] == 0:
        msg += "\n⚠ 系統警告：目標已被標記為清除對象。"
    await ctx.send(msg)

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

@bot.event
async def on_ready():
    print(f"食指命令分配系統 v6.1 已啟動：{bot.user}")
    check_deadlines.start()

bot.run(TOKEN)
