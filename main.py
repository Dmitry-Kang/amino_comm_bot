from datetime import datetime
import amino
import os
from decouple import config
import time
import asyncio
import dateutil.parser
import pretty_errors
import db as database
import commands, amino_commands

# Импорт конфигов
DEV = False # True = разработка, False = прод
EMAIL=os.environ.get('EMAIL') # админ сообщества И(!) ведущий в чатах
PASSWORD=os.environ.get('PASSWORD')
COMID=os.environ.get('COMMUNITY_ID') # id сообщества
USERID=None # ставится автоматом
if DEV:
    EMAIL=config('EMAIL')
    PASSWORD=config('PASSWORD')
    COMID=config('COMMUNITY_ID')

# Таблицы
# whitelist - пользователи которых антирейд игнорит
# anti_spam - время отправленного последниего сообщения/текста/картинки и тд
# anti_spam_warns - количество нарушений спамом (счетчик)
# join_leave_spam - время последниего выхода - захода

# striked_users - таблица с юзерами на которых висит страйк и до какого момента
# kicked_users - таблица с юзерами которых кикнули


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
    try:
        print("login")
        await client.login(email=EMAIL, password=PASSWORD)
        USERID = client.userId
        subclient = await amino.AsyncSubClient(comId=COMID, profile=client.profile)
        await client.session.close()
    except Exception as e:
        print(f"Exception: {str(e)}")
    finally:
        return

async def check_comments():
    global subclient
    COMMENTS_WARNS = []
    COMMENT_ANTI_SPAM = {}
    try:
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
                elif (dateutil.parser.isoparse(comment_created) - dateutil.parser.isoparse(COMMENT_ANTI_SPAM[comment_author_uid])).total_seconds() <= 30:
                    if COMMENTS_WARNS.count(comment_author_uid) >= 4:
                        # striked_users = database.get_striked_users(author_uid)
                        # if not commands.contains(striked_users, lambda x: x['userid'] == author_uid):
                        print("striking for comment: ", author_uid)
                        # await subclient.strike(userId=author_uid, time=5, reason="Spam blog comments")
                        # database.add_striked_users(author_uid, 0)
                        for i in COMMENTS_WARNS:
                            if i == comment_author_uid:
                                COMMENTS_WARNS.remove(comment_author_uid)
                    else:
                        COMMENTS_WARNS.append(comment_author_uid)
                elif (dateutil.parser.isoparse(comment_created) - dateutil.parser.isoparse(COMMENT_ANTI_SPAM[comment_author_uid])).total_seconds() > 30:
                    COMMENT_ANTI_SPAM[comment_author_uid] = comment_created
                    for i in COMMENTS_WARNS:
                        if i == comment_author_uid:
                            COMMENTS_WARNS.remove(comment_author_uid)
    except Exception as e:
        print(f"Exception: {str(e)}")
    finally:
        return

async def check_blog():
    global subclient
    BLOG_WARNS = []
    BLOGS_ANTI_SPAM = {}
    
    try:
        bloglist = await subclient.get_recent_blogs(size=9999)
        for x in bloglist.json:
            author = x['author']['nickname']
            author_uid = x['author']['uid']
            title = x['title']
            content = x['content']
            blog_created = str(x['createdTime'])
            if BLOGS_ANTI_SPAM.get(author_uid) is None: # спам 
                BLOGS_ANTI_SPAM[author_uid] = str(blog_created)
            elif (dateutil.parser.isoparse(BLOGS_ANTI_SPAM[author_uid]) - dateutil.parser.isoparse(blog_created)).total_seconds() <= 30:
                if BLOG_WARNS.count(author_uid) >= 1:
                    # print("set read only for posts: " + author + "\n")
                    # striked_users = database.get_striked_users(author_uid)
                    # if not commands.contains(striked_users, lambda x: x['userid'] == author_uid):
                    print("striking for blog: ", author_uid, author)
                    # await subclient.strike(userId=author_uid, time=5, reason="Spam blog posts")
                    # database.add_striked_users(author_uid, 0)
                    # await subclient.delete_blog()
                    for i in BLOG_WARNS:
                        if i == author_uid:
                            BLOG_WARNS.remove(author_uid)
                else:
                    BLOG_WARNS.append(author_uid)
            elif (dateutil.parser.isoparse(BLOGS_ANTI_SPAM[author_uid]) - dateutil.parser.isoparse(blog_created)).total_seconds() > 30:
                BLOGS_ANTI_SPAM[author_uid] = blog_created
                for i in BLOG_WARNS:
                    if i == author_uid:
                        BLOG_WARNS.remove(author_uid)
    except Exception as e:
        print(f"Exception: {str(e)}")
    finally:
        return

async def taskB():
    while True:
        await asyncio.sleep(60)
        await check_blog()
        await check_comments()

# async def task_check_striked_users():
#     while True:
#         await asyncio.sleep(5)
        
#         striked_users = database.get_striked_users()
#         print("checking striked users\n", str(striked_users))
#         for user in striked_users:
#             if (user["date"] != "0"):
#                 print("11", user)
#                 await asyncio.sleep(5)
#                 date = datetime.fromtimestamp(int(user["date"]))
#                 if (date - datetime.now() < 0):
#                     print(f"Removing from strike {user['date']}")
#                     database.delete_striked_users(user["userid"])


async def main():
    taska = loop.create_task(taskA())
    taskb = loop.create_task(taskB())
    # taskc = loop.create_task(task_check_striked_users())
    await asyncio.wait([taska,taskb])

# @client.event("on_chat_invite")
# async def on_chat_invite(data):
#     print("invite: ", data.json)
        
@client.event("on_text_message")
@client.event("on_image_message")
@client.event("on_youtube_message")
@client.event("on_voice_message")
@client.event("on_sticker_message")
async def on_text_message(data):
    global subclient
    #
    #STRINGS
    #
    try:
        comid = data.comId
        chatid = data.message.chatId
        nickname = data.message.author.nickname
        strcontent = str(data.message.content)
        content = strcontent.lower().split()
        mtype = data.message.type
        mediatype = data.message.mediaType # 0 = text; 100 = image; 103 = video; 110 = voicemessage; 113 = smile
        mid = data.message.messageId
        uid = data.message.author.userId
        message_json = data.json
        whitelist = database.get_whitelist()

        def check(s):
            s = s.lower().replace(" ","").replace("\u200e", "").replace("\u200f", "").replace("\u202c", "").replace("\u202d", "")
            ret = all('a' <= x <= 'z' or 'а' <= x <= 'я' or '0' <= x <= '9' or x == "'" or x == '`' or x == "." or x == "~" or x == "!" 
                            or x == "@" or x == "#" or x == "$" or x == "%" or x == "^" or x == "&" or x == "*" or x == "(" or x == ")" 
                            or x == "-" or x == "_" or x == "=" or x == "+" or x == "," or x == "/" or x == "<" or x == ">" 
                            or x == "?" or x == "\\" or x == "|" for x in s)
            return ret
        
        #
        #обрабатывает сообщения только в определенном соо 
        #   
        print(f"{str(chatid)} {nickname}: {strcontent}")
        # print(f"{str(data.json)}")
        if (str(comid) != COMID): # or uid == USERID и игнорит от самого бота
            return

        if whitelist.count(uid) > 0: # Админка
            #
            # MUTE
            #
            if content[0] == "mute" and message_json["chatMessage"]["extensions"]["replyMessageId"] is not None:
                if (len(content) > 1 and (content[1] == "1" or content[1] == "2" or content[1] == "3" or content[1] == "4" or content[1] == "5")):
                    reply_message = await subclient.get_message_info(chatId=chatid, messageId=message_json["chatMessage"]["extensions"]["replyMessageId"])
                    reply_uid = reply_message.json["uid"]
                    # reply_user = subclient.get_user_info(reply_uid)
                    # newdate = (datetime.now() - datetime(1970,1,1)).total_seconds() + 60 * int(content[1])
                    print("muting user {} for {} minutes".format(str(reply_uid), content[1]))
                    # await subclient.strike(userId=reply_uid, time=content[1])
                    if content[1] == "1":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {1} час")
                    elif content[1] == "2":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {3} часа")
                    elif content[1] == "3":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {6} часов")
                    elif content[1] == "4":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {12} часов")
                    elif content[1] == "5":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {24} часа")
                    return
            #
            # HEY
            #
            if content is not None and content[0] == "?hey":
                try:
                    await subclient.send_message(chatId=chatid, message="work status: True")
                except:
                    pass
                return
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
            return

        #
        # NOT LATIN AND KYRILLIC
        #
        if strcontent is not None and mediatype == 0 and not check(str(strcontent)):
            print(f"{chatid} deleting message {strcontent} {mid}")
            # await subclient.delete_message(chatId=chatid, messageId=mid)
            
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
                    database.add_kicked_users(user_id)
                    print(f"{user_id} удален из чата за отправку системного сообщения")
                    # await subclient.kick(chatId=data.message.chatId, userId=user_id, allowRejoin=False)
                    # await subclient.send_message(chatId=chatid, message=f"{user_id} удален из чата за отправку системного сообщения")
            if not commands.contains(database.get_anti_spam(user_id), lambda x: x['userid'] == user_id): # спам сообщениями с текстом
                database.add_anti_spam(user_id, int(time.time()))
            elif int(time.time()) - int(database.get_anti_spam(user_id)[0]['date']) <= 0.5:
                anti_spam_warns = database.get_anti_spam_warns()
                if anti_spam_warns.count(user_id) >= 4:
                    database.add_kicked_users(user_id)
                    print(f"{user_id} удален из чата за отправку системного сообщения")
                    # await subclient.kick(userId=user_id, chatId=data.message.chatId, allowRejoin=False)
                    # await subclient.send_message(chatId=chatid, message=f"{user_id} удален из чата за спам")
                    database.delete_anti_spam_warns(user_id)
                else:
                    database.add_anti_spam_warns(user_id)
            elif int(time.time()) - int(database.get_anti_spam(user_id)[0]['date']) > 1:
                database.update_anti_spam(user_id, int(time.time()))
                database.delete_anti_spam_warns(user_id)
    except Exception as e:
        print(f"Exception: {str(e)}")
    finally:
        return    

@client.event("on_group_member_join") # спам с перезаходами
@client.event("on_group_member_leave")
async def on_join_leave(data):
    try:
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
            if not commands.contains(database.get_join_leave_spam(user_id), lambda x: x['userid'] == user_id):
                database.add_join_leave_spam(user_id, int(time.time()))
            elif int(time.time()) - int(database.get_join_leave_spam(user_id)[0]['date']) <= 0.5:
                lel = subclient.get_all_users()
                database.add_kicked_users(user_id)
                print(f"{user_id} удален из чата за отправку системного сообщения")
                # await subclient.kick(userId=user_id, chatId=chatid, allowRejoin=False)
                # await subclient.send_message(chatId=chatid, message=f"{user_id} удален из чата за спам входом/выходом из чата")
                database.delete_join_leave_spam(user_id)
            elif int(time.time()) - int(database.get_join_leave_spam(user_id)[0]['date']) > 0.5:
                database.update_join_leave_spam(user_id, int(time.time()))
    except Exception as e:
        print(f"Exception: {str(e)}")
    finally:
        return

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