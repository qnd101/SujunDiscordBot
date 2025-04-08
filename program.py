import discord
from discord.ext import tasks
import asyncio
import yaml
import mc_manager
import time
import gyuhwasays
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from os.path import join
import random

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

cmd_reserved = {"/마크": "마인크래프트 서버에 관한 명령어입니다. /마크 켜: 서버를 켭니다",
                "/명령어": "명령어 목록을 보여줍니다. /명령어 자세히: 명령어에 대한 자세한 설명을 보여줍니다"}

status = ""

command_lock = asyncio.Lock() #I need to execute commands synchronously...

font = ImageFont.truetype("./NotoSansKR-Regular.ttf" or "arial.ttf", 20)

with open('gyuhwasays.yml', 'r') as file:
    gs_settings = yaml.safe_load(file)["settings"]
gs_dir = gs_settings["imgdir"]
gs_commands = gs_settings["commands"]
for cmd_data in gs_commands:
    for data in cmd_data["data"]:
        data["img"] = Image.open(join(gs_dir, data["file"]))

cmd_dict = cmd_reserved | {cmd_data["cmd"] : f"{len(cmd_data["data"])}개의 사진 중 하나를 무작위로 선정" for cmd_data in gs_commands} | {cmd_data["cmd"]+"[i]" : f"{len(cmd_data["data"])}개의 사진 중 i번째 사진을 선정" for cmd_data in gs_commands}

@bot.event
async def on_message(message : discord.Message):
    # Skip if the message is from the bot itself to avoid infinite loops
    async with command_lock:
        content_split = message.content.split()        
        if len(content_split) == 0:
            return
        command = content_split[0]
        
        if message.channel.id != mc_settings["channel-id"] or message.author == bot.user:
            return

        
        match command:
            case "/마크":
                global mcsrv, status
                if len(content_split) == 1:
                    await message.reply(content=status)
                elif content_split[1] == "켜":
                    result = mc_manager.start(mcsrv)
                    await message.reply(content="서버 켜는중..." if result == 0 else f"서버를 켤 수 없음. 에러코드 {result}")
            case "/명령어":
                global cmd_dict
                if len(content_split)>1 and content_split[1] == "자세히":
                    await message.reply(content="\n".join([f"{k}: {v}" for k, v in cmd_dict.items()]))
                else:
                    await message.reply(content=" ".join(cmd_dict.keys()))
            case default:
                global gs_commands
                cmd_data = next(filter(lambda x: command.startswith(x["cmd"]), gs_commands), None)
                if cmd_data is None:
                    # global help_msg
                    # await message.reply(content=help_msg)
                    return
                choices = len(cmd_data["data"])
                if len(command) == len(cmd_data["cmd"]):
                    chosen = cmd_data["data"][random.randint(0, choices-1)]
                else:
                    num = command[len(cmd_data["cmd"]):]
                    if num.isdigit() and int(num) <= choices:
                        chosen = cmd_data["data"][int(num)-1]
                    else:
                        return
                text = message.content[len(command):].strip()
                try:
                    result = gyuhwasays.gyuwhasays(text, font, chosen["img"], (chosen["x"], chosen["y"]))
                    with BytesIO() as image_binary:
                        result.save(image_binary, 'JPEG')
                        image_binary.seek(0)
                        image_file = discord.File(fp=image_binary, filename='pil_image.jpg')

                    # Create an embed
                    embed = discord.Embed(title="", description="")
                    embed.set_image(url="attachment://pil_image.jpg")  # Important: Use attachment://

                    # Send the embed and the file
                    await message.reply(file=image_file, embed=embed)
                finally:
                    return
                # if no command matched

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