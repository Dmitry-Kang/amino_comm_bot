from datetime import datetime
import amino
import re
import traceback
import sys
import os
from decouple import config
import time
import asyncio
import dateutil.parser
import pretty_errors
import db as database
import commands, amino_commands

# Импорт конфигов
DEV = True # False - прод
DEBUG = False # False - включены баны и кики
POSTS = False # True - включены проверки постов и комментов
BOT_CHAT_ID = "set your chat id"

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

async def taskA():
    global client
    global USERID
    print("Try login via", EMAIL, PASSWORD)
    try:
        await client.login(email=EMAIL, password=PASSWORD)
        print("login success")
        USERID = client.userId
        subclient = amino.AsyncSubClient(comId=COMID, profile=client.profile)
        await client.session.close()
    except Exception:
        print(f"Exception in taskA: {traceback.format_exc()}")
    finally:
        return

async def check_comments():
    global DEBUG
    COMMENTS_WARNS = []
    COMMENT_ANTI_SPAM = {}
    try:
        subclient = amino.AsyncSubClient(comId=COMID, profile=client.profile)
        bloglist = await subclient.get_recent_blogs(size=9999)
        for x in bloglist.json:
            author = x['author']['nickname']
            author_uid = x['author']['uid']
            title = x['title']
            blogId = x['blogId']
            content = x['content']
            blog_created = str(x['createdTime'])
            comments = await subclient.get_blog_comments(blogId=x['blogId'], size=9999)
            for y in comments.json:
                comment_author = y['author']['nickname']
                comment_author_uid = y['author']['uid']
                commentId = y['commentId']
                comment_created = str(y['createdTime'])
                comment_text = y['content']
                if COMMENT_ANTI_SPAM.get(comment_author_uid) is None: # спам 
                    COMMENT_ANTI_SPAM[comment_author_uid] = str(comment_created)
                elif (dateutil.parser.isoparse(comment_created) - dateutil.parser.isoparse(COMMENT_ANTI_SPAM[comment_author_uid])).total_seconds() <= 30:
                    if COMMENTS_WARNS.count(comment_author_uid) > 3:
                        print(f"Deleting comment: {commentId}")
                        if not DEBUG:
                            try:
                                await subclient.delete_comment(commentId=commentId,blogId=blogId)
                            except Exception:
                                print(f"Exception when deleting blog comment {author_uid}: {traceback.format_exc()}")
                        striked_users = database.get_striked_users(author_uid)
                        if not commands.contains(striked_users, lambda x: x['userid'] == author_uid):
                            print("striking for comment: ", author_uid)
                            if not DEBUG:
                                try:
                                    await subclient.strike(userId=author_uid, time=5, reason="Spam blog comments")
                                except Exception:
                                    print(f"Exception when striking for comments {author_uid}: {traceback.format_exc()}")
                            database.add_striked_users(author_uid, int((datetime.now()-datetime(1970,1,1)).total_seconds()) + 60 * 60 * 24)
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
    except Exception:
        print(f"Exception in check_comments: {traceback.format_exc()}")
    finally:
        try:
            await subclient.session.close()
        except:
            print(f"Exception in check_comments: {traceback.format_exc()}")
        return

async def check_blog():
    global DEBUG
    BLOG_WARNS = []
    BLOGS_ANTI_SPAM = {}
    try:
        subclient = amino.AsyncSubClient(comId=COMID, profile=client.profile)
        bloglist = await subclient.get_recent_blogs(size=9999)
        for x in bloglist.json:
            author = x['author']['nickname']
            author_uid = x['author']['uid']
            blogId = x['blogId']
            title = x['title']
            content = x['content']
            blog_created = str(x['createdTime'])
            if BLOGS_ANTI_SPAM.get(author_uid) is None: # спам 
                BLOGS_ANTI_SPAM[author_uid] = str(blog_created)
            elif (dateutil.parser.isoparse(BLOGS_ANTI_SPAM[author_uid]) - dateutil.parser.isoparse(blog_created)).total_seconds() <= 30:
                if BLOG_WARNS.count(author_uid) > 3:
                    print(f"Deleting blog: {blogId}")
                    if not DEBUG:
                        try:
                            await subclient.delete_blog(blogId=blogId)
                        except Exception:
                            print(f"Exception when deleting blog {author_uid}: {traceback.format_exc()}")
                    striked_users = database.get_striked_users(author_uid)
                    if not commands.contains(striked_users, lambda x: x['userid'] == author_uid):
                        print("striking for blog: ", author_uid, author)
                        if not DEBUG:
                            try:
                                await subclient.strike(userId=author_uid, time=5, reason="Spam blog posts")
                            except Exception:
                                print(f"Exception when striking for post {author_uid}: {traceback.format_exc()}")
                        database.add_striked_users(author_uid, int((datetime.now()-datetime(1970,1,1)).total_seconds()) + 60 * 60 * 24)
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
    except Exception:
        print(f"Exception in check_blog: {traceback.format_exc()}")
    finally:
        try:
            await subclient.session.close()
        except:
            print(f"Exception in check_blog: {traceback.format_exc()}")
        return

async def taskB():
    global POSTS
    while True:
        await asyncio.sleep(60)
        if (POSTS):
            await check_blog()
            await check_comments()

async def task_check_striked_users():
    while True:
        try:
            await asyncio.sleep(60)
            striked_users = database.get_striked_users()
            print("Checking striked users:")
            for user in striked_users:
                date = datetime.fromtimestamp(int(user["date"]))
                if (date - datetime.now()).total_seconds() < 0:
                    print(f"Removing from strikes user {user['userid']}")
                    database.delete_striked_users(user["userid"])
        except Exception:
            print(f"Exception in task_check_striked_users: {traceback.format_exc()}")
        finally:
            return  
def get_anti_ban(s):
    if not s or len(s) < 1:
        print("1")
        return False
    if s.find('_(.a=') > -1:
        return True
    print("2")
    return False
def get_percent(s):
    if not s or len(s) < 1:
        return 1.0
    s = s.lower().replace(" ","")
    leng = len(s)
    len_true = 0
    for x in s:
        if ('a' <= x <= 'z' or 'а' <= x <= 'я' or '0' <= x <= '9' or x == "'" or x == '`' or x == "." or x == "~" or x == "!" 
                    or x == "@" or x == "#" or x == "$" or x == "%" or x == "^" or x == "&" or x == "*" or x == "(" or x == ")" 
                    or x == "-" or x == "_" or x == "=" or x == "+" or x == "," or x == "/" or x == "<" or x == ">" 
                    or x == "?" or x == "\\" or x == "|" or x == ":" or x == ";" or x == '"' or x == "[" or x == "]" or x == "{" or x == "}" or x == "ё"):
            len_true += 1
    return len_true/leng

async def task_check_antiban():
    try:
        res = ""
        subclient = await amino.AsyncSubClient(comId=COMID, profile=client.profile)
        all_users = await subclient.get_all_users("recent", 0, 99999)
        for user in all_users.json['userProfileList']:
            user_uid = user['uid']
            user_name = user['nickname']
            user_content = user['content']
            if get_percent(user_content) < 0.05 or get_anti_ban(user_content):
                # res += f"\u200e\u200f@{user_name}\u202c\u202d:{get_percent(user_content)}:{get_anti_ban(user_content)}\n"
                res += f"\u200e\u200f@{user_name}\u202c\u202d\n"
    except Exception:
            print(f"Exception in task_check_antiban: {traceback.format_exc()}")
    finally:
        try:
            await subclient.session.close()
        except:
            print(f"Exception in task_check_antiban: {traceback.format_exc()}")
        if len(res) == 0:
            res = "Не обнаружено"
        return f"Подозрительные персоны:\n{res}"  

async def main():
    while True:
        try:
            taska = loop.create_task(taskA())
            taskb = loop.create_task(taskB())
            taskc = loop.create_task(task_check_striked_users())
            # taskd = loop.create_task(task_check_antiban())
            await asyncio.wait([taska,taskb,taskc])
        except:
            print(f"Exception in main: {traceback.format_exc()}")
    

# @client.event("on_chat_invite")
# async def on_chat_invite(data):
#     print("invite: ", data.json)
        
@client.event("on_text_message")
@client.event("on_image_message")
@client.event("on_youtube_message")
@client.event("on_voice_message")
@client.event("on_sticker_message")
async def on_text_message(data):
    global DEBUG
    try:
        #
        #STRINGS
        #
        subclient = amino.AsyncSubClient(comId=COMID, profile=client.profile)
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

        def clear_mentions(text):
            res = re.findall("\\u200e\\u200f@[^\u202c\\u202d]*\\u202c\\u202d", text)
            while (len(res) > 0):
                text = text.replace(res[0], "")
                res = re.findall("\\u200e\\u200f@[^\u202c\\u202d]*\\u202c\\u202d", text)
            return text

        def check(s):
            # s = s.lower().replace(" ","").replace("\u200e", "").replace("\u200f", "").replace("\u202c", "").replace("\u202d", "")
            s = s.lower().replace(" ","")
            s = clear_mentions(s)
            # mentions = осталось только игнорить упоминания
            ret = all('a' <= x <= 'z' or 'а' <= x <= 'я' or '0' <= x <= '9' or x == "'" or x == '`' or x == "." or x == "~" or x == "!" 
                            or x == "@" or x == "#" or x == "$" or x == "%" or x == "^" or x == "&" or x == "*" or x == "(" or x == ")" 
                            or x == "-" or x == "_" or x == "=" or x == "+" or x == "," or x == "/" or x == "<" or x == ">" 
                            or x == "?" or x == "\\" or x == "|" or x == ":" or x == ";" or x == '"' or x == "[" or x == "]" or x == "{" or x == "}" or x == "ё" for x in s)
            return ret
        
        #
        #обрабатывает сообщения только в определенном соо 
        #
        if (str(comid) != COMID): # or uid == USERID и игнорит от самого бота
            return
        print(f"{str(chatid)} {uid} {nickname}: {strcontent}")
        # print(f"{str(data.json)}")

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
                    await subclient.strike(userId=reply_uid, time=int(content[1]))
                    if content[1] == "1":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {1} час")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"Пользователь отправился в мут на {1} час")
                    elif content[1] == "2":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {3} часа")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"Пользователь отправился в мут на {3} часа")
                    elif content[1] == "3":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {6} часов")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"Пользователь отправился в мут на {6} часов")
                    elif content[1] == "4":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {12} часов")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"Пользователь отправился в мут на {12} часов")
                    elif content[1] == "5":
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в мут на {24} часа")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"Пользователь отправился в мут на {24} часа")
                    return
            #
            # BAN
            #
            if content[0] == "ban" and message_json["chatMessage"]["extensions"]["replyMessageId"] is not None:
                    reply_message = await subclient.get_message_info(chatId=chatid, messageId=message_json["chatMessage"]["extensions"]["replyMessageId"])
                    reply_uid = reply_message.json["uid"]
                    reply_user = subclient.get_user_info(reply_uid)
                    user_name = reply_user['nickname']
                    print("ban user {}".format(str(reply_uid)))
                    try:
                        await subclient.ban(userId=reply_uid, reason="Ты нарушил правила")
                        await subclient.send_message(chatId=chatid, message=f"Пользователь отправился в бан")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"Пользователь{user_name} отправился в бан")
                    except:
                        print(f"Exception in ban command: {traceback.format_exc()}")
                  
            #
            # HEY
            #
            if content is not None and content[0] == "?ping":
                try:
                    await subclient.send_message(chatId=chatid, message="pong")
                except:
                    print(f"Exception in ping pong: {traceback.format_exc()}")
                return
            #
            # STRANGE USERS
            #
            if content is not None and content[0] == "get" and content[1] == "antiban":
                try:
                    msg = await task_check_antiban()
                    await subclient.send_message(chatId=chatid, message=msg)
                except:
                    print(f"Exception in STRANGE USERS: {traceback.format_exc()}")
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
        # if strcontent is not None and mediatype == 0 and not check(str(strcontent)):
        #     print(f"{chatid} deleting message {strcontent} {mid}")
        #     if not DEBUG:
        #         await subclient.delete_message(chatId=chatid, messageId=mid)
            
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
                    if not DEBUG:
                        await subclient.kick(chatId=data.message.chatId, userId=user_id, allowRejoin=False)
                        await subclient.send_message(chatId=chatid, message=f"{nickname} удален из чата за отправку системного сообщения")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"{nickname} удален из чата за отправку системного сообщения")
                    database.add_kicked_users(user_id)
            if not commands.contains(database.get_anti_spam(user_id), lambda x: x['userid'] == user_id): # спам сообщениями с текстом
                database.add_anti_spam(user_id, int(time.time()))
            elif int(time.time()) - int(database.get_anti_spam(user_id)[0]['date']) <= 0.5:
                anti_spam_warns = database.get_anti_spam_warns()
                if anti_spam_warns.count(user_id) >= 4:
                    database.add_kicked_users(user_id)
                    print(f"{user_id} удален из чата за спам")
                    if not DEBUG:
                        await subclient.kick(userId=user_id, chatId=data.message.chatId, allowRejoin=False)
                        await subclient.send_message(chatId=chatid, message=f"{nickname} удален из чата за спам")
                        await subclient.send_message(chatId=BOT_CHAT_ID, message=f"{nickname} удален из чата за спам")
                    database.add_kicked_users(user_id)
                    database.delete_anti_spam_warns(user_id)
                else:
                    database.add_anti_spam_warns(user_id)
            elif int(time.time()) - int(database.get_anti_spam(user_id)[0]['date']) > 1:
                database.update_anti_spam(user_id, int(time.time()))
                database.delete_anti_spam_warns(user_id)
    except Exception:
        print(f"Exception in on_text_message: {traceback.format_exc()}")
    finally:
        try:
            await subclient.session.close()
        except:
            print(f"Exception in on_text_message: {traceback.format_exc()}")
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
        nickname = data.message.author.nickname
        text_to_print = "Joined chat"
        if (data.message.type==102):
            user_id = data.json['chatMessage']['uid']
            text_to_print = "Left chat"
        print(f"{data.message.author.nickname}: {text_to_print} {chatid}")
        # print(f"debug: {chatid}: {user_id}\n{data.message.chatId}")
        if user_id != client.userId:
            if not commands.contains(database.get_join_leave_spam(user_id), lambda x: x['userid'] == user_id):
                database.add_join_leave_spam(user_id, int(time.time()))
            elif int(time.time()) - int(database.get_join_leave_spam(user_id)[0]['date']) <= 0.5:
                lel = await subclient.get_all_users()
                database.add_kicked_users(user_id)
                print(f"{user_id} удален из чата за отправку системного сообщения")
                if not DEBUG:
                    await subclient.kick(userId=user_id, chatId=chatid, allowRejoin=False)
                    await subclient.send_message(chatId=chatid, message=f"{nickname} удален из чата за спам входом/выходом из чата")
                    await subclient.send_message(chatId=BOT_CHAT_ID, message=f"{nickname} удален из чата за спам входом/выходом из чата")
                database.add_kicked_users(user_id)
                database.delete_join_leave_spam(user_id)
            elif int(time.time()) - int(database.get_join_leave_spam(user_id)[0]['date']) > 0.5:
                database.update_join_leave_spam(user_id, int(time.time()))
    except Exception:
        print(f"Exception in on_join_leave: {traceback.format_exc()}")
    finally:
        try:
            await subclient.session.close()
        except:
            print(f"Exception in on_join_leave: {traceback.format_exc()}")
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