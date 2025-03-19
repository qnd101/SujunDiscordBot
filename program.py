import discord
from discord.ext import tasks
import asyncio
import yaml
import mc_manager
import time
import gyuhwasays
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

# Intents setup (optional, if you need to access certain features like member events)
intents = discord.Intents.default()
intents.message_content = True
# Bot prefix setupW
bot = discord.Client(intents=intents)


with open('bot_settings.yml', 'r') as file:
    settings = yaml.safe_load(file)["settings"]

mc_settings = settings["mc-manage"]
mcsrv = mc_manager.new(mc_settings["pause-time"], 
                      mc_settings["cool-time"],
                      mc_settings["start-script-path"],
                      mc_settings["backup-script-path"])
help_msg = f"""
# 사용법
/마크 : 마인크래프트 서버의 상태를 알려줍니다. 
*(OFF, LOADING, ON, PAUSED, SHUTDOWN, BACKUP) 중 하나입니다
*서버 인원이 0명이 되면 ON -> PAUSED (서버의 틱이 매우 느리게 흘러감)
*PAUSED 상태에서 {mc_settings["pause-time"]}분이 지나면 자동으로 PAUSED -> SHUTDOWN -> BACKUP -> OFF 의 과정이 진행됩니다.

/마크 켜: 마인크래프트 서버를 켭니다
*OFF -> LOADING -> ON 의 과정이 진행됩니다. 서버가 켜지는데는 최대 1분 정도 걸릴 수 있습니다.
*꺼진지 {mc_settings["cool-time"]}분 이내에 서버를 켤 수 없습니다. 이 경우 에러코드 2가 출력됩니다.

# 기능
서버 내 플레이어의 입장/퇴장, 채팅 내용을 자동으로 채널 내에 로그합니다.
서버가 꺼지면 바로 백업을 진행합니다. (최대 3개. 예전 백업은 소멸됨)

# 기타
서버의 주소는 {mc_settings["server-path"]}입니다. 
"""

status = ""

command_lock = asyncio.Lock() #I need to execute commands synchronously...

font = ImageFont.truetype("./NotoSansKR-Regular.ttf" or "arial.ttf", 20)
img = Image.open("gyuwha_500.jpg")

@bot.event
async def on_message(message : discord.Message):
    # Skip if the message is from the bot itself to avoid infinite loops
    async with command_lock:
        global mcsrv, prefix_map, global_state
        if message.content.startswith("/규화") and len(message.content) > 4:
            text = message.content[4:]
            try:
                result = gyuhwasays.gyuwhasays(text, font, img, (250, 0))
                result.show()
                with BytesIO() as image_binary:
                    result.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    image_file = discord.File(fp=image_binary, filename='pil_image.png')

                # Create an embed
                embed = discord.Embed(title="", description="")
                embed.set_image(url="attachment://pil_image.png")  # Important: Use attachment://

                # Send the embed and the file
                await message.reply(file=image_file, embed=embed)
            except:
                pass
            return
            
        content_split = message.content.split()
        
        if message.channel.id != mc_settings["channel-id"] or message.author == bot.user:
            return
        if content_split[0] != "/마크":
            return
        if len(content_split) == 1:
            await message.reply(content=status)
            return
        elif content_split[1] == "켜":
            result = mc_manager.start(mcsrv)
            await message.reply(content="서버 켜는중..." if result == 0 else f"서버를 켤 수 없음. 에러코드 {result}")
            return
        else:
            await message.reply(content=help_msg)

@tasks.loop(seconds=mc_settings["update-period"])
async def mcsrv_update():
    global mcsrv, status
    async with command_lock:
        channel = bot.get_channel(mc_settings["channel-id"])
        mc_manager.update(mcsrv)
        newstatus = mc_manager.get_status(mcsrv)
        if status != newstatus:
            print(f"status: {status}")
        status = newstatus
        while True:
            player, msg = mc_manager.try_pop_chat(mcsrv)
            if player and msg:
                await channel.send(f"{player}: {msg}")
            else:
                break

@mcsrv_update.before_loop
async def before():
    await bot.wait_until_ready()

# Event: on bot ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    mcsrv_update.start()

# Run the bot with your token
while True:
    try:
        bot.run(settings["token"])
    except Exception as e:
        print(f"Bot encountered an error: {e}")
        print("Retrying in 5 seconds...")
        time.sleep(5)