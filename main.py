import amino
import os
import time
import asyncio
import dateutil.parser
import pretty_errors
from threading import Thread, Lock
EMAIL=os.environ.get('EMAIL') # админ сообщества И(!) ведущий в чатах
PASSWORD=os.environ.get('PASSWORD')
USERID=None # ставится автоматом
COMID=os.environ.get('COMMUNITY_ID') # id сообщества

lock = Lock()
WARNS = []
ANTI_SPAM = {}
JOIN_LEAVE_DETECTOR = {}
STRIKED_USERS = []



pretty_errors.configure(
    separator_character = '*',
    filename_display    = pretty_errors.FILENAME_EXTENDED,
    line_number_first   = True,
    display_link        = True,
    lines_before        = 5,
    lines_after         = 2,
    line_color          = pretty_errors.RED + '> ' + pretty_errors.default_config.line_color,
    code_color          = '  ' + pretty_errors.default_config.line_color,
    truncate_code       = True,
    display_locals      = True
)
pretty_errors.blacklist('c:/python')

#
#CLIENT, LOGIN, SUBCLIENT
#
client = amino.AsyncClient()
subclient = None

async def taskA():
    global subclient
    global client
    global USERID
    print("login")
    await client.login(email=EMAIL, password=PASSWORD)
    USERID = client.userId
    subclient = await amino.AsyncSubClient(comId=COMID, profile=client.profile)
    await client.session.close()

async def check_comments():
    global STRIKED_USERS
    global subclient
    COMMENTS_WARNS = []
    COMMENT_ANTI_SPAM = {}
    bloglist = await subclient.get_recent_blogs(size=9999)
    for x in bloglist.json:
        author = x['author']['nickname']
        author_uid = x['author']['uid']
        title = x['title']
        content = x['content']
        blog_created = str(x['createdTime'])
        comments = await subclient.get_blog_comments(blogId=x['blogId'], size=9999)
        for y in comments.json:
            comment_author = y['author']['nickname']
            comment_author_uid = y['author']['uid']
            comment_created = str(y['createdTime'])
            comment_text = y['content']
            if COMMENT_ANTI_SPAM.get(comment_author_uid) is None: # спам 
                COMMENT_ANTI_SPAM[comment_author_uid] = str(comment_created)
            elif (dateutil.parser.isoparse(comment_created) - dateutil.parser.isoparse(COMMENT_ANTI_SPAM[comment_author_uid])).total_seconds() <= 60:
                if COMMENTS_WARNS.count(comment_author_uid) >= 4:
                    print("set read only for comment: " + comment_author + "\n")
                    if STRIKED_USERS.count(author_uid) < 1:
                        print("striking: ", author_uid)
                        # await subclient.strike(userId=author_uid, time=1, reason="Spam blog comments")
                        STRIKED_USERS.append(author_uid)
                    for i in COMMENTS_WARNS:
                        if i == comment_author_uid:
                            COMMENTS_WARNS.remove(comment_author_uid)
                else:
                    COMMENTS_WARNS.append(comment_author_uid)
            elif dateutil.parser.isoparse(comment_created) - dateutil.parser.isoparse(COMMENT_ANTI_SPAM[comment_author_uid]) > 60:
                COMMENT_ANTI_SPAM[comment_author_uid] = comment_created
                for i in COMMENTS_WARNS:
                    if i == comment_author_uid:
                        COMMENTS_WARNS.remove(comment_author_uid)

async def check_blog():
    global STRIKED_USERS
    global subclient
    BLOG_WARNS = []
    BLOGS_ANTI_SPAM = {}
    
    bloglist = await subclient.get_recent_blogs(size=9999)
    for x in bloglist.json:
        author = x['author']['nickname']
        author_uid = x['author']['uid']
        title = x['title']
        content = x['content']
        blog_created = str(x['createdTime'])
        if BLOGS_ANTI_SPAM.get(author_uid) is None: # спам 
            BLOGS_ANTI_SPAM[author_uid] = str(blog_created)
        elif (dateutil.parser.isoparse(BLOGS_ANTI_SPAM[author_uid]) - dateutil.parser.isoparse(blog_created)).total_seconds() <= 60:
            if BLOG_WARNS.count(author_uid) >= 1:
                print("set read only for posts: " + author + "\n")
                if STRIKED_USERS.count(author_uid) < 1:
                    print("striking: ", author_uid, author)
                    # await subclient.strike(userId=author_uid, time=1, reason="Spam blog posts")
                    STRIKED_USERS.append(author_uid)
                # await subclient.delete_blog()
                for i in BLOG_WARNS:
                    if i == author_uid:
                        BLOG_WARNS.remove(author_uid)
            else:
                BLOG_WARNS.append(author_uid)
        elif (dateutil.parser.isoparse(BLOGS_ANTI_SPAM[author_uid]) - dateutil.parser.isoparse(blog_created)).total_seconds() > 60:
            BLOGS_ANTI_SPAM[author_uid] = blog_created
            for i in BLOG_WARNS:
                if i == author_uid:
                    BLOG_WARNS.remove(author_uid)

async def taskB():
    while True:
        await asyncio.sleep(60)
        await check_blog()
        await check_comments()

async def main():
    taska = loop.create_task(taskA())
    taskb = loop.create_task(taskB())
    await asyncio.wait([taska,taskb])

# @client.event("on_chat_invite")
# async def on_chat_invite(data):
#     print("invite: ", data.json)
        
@client.event("on_text_message")
@client.event("on_image_message")
@client.event("on_youtube_message")# @client.event("on_strike_message")
@client.event("on_voice_message")
@client.event("on_sticker_message")
async def on_text_message(data):
    subclient = amino.AsyncSubClient(comId=COMID, profile=client.profile)
#
#STRINGS
#
    comid = data.comId
    chatid = data.message.chatId
    nickname = data.message.author.nickname
    strcontent = str(data.message.content)
    content = str(data.message.content).split()
    mtype = data.message.type
    mediatype = data.message.mediaType # 103 = video # 113 = smile # 110 = voicemessage
    mid = data.message.messageId
    uid = data.message.author.userId

    print(f"{nickname}: {strcontent}")

    check = lambda s: all('a' <= x <= 'z' or 'а' <= x <= 'я' or '0' <= x <= '9' or x == "'" or x == '`' or x == "." or x == "~" or x == "!" 
                        or x == "@" or x == "#" or x == "$" or x == "%" or x == "^" or x == "&" or x == "*" or x == "(" or x == ")" 
                        or x == "-" or x == "_" or x == "=" or x == "+" or x == "," or x == "/" or x == "<" or x == ">" 
                        or x == "?" or x == "\\" or x == "|" for x in s.lower().replace(" ",""))
    
#
#обрабатывает сообщения только в определенном соо и игнорит от самого бота
#   
    if (str(comid) != COMID or uid == USERID):
        return
#
#DEBUG
# 
# print(str(data.json))
#
# NOT LATIN AND KYRILLIC
#
    if strcontent is not None and mediatype != 103 and mediatype != 113 and mediatype != 113 and not check(str(strcontent)):
        await subclient.delete_message(chatId=chatid, messageId=mid)
#
#ANTIRAID
#
    user_id = data.message.author.userId
    if user_id != client.userId:
        msg_type = data.message.type
        if msg_type != 0:
            media_type = data.message.mediaType
            content = data.message.content
            if content is not None and media_type == 0:
                await subclient.kick(chatId=data.message.chatId, userId=user_id, allowRejoin=False)
                await subclient.send_message(chatId=chatid, message=f"{user_id} удален из чата за отправку системного сообщения")
        lock.acquire()
        if ANTI_SPAM.get(user_id) is None: # спам сообщениями с текстом
            ANTI_SPAM[user_id] = int(time.time())
        elif int(time.time()) - ANTI_SPAM[user_id] <= 0.5:
            if WARNS.count(user_id) >= 4:
                await subclient.kick(userId=user_id, chatId=data.message.chatId, allowRejoin=False)
                await subclient.send_message(chatId=chatid, message=f"{user_id} удален из чата за спам")
                for i in WARNS:
                    if i == user_id:
                        WARNS.remove(user_id)
            else:
                WARNS.append(user_id)
        elif int(time.time()) - ANTI_SPAM[user_id] > 1:
            ANTI_SPAM[user_id] = int(time.time())
            for i in WARNS:
                if i == user_id:
                    WARNS.remove(user_id)
        lock.release()
#
#HEY
#
    if content is not None and content[0] == "?hey":
        try:
            await subclient.send_message(chatId=chatid, message="work status: True")
        except:
            pass
#
#Join
#
    # if content[0][0] == '!':
    #     if content[0][1:].lower() == "join":
    #         if any(user in uid for user in whitelist):
    #             try:
    #                 print(content[-1])
    #                 id = client.get_from_code(content[-1]).objectId
    #                 subclient.join_chat(id)
    #                 subclient.send_message(chatId = chatid, message="Joined")
    #             except:
    #                 subclient.send_message(chatId = chatid, message="Error")
    #         else:
    #             subclient.send_message(chatId = chatid, message="You don't have permissions")

@client.event("on_group_member_join") # спам с перезаходами
@client.event("on_group_member_leave")
async def on_join_leave(data):
    #
    #DEBUG
    # 
    # print(str(data.json))
    chatid = data.message.chatId
    subclient = amino.AsyncSubClient(comId=COMID, profile=client.profile)
    user_id = data.message.author.userId
    text_to_print = "Joined chat"
    if (data.message.type==102):
        user_id = data.json['chatMessage']['uid']
        text_to_print = "Left chat"
    # print(f"{data.message.author.nickname}: {text_to_print}")
    # print(f"debug: {chatid}: {user_id}\n{data.message.chatId}")
    if user_id != client.userId:
        lock.acquire()
        if JOIN_LEAVE_DETECTOR.get(user_id) is None:
            JOIN_LEAVE_DETECTOR[user_id] = int(time.time())
        elif int(time.time()) - JOIN_LEAVE_DETECTOR[user_id] <= 1:
            lel = subclient.get_all_users()
            await subclient.kick(userId=user_id, chatId=chatid, allowRejoin=False)
            await subclient.send_message(chatId=chatid, message=f"{user_id} удален из чата за спам входом/выходом из чата")
            JOIN_LEAVE_DETECTOR[user_id] = None
        elif int(time.time()) - JOIN_LEAVE_DETECTOR[user_id] > 1:
            JOIN_LEAVE_DETECTOR[user_id] = int(time.time())
        lock.release()

loop = asyncio.get_event_loop()

try:
    t1 = loop.create_task(main())
    loop.run_until_complete(t1)
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    print("Closing Loop")
    loop.close()