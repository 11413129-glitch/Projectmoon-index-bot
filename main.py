from dotenv import load_dotenv
import os
import discord
from discord import app_commands
import random
import datetime
import sqlite3

# =====================
# Token
# =====================
TOKEN = os.getenv("bot_token")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

TERMINAL_VERSION = "THE INDEX TERMINAL v10.0"

# =====================
# SQLite
# =====================
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

# =====================
# 工具函式
# =====================

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

# =====================
# 指令池（每項 >= 30）
# =====================

DAY_LOCATIONS = [
"人行道邊緣","商店門口","第二個路口","公車站旁","斑馬線中央",
"玻璃櫥窗前","咖啡店外","街角轉彎處","市場入口","高樓陰影下",
"銀行前階梯","便利商店外","天橋入口","公園長椅旁","地下道出口",
"郵局門前","十字路口中央","書店旁","電影院外牆","紅磚牆邊",
"廣場中央","辦公大樓前","車站大廳","停車場邊緣","鐵門旁",
"街燈下","行道樹旁","施工圍欄外","報攤旁","商場入口"
]

NIGHT_LOCATIONS = [
"無人巷道","天橋陰影下","熄燈建築外","封閉鐵門前","地下停車場",
"橋墩下","廢棄店面前","屋頂邊緣","空曠廣場","路燈閃爍處",
"夜市角落","河岸邊","隧道出口","黑暗樓梯間","舊倉庫旁",
"寂靜公園","雨遮陰影下","大樓後巷","關閉商場外","施工工地邊",
"停駛車輛旁","月光照射處","破舊牆面前","鐵橋中央","昏暗騎樓",
"停電街區","夜間便利店外","舊劇院前","陰暗樓道","空蕩月台"
]

NEUTRAL_ACTIONS = [
"停留三分鐘","保持沉默","觀察周圍動靜","確認目標是否回頭",
"不得與任何人交談","等待下一次鐘聲","站在原地不動",
"記住經過的三個人","放慢呼吸","避免與他人對視",
"記錄時間","聽取環境聲音","確認出口位置","保持距離",
"調整步伐","觀察天空變化","注意影子方向","計算路人數量",
"觀察光線變化","等待信號","記下車輛顏色","確認手機時間",
"數到二十","確認是否被注視","注意腳步聲","檢查四周門窗",
"觀察標誌","確認風向","保持冷靜","聆聽遠方聲響"
]

HIGH_LEVEL_ACTIONS = [
"干涉目標的決定","使對方改變行進方向","製造一次微小秩序偏移",
"阻止既定事件發生","迫使對方停下腳步","延遲某個結果的發生",
"讓一段對話無法完成","確保某人錯過關鍵時刻","打斷既定流程",
"製造錯誤選擇","讓秩序產生裂痕","干預一次決策",
"改變一條行進軌跡","引發不確定因素","擾亂一次計畫",
"改寫當下選擇","讓某個信號無法傳達","引導事件轉向",
"迫使時間延後","阻止訊息到達","打亂節奏","重置一次節點",
"迫使事件重來","使秩序鬆動","擾動命運線",
"讓目標產生猶豫","阻斷交集","改變既定步伐","讓錯誤發生"
]

TIME_DAY = [
"在紅燈亮起時","於人群最密集時","當陽光照射街道時",
"在鐘聲響起後","於正午之前","當影子最短時",
"在人聲最吵雜時","於第一班車到站時","當廣播響起時",
"於午餐時段","在門開啟瞬間","於工作開始時",
"在排隊最長時","當街燈尚未亮起時","於下午之前",
"當雲層遮住陽光時","於三分鐘內","在步行途中",
"當車流減少時","於轉角之前","當警示聲響起時",
"於商店開門時","在收銀聲響起後","當音樂停止時",
"於廣場鐘聲後","在第一聲喇叭聲後","於門關閉前",
"在雨未落下時","於公告結束後","當電梯開門時"
]

TIME_NIGHT = [
"在路燈熄滅後","於午夜鐘響時","當街道完全安靜時",
"在最後一班車離開後","於夜色最深時","當月光最亮時",
"在廣播結束後","於雨聲停止時","當影子消失時",
"於零點之前","在霧氣瀰漫時","當霓虹燈閃爍時",
"於警報聲後","在門上鎖後","當腳步聲遠去時",
"於夜班交接時","在空氣變冷時","當風停止時",
"於街道無人時","在燈光轉暗時","當最後一扇窗熄燈時",
"於凌晨之前","在月亮升起時","當遠方傳來回音時",
"於沉默之後","在低語停止時","當鐘聲回蕩時",
"於黑暗完全降臨時","在夜雨開始時","當星光出現時"
]

MAJOR_COMMANDS = [
"確保某件物品不再存在於此街區。",
"讓該區域的秩序產生一次不可逆偏移。",
"阻止命運進入下一階段。",
"於日落前干涉目標的既定選擇。",
"迫使一次關鍵事件中止。",
"使某人失去原本的路線。",
"讓時間錯開原本的節點。",
"切斷一段正在形成的聯繫。",
"迫使選擇改變方向。",
"讓秩序崩解一瞬間。",
"引發一次重大偏移。",
"使結果延後發生。",
"讓決定無法成立。",
"打破既定因果。",
"重寫此區域的軌跡。",
"迫使命運轉向。",
"阻斷一次交會。",
"讓未來產生裂縫。",
"迫使關鍵人物停下。",
"讓節點消失。",
"製造一次重大錯誤。",
"使時間停滯片刻。",
"引發無法預測的變化。",
"改寫一段命運線。",
"阻止關鍵相遇。",
"讓某人失去機會。",
"迫使秩序重新排列。",
"打斷一次重要對話。",
"讓未來改變方向。",
"使原本的結局失效。"
]

# =====================
# 生成指令
# =====================

def generate_command(user_id):

    user = get_user(user_id)
    disobeyed = user[2]
    stability = user[3]

    now = datetime.datetime.now()
    hour = now.hour

    time_mode = "day" if 6 <= hour < 18 else "night"

    difficulty = "high" if stability >= 85 else "normal"

    major_chance = 0.10
    if time_mode == "night":
        major_chance += 0.05
    if stability >= 90:
        major_chance += 0.05

    is_major = random.random() < major_chance

    if is_major:
        command_text = random.choice(MAJOR_COMMANDS)
        deviation = round(random.uniform(30, 60) + disobeyed * 8, 2)
    else:
        if time_mode == "day":
            location = random.choice(DAY_LOCATIONS)
            time_trigger = random.choice(TIME_DAY)
        else:
            location = random.choice(NIGHT_LOCATIONS)
            time_trigger = random.choice(TIME_NIGHT)

        action_pool = HIGH_LEVEL_ACTIONS if difficulty == "high" else NEUTRAL_ACTIONS
        action = random.choice(action_pool)

        template = random.choice([
            "{time}前往{location}，{action}。",
            "進入{location}並{action}。",
            "於{location}{action}。"
        ])

        command_text = template.format(
            time=time_trigger,
            location=location,
            action=action
        )

        deviation = round(random.uniform(5, 25) + disobeyed * 5, 2)

    deadline = now + datetime.timedelta(minutes=random.randint(4, 10))

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

    return command_text, deviation, deadline, is_major

# =====================
# Slash 指令
# =====================

@tree.command(name="指令", description="生成食指命令")
async def command(interaction: discord.Interaction, member: discord.Member):

    command_text, deviation, deadline, is_major = generate_command(member.id)
    unix_time = int(deadline.timestamp())

    color = discord.Color.dark_red() if is_major else discord.Color.dark_grey()
    title = "⚠ 重大指令" if is_major else "食指命令"

    embed = discord.Embed(
        title=title,
        description=command_text,
        color=color
    )

    embed.add_field(name="目標", value=member.name, inline=False)
    embed.add_field(name="偏移值", value=f"{deviation}%", inline=False)
    embed.add_field(name="截止時間", value=f"<t:{unix_time}:F>\n<t:{unix_time}:R>", inline=False)
    embed.set_footer(text=TERMINAL_VERSION)

    await interaction.response.send_message(embed=embed)

@client.event
async def on_ready():
    await tree.sync()
    print("Index Terminal v10 已啟動")

client.run(TOKEN)
