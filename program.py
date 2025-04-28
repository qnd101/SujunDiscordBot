import discord
from discord.ext import tasks
import asyncio
import yaml
import mc_manager
import time
import gyuhwasays
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from os.path import join, basename, exists
import random
import subprocess
import alchemy
import bothosting
import os
import csv
import re

# Intents setup (optional, if you need to access certain features like member events)
intents = discord.Intents.default()
intents.message_content = True
# Bot prefix setupW
bot = discord.Client(intents=intents)

gs_commands = None

with open('./bot_settings.yml', 'r') as file:
    settings = yaml.safe_load(file)["settings"]

mc_settings = settings["mc-manage"]
mc_loaded = False
mc_status = ""
mcsrv = None

cmd_reserved = {"/마크": "마인크래프트 서버에 관한 명령어입니다. /마크 켜: 서버를 켭니다",
                "/명령어": "명령어 목록을 보여줍니다. /명령어 자세히: 명령어에 대한 자세한 설명을 보여줍니다",
                "/재로딩": "명령어 목록을 갱신합니다. 관리자만 사용 가능합니다.",
                "/조합": "두 아이템을 조합합니다. 조합한 적이 있는 아이템만 조합할 수 있습니다. 조합에 성공하면 수준이 올라갑니다.",
                "/조합법": "제작한 적 있는 아이템의 조합법을 보여줍니다.",
                "/남은조합": "해당 아이템에 대해 몇개의 조합법이 남았는지 알려줍니다.",
                "/아이템": "조합한 적이 있는 아이템을 보여줍니다. 더 이상 조합법이 없는 아이템은 표시하지 않습니다.",
                "/크레딧": "현재 크레딧을 보여줍니다.",
                "/랭킹": "크레딧의 랭킹을 보여줍니다.",
                "/퀘스트": "조합 퀘스트를 보여줍니다.",
                "/업로드": "봇에 필요한 파일을 업로드 합니다.",
                "/다운" : "파일을 다운 받습니다.",
                "/파일" : "업로드한 파일들을 보여줍니다.",
                "/삭제" : "업로드된 파일을 지웁니다.",
                "/봇": "봇의 상태를 알려줍니다. /봇 켜: 봇을 켭니다. /봇 꺼: 봇을 끕니다."}
cmd_dict = cmd_reserved.copy()

command_lock = asyncio.Lock() #I need to execute commands synchronously...
font = ImageFont.truetype("./NotoSansKR-Regular.ttf" or "arial.ttf", 20)

with open(settings["credits-path"], newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    credits = {int(row[0]):int(row[1]) for row in reader}

alchemy_config = settings["alchemy-config"]
alchemy_manager = alchemy.Alchemy(alchemy_config["items-path"], alchemy_config["recipes-path"], alchemy_config["founditems-path"])

hosting_config = settings["bot-hosting-config"]
hosting_manager = bothosting.HostingManger(hosting_config["root-dir"], hosting_config["init-script"])


def load_mc():
    global mc_loaded, mcsrv
    if mc_loaded:
        return
    mc_loaded = True
    subprocess.run(["/bin/bash", mc_settings["load-script-path"]], capture_output=True, text=True)
    mcsrv = mc_manager.new(mc_settings["pause-time"], 
                    mc_settings["cool-time"],
                    mc_settings["start-script-path"],
                    mc_settings["backup-script-path"])

def load_gs_config():
    global gs_commands, cmd_dict
    with open(settings["gyuhwasays-config"], 'r') as file:
        gs_settings = yaml.safe_load(file)["settings"]
    gs_dir = gs_settings["imgdir"]
    gs_commands = gs_settings["commands"]
    for cmd_data in gs_commands:
        for data in cmd_data["data"]:
            data["img"] = Image.open(join(gs_dir, data["file"]))

    cmd_dict = cmd_reserved | {cmd_data["cmd"] : f"{len(cmd_data['data'])}개의 사진 중 하나를 무작위로 선정" for cmd_data in gs_commands} | {cmd_data["cmd"]+"[i]" : f"{len(cmd_data['data'])}개의 사진 중 i번째 사진을 선정" for cmd_data in gs_commands}

load_gs_config()

def format_list(li, col_cnt = 5, spacing = 10):
    return "\n".join("".join(s.ljust(spacing) for s in li[i:i+col_cnt]) for i in range(0, len(li), col_cnt) )

def is_safe_filename(name):
    if ".." in name or "/" in name or "\\" in name or "\x00" in name:
        return False
    if not re.match(r'^[\w.\-]+$', name):  # only allow a-z, A-Z, 0-9, _, -, .
        return False
    return True

@bot.event
async def on_message(message : discord.Message):
    global mcsrv, mc_status, settings, mc_settings
    global cmd_dict
    global gs_commands
    global alchemy_manager, credits
    global hosting_config, hosting_manager

    async with command_lock:
        content_split = message.content.split()        
        if len(content_split) == 0:
            return
        command = content_split[0]
        
        match command:
            case "/마크":
                if message.channel.id != mc_settings["channel-id"] or message.author == bot.user:
                    return
                if len(content_split) == 1:
                    if not mc_loaded:
                        await message.reply(content="데이터가 아직 로드되지 않았습니다. /마크 켜 명령어를 사용하면 서버를 로드한 후 켭니다.")
                    else:
                        await message.reply(content=mc_status)
                elif content_split[1] == "켜":
                    if not mc_loaded:
                        await message.reply(content="먼저 데이터를 로드합니다. 잠시만 기다려주세요.")
                        load_mc()
                        await message.reply(content="데이터를 로드했습니다.")
                    result = mc_manager.start(mcsrv)
                    await message.reply(content="서버 켜는중..." if result == 0 else f"서버를 켤 수 없음. 에러코드 {result}")
            case "/명령어":
                if len(content_split)>1 and content_split[1] == "자세히":
                    await message.reply(content="\n".join([f"{k}: {v}" for k, v in cmd_dict.items()]))
                else:
                    await message.reply(content=" ".join(cmd_dict.keys()))
            case "/재로딩":
                if message.author.id == settings["admin-id"]:
                    load_gs_config()
                    await message.reply(content="명령어 목록을 갱신했습니다.")
                else:
                    await message.reply(content="권한이 없습니다.")
            case "/업로드":
                if message.author.bot:
                    await message.reply(content=f"인간도 아닌게 어딜!")
                    return
                if not hosting_manager.user_exists(message.author.id):
                    await message.reply(content="아직 등록되지 않은 사용자입니다. 폴더를 생성하고 환경을 세팅합니다...")
                    hosting_manager.init_user(message.author.id)
                    await message.reply(content="등록 및 세팅이 완료되었습니다.")
                else:
                    hosting_manager.init_user(message.author.id) #do init anyways. (only creates user)

                for attachment in message.attachments:
                    if not is_safe_filename(attachment.filename):
                        await message.reply(f"{attachment.filename} 파일 이름이 올바르지 않습니다.")
                        continue
                    filename = basename(attachment.filename) #sanitizing
                    file_path = join(hosting_manager.user_dir(message.author.id), attachment.filename)
                    await attachment.save(file_path)
                    await message.channel.send(f"{attachment.filename} 업로드 완료!")
            
            case "/다운":
                if not hosting_manager.user_exists(message.author.id):
                    await message.reply("등록된 사용자가 아닙니다. 등록하려면 /업로드를 이용해주세요")
                    return
                if len(content_split) != 2:
                    await message.reply("파일명 1개를 입력해주세요.")
                    return
                if not is_safe_filename(content_split[1]):
                    await message.reply("파일 이름이 올바르지 않습니다.")
                    return
                filename = content_split[1]
                fullpath = join(hosting_manager.user_dir(message.author.id), filename)
                if not exists(fullpath):
                    await message.reply("해당 파일이 존재하지 않습니다.")
                else:
                    await message.reply(content=f"{content_split[1]}을 찾았습니다.", file=discord.File(fullpath))
            case "/삭제":
                if not hosting_manager.user_exists(message.author.id):
                    await message.reply("등록된 사용자가 아닙니다. 등록하려면 /업로드를 이용해주세요")
                    return
                if len(content_split) != 2:
                    await message.reply("파일명 1개를 입력해주세요.")
                    return
                if not is_safe_filename(content_split[1]):
                    await message.reply("파일 이름이 올바르지 않습니다.")
                    return
                fullpath = join(hosting_manager.user_dir(message.author.id), content_split[1])
                os.remove(fullpath)

            case "/봇":
                if not hosting_manager.user_exists(message.author.id):
                    await message.reply("등록된 사용자가 아닙니다. 등록하려면 /업로드를 이용해주세요")
                    return
                if len(content_split) == 1:
                    is_on = hosting_manager.bot_isrunning(message.author.id)
                    await message.reply(f"봇이 현재 {'켜져' if is_on else '꺼져'} 있습니다.")
                    return
                if content_split[1] == "켜":
                    if hosting_manager.bot_isrunning(message.author.id):
                        await message.reply("봇이 이미 켜져 있습니다.")
                        return
                    await message.reply("봇을 켰습니다.")
                    hosting_manager.init_user(message.author.id)
                    hosting_manager.bot_run(message.author.id)
                elif content_split[1] == "꺼":
                    if not hosting_manager.bot_isrunning(message.author.id):
                        await message.reply("봇이 꺼져 있습니다.")
                        return
                    await message.reply("봇을 끄는 중입니다.")
                    hosting_manager.bot_stop(message.author.id)
                    await message.reply("봇을 껐습니다.")
                
            case "/파일":
                if not hosting_manager.user_exists(message.author.id):
                    await message.reply("등록된 사용자가 아닙니다. 등록하려면 /업로드를 이용해주세요")
                    return
                dirs, files = hosting_manager.get_subobjs(message.author.id)
                await message.reply("```\n"+"\n".join(["📁 "+name for name in dirs]+["📄 "+name for name in files])+"\n```")
            
            case "/조합":
                if len(content_split) != 3:
                    await message.reply(content="아이템 2개를 입력해주세요.")
                    return
                for ing in content_split[1:]:
                    if ing not in alchemy_manager.founditems:
                        await message.reply(content=f"'{ing}' 은(는) 존재하지 않거나 아직 획득하지 못한 아이템입니다.")
                        return
                result = alchemy_manager.combine(content_split[1], content_split[2])
                if len(result) == 0:
                    return
                ing1_em = content_split[1]+alchemy_manager.get_emoji(content_split[1])
                ing2_em = content_split[2]+alchemy_manager.get_emoji(content_split[2])
                for found in result:
                    found_em = found+alchemy_manager.get_emoji(found)
                    
                    if found in alchemy_manager.founditems.keys():
                        found_user = await bot.fetch_user(alchemy_manager.founditems[found])
                        msg = f"'{found_em}' 은(는) {found_user} 이(가) 먼저 찾았어요..."
                        color = discord.Color.red()
                        title = "조합 성공! 그러나..."
                    else:
                        gain = len(alchemy_manager.founditems) // 20 + 1
                        if message.author.id in credits:    
                            credits[message.author.id] += gain
                        else:
                            credits[message.author.id] = gain

                        if found in alchemy_manager.quest1:
                            credits[message.author.id] += 50
                            await message.reply(content="퀘스트 완료! [+50 YEOP]")
                        if found in alchemy_manager.quest2:
                            credits[message.author.id] += 150
                            await message.reply(content="퀘스트 완료! [+150 YEOP]")

                        msg = f"'{found_em}' 을(를) 조합했다! 현재 크레딧: {credits[message.author.id]} YEOP **[+ {gain} YEOP]**"
                        with open(settings["credits-path"], "w", newline="") as f:
                            for key, value in credits.items():
                                f.write(f"{key}, {value}\n")
                        
                        alchemy_manager.process_newitem(found, message.author.id)
                
                        color = discord.Color.green()
                        title = "조합 성공!"
                    embed = discord.Embed(title=title, description=f"{ing1_em} + {ing2_em} = {found_em}", color=color)
                    await message.reply(embed=embed, content=msg)

            case "/남은조합":
                if len(content_split) != 2:
                    await message.reply(content="아이템 1개를 입력해주세요.")
                    return
                item = content_split[1]
                if item not in alchemy_manager.founditems:
                    await message.reply(content=f"'{item}' 은(는) 존재하지 않거나 아직 획득하지 못한 아이템입니다.")
                    return
                if item not in alchemy_manager.usable_items:
                    leftnew = 0
                else:
                    leftnew = alchemy_manager.usable_items[item]
                totalcrafts = alchemy_manager.craftable_items(item)
                await message.reply(content=f"{item+alchemy_manager.get_emoji(item)}으로 제작할 수 있는 아이템 {len(totalcrafts)}개 중 {leftnew}개 남았습니다.")
                
            case "/아이템":
                items = [key+alchemy_manager.get_emoji(key)+f"({val})" for key, val in alchemy_manager.usable_items.items()]
                for i in range(0, len(items), 150):
                    await message.reply(f"```\n{format_list(items[i:i+150], 6, 10)}\n```")
                await message.reply(f"총 {len(alchemy_manager.items)}개의 아이템 중 {len(alchemy_manager.founditems)}개를 찾았습니다. 이 중 조합법이 남은 아이템들만 표시했습니다.")

            case "/크레딧":
                cred = credits[message.author.id] if message.author.id in credits else 0
                await message.reply(f"현재 크레딧: {cred} YEOP")
            case "/랭킹":
                sortedlist = sorted(credits.items(), key=lambda x: x[1], reverse=True) 
                users = await asyncio.gather(*[bot.fetch_user(tup[0]) for tup in sortedlist])
                ranklist = [s for i in range(len(sortedlist)) for s in (users[i].name, str(sortedlist[i][1]))]
                await message.reply(content="```\n" + format_list(ranklist, 2, 25) + "\n```")

            case "/퀘스트":
                msg = "```\n즉시 조합 가능 [50 YEOP]: " \
                +", ".join(item + alchemy_manager.get_emoji(item) for item in alchemy_manager.quest1) \
                + "\n즉시 조합 못함 [150 YEOP]: " \
                +", ".join(item + alchemy_manager.get_emoji(item) for item in alchemy_manager.quest2) \
                + "\n```"
                await message.reply(content=msg)

            case "/조합법":
                if len(content_split) != 2:
                    await message.reply(content="아이템 1개를 입력해주세요.")
                    return
                item = content_split[1]
                if item not in alchemy_manager.founditems:
                    await message.reply(content=f"'{item}' 은(는) 존재하지 않거나 아직 획득하지 못한 아이템입니다.")
                    return
                recipe = alchemy_manager.known_recipes(item)
                print(recipe)
                recipe_text = " , ".join(f"{i1+alchemy_manager.get_emoji(i1)} + {i2+alchemy_manager.get_emoji(i2)}" for i1, i2 in recipe)
                await message.reply(content=f"'지금까지 알려진 {item+alchemy_manager.get_emoji(item)}' 의 조합법: \n{recipe_text}")
            case default:
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
    global mcsrv, mc_status
    async with command_lock:
        if not mc_loaded:
            return
        channel = bot.get_channel(mc_settings["channel-id"])
        mc_manager.update(mcsrv)
        newstatus = mc_manager.get_status(mcsrv)
        if mc_status != newstatus:
            print(f"status: {mc_status}")
        mc_status = newstatus
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