from random import randrange
import requests
import json
from pprint import pprint

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from tokens import TOKEN, APP_ID, AUTH_REDIRECT_URI, USER_TOKEN
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from requests.exceptions import ReadTimeout as requests_exceptions_ReadTimeout

from vk_api.exceptions import ApiError

from time import sleep as time_sleep

from State import State

from vk_auth import (
    vk_auth_link,
    generate_code_verifier as vk_auth_generate_code_verifier,
    gen_state,
    vk_refresh,
)

from User import User
from DB.profiles import (
    db_add_profiles,
    db_count_filter_profiles,
    db_count_filter_profiles_blacklisted,
    db_count_filter_profiles_viewed,
    db_get_profile,
    db_profile_set_viewed,
    db_profile_clean_viewed,
    db_profile_set_blacklisted,
    db_profile_clean_bl,
    db_profile_del,
    db_profile_to_fav,
    db_count_filter_fav,
    db_count_fav_total,
    db_get_fav,
)

# token = input('Token: ')
vk = vk_api.VkApi(token=TOKEN)
# longpoll = VkLongPoll(vk)
longpoll = VkLongPoll(
    vk,
    wait=1,
)
vkapi = vk.get_api()

# Создаем доп. экземпляр для запросов от имени пользователя
# user_vk = vk_api.VkApi(token=USER_TOKEN)
# vkuserapi = user_vk.get_api()
user_vk = None
vkuserapi = None


def declension(n, for_1, for_234, for_other):
    d = n % 10

    if d == 1 and n % 100 != 11:
        return for_1

    if d in [2, 3, 4] and not (n % 100 in [12, 13, 14]):
        return for_234

    return for_other


def extend_message(message, add, format_=[], type=None):
    format = format_.copy()
    res = message + add
    if type:
        format.append(
            {
                "type": type,
                "offset": len(message),
                "length": len(add),
            }
        )
    return format, res


def write_msg(user, message, keyboard=None, format=None, delete=False, attach=None):
    if isinstance(user, User):
        user_id = user.vk_id
    else:
        user_id = user
    print("write_message ", user_id)  # message)
    pars = {
        "user_id": user_id,
        "message": message,
        "random_id": randrange(10**7),
        "keyboard": keyboard,
    }
    if attach:
        pars["attachment"] = attach
    if format:
        pars["format_data"] = json.dumps({"version": "1", "items": format})
    print(pars)
    res = vk.method(
        "messages.send",
        pars,
    )
    if delete:
        print("Удалить", isinstance(user, User))
        if delete and isinstance(user, User):
            add_to_del(user, res)
            print(user.to_del)
    print(res)
    return res


def del_all(user):
    del_msg(user.to_del)
    user.to_del = ""
    user.save()


def del_msg(message_id, vk=vk):  # user_id,
    print("to_del", message_id)
    if message_id:
        try:
            return vk.method(
                "messages.delete",
                {
                    # "user_id": user_id,
                    "message_ids": message_id,
                    "delete_for_all": 1,
                },
            )
        except Exception as e:
            print(e)
            pass


import psycopg2.extras


def connect():
    conn = psycopg2.connect(database="vk_dating", user="postgres", password="postgres")
    return conn


# def db_set_state(user, state):
#     user["state"] = state
#     sql = f"""UPDATE users SET state = {state} WHERE vk_id = {user["vk_id"]};"""
#     print(sql)
#     conn = connect()
#     conn.autocommit = True
#     with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
#         cur.execute(sql)
#         print(cur.rowcount)
#         print(cur.rownumber)


# def db_update_user(user):
#     state = user["state"]
#     to_del = user["to_del"]
#     sql = f"""UPDATE users SET state = {state}, to_del = '{to_del}' WHERE vk_id = {user["vk_id"]};"""
#     print(sql)
#     conn = connect()
#     conn.autocommit = True
#     with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
#         cur.execute(sql)
#         print(cur.rowcount)
#         print(cur.rownumber)


def add_to_del(user, message_id):
    print(message_id)
    if not user.to_del:
        user.to_del = ""
    # print(user.to_del)
    # print(user.to_del.split(","))
    # print(type(user.to_del.split(",")))
    # print([] + [1])
    # print(user.to_del.split(",").append(message_id))
    # print(type(user.to_del.split(",").append(message_id)))
    # print(user.to_del.split(",") + [message_id])
    # print(type(user.to_del.split(",") + [message_id]))

    user.to_del = (
        ",".join((user.to_del.split(",") + [str(message_id)]))
        if user.to_del
        else str(message_id)
    )
    print("to_del:", user.to_del)


def format_filters_msg(user, title="Условия подбора кандидатов:\n"):
    no_value = "Не задан"
    min_age = user.filter_age_from if user.filter_age_from else no_value
    max_age = user.filter_age_to if user.filter_age_to else no_value
    gender = user.filter_gender if user.filter_gender else no_value
    return (
        title + f"\n        Минимальный возраст: {min_age}"
        f"\n        Максимальный возраст: {max_age}"
        f"\n\n        Пол: {gender}"
    )


while True:
    try:
        # for event in longpoll.listen():
        try:
            events = longpoll.check()
        except Exception as e:
            print("\n" + str(e))
            continue

        for event in events:
            print()
            print("======================================== for", event.type)
            if event.type == VkEventType.MESSAGE_NEW:
                request = event.text
                print(request)

                if event.to_me:

                    print(event.extra_values)

                    payload = json.loads(event.extra_values.get("payload", "{}"))
                    # command = json.loads(event.extra_values.get("payload", "{}")).get(
                    command = payload.get("command")
                    command_next = payload.get("next")
                    command_to_blacklist = payload.get("to_blacklist")
                    action = payload.get("action")

                    print(command)

                    uid = event.user_id
                    print("to_me", event.type)
                    request = event.text

                    # Получаем из базы инфу о пользователе. Если нету, создаем запись, если есть, обновляем запись
                    # msg_id = write_msg(uid, f"Получаем из базы инфу, {uid}")

                    user = User(uid)

                    print("is user new", user.is_new)
                    if user.is_new:
                        print("user is new")
                        user_data = vkapi.users.get(
                            user_ids=uid,
                            fields="city, sex, birth_year, bdate",
                        )[0]
                        user.birthday = user_data["bdate"]
                        print(user.birthday)
                        user.save()
                        user.__init__()
                    print(user._data)
                    # add_to_del(user, msg_id)

                    if not user.refresh_token:
                        if user.state not in State.GETTING_ACCESS_TOKEN:
                            user.state = State.NEED_ACCESS_TOKEN
                            user.save()
                        command = None
                        payload = {}
                        request = None
                    else:
                        user_vk = vk_api.VkApi(token=user.access_token)
                        vkuserapi = user_vk.get_api()

                    print(command)
                    print(command == "set_state")
                    if command == "set_state":
                        user.state = json.loads(
                            event.extra_values.get("payload", "{}")
                        ).get("state")
                        print(
                            "command: set_state",
                            json.loads(event.extra_values.get("payload", "{}")),
                        )
                        print(
                            "delete",
                            json.loads(event.extra_values.get("payload", "{}")).get(
                                "delete", False
                            ),
                        )
                        if json.loads(event.extra_values.get("payload", "{}")).get(
                            "delete", False
                        ):
                            print("delete", user.to_del)
                            del_all(user)
                            # del_msg(user.to_del)
                            user.to_del = ""
                        user.save()
                    elif command == "auth_continue":
                        # db_set_state(user, State.SHOW_FILTERS)
                        # print("request")
                        # import requests

                        # url = "https://my.tuna.am/v1/webhooks"

                        # headers = {
                        #     "accept": "application/json",
                        #     # "Authorization": "tt_usf4j3b4ytsmp3ivn5lglpd72v05965v",
                        #     "Authorization": "tt_usf4j3b4ytsmp3ivn5lglpd72v05965v",
                        # }
                        # response = requests.get(url, headers=headers)

                        # print("Status:", response.status_code)
                        # print("Response JSON:")
                        # print(response.json())
                        # print(r.status_code)
                        # print(r.json())  # если ответ JSON
                        # print("end request")
                        # print(r.headers)
                        # print(r.request)
                        if not user.refresh_token:
                            user.state = State.NEED_ACCESS_TOKEN
                            user.save()
                        pass

                    elif command == "filter_finish":
                        user.state, State.FILTERS_FINISH
                        user.save()
                    elif command == "main":
                        user.state = State.SHOW
                        user.save()

                    # if user["to_del"]:
                    #     del_msg(user["to_del"])

                    # del_msg(event.message_id)
                    print(event.extra_values)
                    while True:
                        # Цикл выполняется пока не нужен ввод пользователя
                        print("цикл состояний", user.state)
                        if user.state == State.NEED_ACCESS_TOKEN:
                            del_all(user)
                            kb = VkKeyboard(inline=True)
                            kb.add_openlink_button(
                                "Разрешить доступ",
                                vk_auth_link(
                                    APP_ID,
                                    AUTH_REDIRECT_URI,
                                    code_verifier=user.code_verifier,
                                ),
                            )
                            kb.add_button(
                                "Продолжить",
                                color=VkKeyboardColor.POSITIVE,
                                payload={"command": "auth_continue"},
                            )
                            write_msg(
                                user,
                                "Для поиска анкет в контакте нажмите на кнопку чтобы разрешить доступ",
                                keyboard=kb.get_keyboard(),
                                delete=True,
                            )
                            user.state = State.WAIT_ACCESS_TOKEN
                            user.save()
                            break
                        # write_msg(user, f"Состояние диалога: {user.state}", delete=True)
                        if user.state == State.WAIT_ACCESS_TOKEN:
                            if not user.refresh_token:
                                user.state = State.NEED_ACCESS_TOKEN
                                user.save()
                                print("check token", user.state)
                            else:
                                # Создаем доп. экземпляр для запросов от имени пользователя
                                # user_vk = vk_api.VkApi(token=user.access_token)
                                # vkuserapi = user_vk.get_api()
                                print(user.access_token)
                                print(event.message)
                                # del_msg(event.message_id, vk=user_vk)

                                del_all(user)
                                user.state = State.START
                                user.save()
                                continue

                                write_msg(user, "Подбираем кандидатуры....")
                                user_data = vkapi.users.get(
                                    user_ids=event.user_id,
                                    fields="city, sex, birth_year, bdate",
                                )[0]
                                birth_year = user_data["bdate"][5::]
                                print(birth_year)

                                print(user_data)
                                city_id = int(user_data["city"]["id"])
                                sex = (not (user_data["sex"] - 1)) + 1
                                profiles = vkuserapi.users.search(
                                    city=city_id,
                                    sex=sex,
                                    birth_year=birth_year,
                                    count=10,
                                    fields="city, domain, bdate",
                                )["items"]
                                print(profiles)
                                # data["profiles"] = profiles
                                user.state = State.START
                                user.save()
                                break
                            user.state = State.NEED_ACCESS_TOKEN
                            user.save()
                            continue

                        if not user.filter_age_from:
                            if user.age:
                                user.filter_age_from = int(user.age)
                                user.save()
                            elif user.state not in State.SET_MIN_AGE:
                                user.state = State.MIN_AGE_NEED
                                user.save()
                                command = None
                                payload = {}
                        elif not user.filter_age_to:
                            if user.age:
                                user.filter_age_to = int(user.age)
                                user.save()
                            elif user.state not in State.SET_MAX_AGE:
                                user.state = State.MAX_AGE_NEED
                                user.save()
                                command = None
                                payload = {}
                        elif (
                            user.filter_gender is None
                            and user.state != State.CHANGE_GENDER
                        ):
                            user.state = State.GENDER_NEED
                            user.save()
                            command = None
                            payload = {}

                        if not user.state:
                            user.state = State.SHOW
                        elif user.state == State.FIND:
                            del_all(user)
                            kb = VkKeyboard(inline=True)
                            kb.add_button(
                                "Начать поиск",
                                color=VkKeyboardColor.PRIMARY,
                                payload={
                                    "command": "set_state",
                                    "state": State.FINDING,
                                    "delete": True,
                                },
                            )
                            write_msg(
                                user,
                                format_filters_msg(
                                    user,
                                    "Сейчас мы поищем для вас людей по следующим условиям:\n",
                                ),
                                delete=True,
                                keyboard=kb.get_keyboard(),
                            )
                            user.save()
                            break
                        if user.state == State.SHOW_FAV:
                            del_all(user)
                            user.save()
                            fav_cnt = db_count_filter_fav(user)["count"]
                            fav_cnt_total = db_count_fav_total(user)["count"]
                            if fav_cnt:
                                res = db_get_fav(user)
                                write_msg(user, str(res))
                                pprint(res)
                                print(type(res["birthday"]))
                                user_vk, vkuserapi = vk_refresh(user, APP_ID)
                                if not user_vk:
                                    user.state = State.NEED_ACCESS_TOKEN
                                    user.save()
                                    continue
                                profile = vkuserapi.users.get(user_ids=res["vk_id"])[0]
                                pprint(profile)
                                write_msg(user, str(profile))
                                photos = []
                                try:
                                    photos = vkuserapi.photos.get(
                                        owner_id=res["vk_id"],
                                        album_id="profile",
                                        count=1000,
                                        extended=1,
                                        rev=1,
                                    )
                                except Exception as e:
                                    if type(e) == vk_api.exceptions.ApiError:
                                        ee: vk_api.exceptions.ApiError = e
                                        # ee.code
                                        print(
                                            type(e) == ApiError,
                                            e,
                                            ee.code,
                                            ee.error["error_msg"],
                                        )
                                        if (
                                            ee.code == 30
                                            and ee.error["error_msg"]
                                            == "This profile is private"
                                        ):
                                            print("delete")
                                            db_profile_del(user, res["id"])
                                            user.state = State.SHOW
                                            user.save()
                                            continue
                                    print(type(e), e)
                                # print(photos)
                                phs = []
                                for p in photos["items"]:
                                    phs.append(
                                        {
                                            "likes": p["likes"]["count"],
                                            "str": f"photo{p['owner_id']}_{p['id']}",
                                        }
                                    )
                                # pprint(phs)
                                phs = sorted(
                                    phs, key=lambda x: x["likes"], reverse=True
                                )[0 : min(3, len(phs))]
                                pprint(phs)
                                phsl = list(map(lambda x: x.get("str"), phs))
                                if not phsl:
                                    phsl = ["photo-233543845_457239066"]
                                pprint(phsl)
                                write_msg(user, str(phsl))
                                if res:
                                    kb = VkKeyboard(inline=True)
                                    kb.add_button(
                                        "Дальше",
                                        color=VkKeyboardColor.PRIMARY,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW_FAV,
                                            "action": State.ACT_NEXT,
                                            "delete": True,
                                        },
                                    )
                                    kb.add_button(
                                        "➕❤️",
                                        color=VkKeyboardColor.POSITIVE,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW,
                                            "action": State.ACT_TO_FAV,
                                            "delete": True,
                                        },
                                    )
                                    kb.add_button(
                                        "➡️🗑",
                                        color=VkKeyboardColor.NEGATIVE,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW,
                                            "to_blacklist": True,
                                            "delete": True,
                                        },
                                    )
                                    send_kb = kb.get_keyboard()

                                    pprint(locals())
                                    if "msg_format" in locals():
                                        print("in_locals")
                                        del msg_format
                                    msg_format, msg = extend_message(
                                        "",
                                        "Вы просматриваете любимые анкеты\n",
                                        type="bold",
                                    )
                                    pprint(msg_format)
                                    pprint(msg)

                                    msg = f"{msg}\n\n[https://vk.com/{res['domain']}|{profile['first_name']} {profile['last_name']}]\n{res['city']}, {int(res['age'])} {declension(int(res['age']), 'год', 'года', 'лет')}"

                                    write_msg(
                                        user,
                                        msg,
                                        format=msg_format,
                                        delete=True,
                                        keyboard=send_kb,
                                        attach=",".join(phsl),
                                    )
                                    user.save()

                            break
                        if user.state == State.SHOW:
                            # Режим показа анкет
                            del_all(user)
                            user.save()
                            cnt = db_count_filter_profiles(user)["count"]
                            if not cnt and action == State.ACT_AGAIN:
                                db_profile_clean_viewed(user)
                                cnt = db_count_filter_profiles(user)["count"]
                                pass
                            viewed_cnt = db_count_filter_profiles_viewed(user)["count"]
                            fav_cnt = db_count_filter_fav(user)["count"]
                            cnt_blck = db_count_filter_profiles_blacklisted(user)[
                                "count"
                            ]
                            if cnt and action == State.ACT_TO_FAV:
                                res = db_get_profile(user)
                                db_profile_to_fav(user, res["id"])
                                cnt -= 1
                                fav_cnt += 1
                                viewed_cnt += 1

                            if not cnt and cnt_blck and action == State.ACT_CLEAR_BL:
                                db_profile_clean_bl(user)
                                cnt = db_count_filter_profiles(user)["count"]
                                cnt_blck = 0
                                pass

                            if cnt > 0 and command_next:
                                res = db_get_profile(user)
                                db_profile_set_viewed(user, res["id"])
                                cnt -= 1
                                viewed_cnt += 1
                            if cnt > 0 and command_to_blacklist:
                                res = db_get_profile(user)
                                db_profile_set_blacklisted(user, res["id"])
                                cnt -= 1
                                cnt_blck += 1
                                # viewed_cnt += 1
                            # Если фильтры не заполнены, пробуем их заполнить автоматически
                            # Если все еще не заполнены, запрашиваем настройки нужного фильтра

                            kb = VkKeyboard(inline=True)
                            send_kb = kb.get_empty_keyboard()
                            if not cnt:
                                kb.add_button(
                                    "Поискать еще",
                                    color=VkKeyboardColor.PRIMARY,
                                    payload={
                                        "command": "set_state",
                                        "state": State.FIND,
                                        "next": True,
                                        "delete": True,
                                    },
                                )
                                if viewed_cnt:
                                    kb.add_button(
                                        "Просмотреть снова",
                                        color=VkKeyboardColor.POSITIVE,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW,
                                            "action": State.ACT_AGAIN,
                                            "delete": True,
                                        },
                                    )
                                if cnt_blck:
                                    kb.add_line()
                                    kb.add_button(
                                        "Очистить черный список",
                                        color=VkKeyboardColor.POSITIVE,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW,
                                            "delete": True,
                                            "action": State.ACT_CLEAR_BL,
                                        },
                                    )
                                send_kb = kb.get_keyboard()
                            msg = format_filters_msg(
                                user,
                                title="Режим показа анкет\n\nУсловия поиска:",
                            )
                            write_msg(
                                user,
                                f"{msg}\n\nПо этим условияям найдено непросмотренных профилей: {cnt}\nПросмотрено {viewed_cnt}, в избранном {fav_cnt}, в черном списке {cnt_blck}",
                                delete=True,
                                keyboard=send_kb,
                            )
                            if cnt:
                                res = db_get_profile(user)
                                pprint(res)
                                print(type(res["birthday"]))
                                user_vk, vkuserapi = vk_refresh(user, APP_ID)
                                if not user_vk:
                                    user.state = State.NEED_ACCESS_TOKEN
                                    user.save()
                                    continue
                                profile = vkuserapi.users.get(user_ids=res["vk_id"])[0]
                                pprint(profile)
                                photos = []
                                try:
                                    photos = vkuserapi.photos.get(
                                        owner_id=res["vk_id"],
                                        album_id="profile",
                                        count=1000,
                                        extended=1,
                                        rev=1,
                                    )
                                except Exception as e:
                                    if type(e) == vk_api.exceptions.ApiError:
                                        ee: vk_api.exceptions.ApiError = e
                                        # ee.code
                                        print(
                                            type(e) == ApiError,
                                            e,
                                            ee.code,
                                            ee.error["error_msg"],
                                        )
                                        if (
                                            ee.code == 30
                                            and ee.error["error_msg"]
                                            == "This profile is private"
                                        ):
                                            print("delete")
                                            db_profile_del(user, res["id"])
                                            user.state = State.SHOW
                                            user.save()
                                            continue
                                    print(type(e), e)
                                # print(photos)
                                phs = []
                                for p in photos["items"]:
                                    phs.append(
                                        {
                                            "likes": p["likes"]["count"],
                                            "str": f"photo{p['owner_id']}_{p['id']}",
                                        }
                                    )
                                # pprint(phs)
                                phs = sorted(
                                    phs, key=lambda x: x["likes"], reverse=True
                                )[0 : min(3, len(phs))]
                                pprint(phs)
                                phsl = list(map(lambda x: x.get("str"), phs))
                                if not phsl:
                                    phsl = ["photo-233543845_457239066"]
                                pprint(phsl)

                                if res:
                                    kb = VkKeyboard(inline=True)
                                    kb.add_button(
                                        "Дальше",
                                        color=VkKeyboardColor.PRIMARY,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW,
                                            "next": True,
                                            "delete": True,
                                        },
                                    )
                                    kb.add_button(
                                        "➕❤️",
                                        color=VkKeyboardColor.POSITIVE,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW,
                                            "action": State.ACT_TO_FAV,
                                            "delete": True,
                                        },
                                    )
                                    kb.add_button(
                                        "➡️🗑",
                                        color=VkKeyboardColor.NEGATIVE,
                                        payload={
                                            "command": "set_state",
                                            "state": State.SHOW,
                                            "to_blacklist": True,
                                            "delete": True,
                                        },
                                    )
                                    send_kb = kb.get_keyboard()

                                    write_msg(
                                        user,
                                        f"\n\n[https://vk.com/{res['domain']}|{profile['first_name']} {profile['last_name']}]\n{res['city']}, {int(res['age'])} {declension(int(res['age']), 'год', 'года', 'лет')}",
                                        delete=True,
                                        keyboard=send_kb,
                                        attach=",".join(phsl),
                                    )
                                    user.save()
                            break
                            user.state = State.FIND
                            user.save()
                            # if not user.filter_age_from:
                            #     user.state = State.MIN_AGE_NEED
                            #     user.save()
                            #     continue
                            # break

                            # Если отсутствуют записи по фильтрам, делаем запрос, предварительно показав фильтры с опцией изменить их
                            # Если нет непросмотренных записей, предлагаем начать просмотр сначала либо сделать расширенный поиск
                            # Если нет непросмотренных записей и записей слишком много, то предлагаем начать просмотр сначала
                            continue

                        elif user.state == State.FINDING:
                            # Режим поиска анкет
                            del_all(user)
                            write_msg(user, "Идет поиск анкет...", delete=True)

                            user_vk, vkuserapi = vk_refresh(user, APP_ID)
                            if not user_vk:
                                user.state = State.NEED_ACCESS_TOKEN
                                user.save()
                                continue

                            user_data = vkapi.users.get(
                                user_ids=event.user_id,
                                fields="city, sex, birth_year, bdate",
                            )[0]

                            birth_year = user_data["bdate"][5::]
                            print(birth_year)

                            print(user_data)
                            # sex = (not (user_data["sex"] - 1)) + 1
                            profiles = vkuserapi.users.search(
                                city=user.filter_city_id,
                                sex=user.filter_gender,
                                age_from=user.filter_age_from,
                                age_to=user.filter_age_to,
                                count=10,
                                status=6,
                                fields="city, domain, bdate, sex",
                            )["items"]
                            print(profiles)
                            to_insert = []
                            for profile in profiles:
                                print(profile)
                                _ = {"vk_id": profile["id"]}
                                _["domain"] = profile["domain"]
                                _["birthday"] = profile["bdate"]
                                _["gender"] = profile["sex"]
                                _["city_id"] = profile["city"]["id"]
                                _["city"] = profile["city"]["title"]
                                to_insert.append(_)
                                print(_)
                            pprint(to_insert)
                            if not to_insert:
                                kb = VkKeyboard(inline=True)
                                kb.add_button(
                                    "Изменить",
                                    color=VkKeyboardColor.PRIMARY,
                                    payload={
                                        "command": "set_state",
                                        "state": State.SHOW_FILTERS,
                                        "delete": True,
                                    },
                                )

                                format_str, msg = extend_message(
                                    "",
                                    "Ничего не найдено, попробуйте изменить условия поиска",
                                    type="bold",
                                )
                                write_msg(
                                    user,
                                    msg,
                                    delete=True,
                                    format=format_str,
                                    keyboard=kb.get_keyboard(),
                                )
                                break
                            db_add_profiles(
                                to_insert,
                                {"domain", "birthday", "gender", "city_id", "city"},
                            )
                            print(to_insert)
                            user.state = State.SHOW
                            user.save()
                            continue
                        elif (
                            user.state == State.SHOW_FILTERS
                            or user.state == State.CHANGE_FILTERS
                        ):
                            msg = format_filters_msg(user)
                            # Клавиатура для просмотра анкет
                            kb = VkKeyboard(inline=True)
                            if user.state == State.CHANGE_FILTERS:
                                msg += "\n\nЧто изменить"
                                kb.add_button(
                                    "Мин. возраст",
                                    color=VkKeyboardColor.SECONDARY,
                                    payload={
                                        "command": "set_state",
                                        "state": State.MIN_AGE_NEED,
                                        "delete": True,
                                    },
                                )
                                kb.add_button(
                                    "Макс. возраст",
                                    color=VkKeyboardColor.SECONDARY,
                                    payload={
                                        "command": "set_state",
                                        "state": State.MAX_AGE_NEED,
                                        "delete": True,
                                    },
                                )
                                kb.add_line()
                                kb.add_button(
                                    "Пол",
                                    color=VkKeyboardColor.SECONDARY,
                                    payload={
                                        "command": "set_state",
                                        "state": State.GENDER_NEED,
                                        "delete": True,
                                    },
                                )
                                kb.add_button(
                                    "Город",
                                    color=VkKeyboardColor.SECONDARY,
                                    payload=f'{{"command": "set_state", "state": {State.CITY_NEED}}}',
                                )
                                kb.add_line()
                                kb.add_button(
                                    "Всё хорошо, продолжить",
                                    color=VkKeyboardColor.POSITIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.SHOW,
                                        "delete": True,
                                    },
                                )
                            else:
                                kb.add_button(
                                    "Всё хорошо, продолжить",
                                    color=VkKeyboardColor.POSITIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.SHOW,
                                        "delete": True,
                                    },
                                )
                                kb.add_button(
                                    "Изменить",
                                    color=VkKeyboardColor.POSITIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.CHANGE_FILTERS,
                                        "delete": True,
                                    },
                                )
                                # kb.add_button(
                                #    "Смотреть анкеты", color=VkKeyboardColor.PRIMARY
                                # )
                            print("До:", user.to_del)
                            write_msg(
                                user,
                                msg,
                                keyboard=kb.get_keyboard(),
                                delete=True,
                            )
                            print("После:", user.to_del)
                            user.save()
                            break
                        if user.state == State.FILTERS_FINISH:
                            del_msg(user["to_del"])
                        if user.state == State.CITY_NEED:
                            msg = format_filters_msg(user) + "\n\nИзменяем город:"
                            kb = VkKeyboard(inline=True)
                            if not user.filter_city:
                                send_kb = kb.get_empty_keyboard()
                            else:
                                kb.add_button(
                                    "Отмена",
                                    color=VkKeyboardColor.NEGATIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.CHANGE_FILTERS,
                                        "delete": True,
                                    },
                                )
                                send_kb = kb.get_keyboard()
                            write_msg(
                                user,
                                msg,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"Введите название города или его часть",
                                delete=True,
                            )
                            user.state = State.INPUT_CITY
                            user.save()
                            break
                        if user.state == State.MIN_AGE_NEED:
                            msg = (
                                format_filters_msg(user)
                                + "\n\nИзменяем минимальный возраст:"
                            )
                            kb = VkKeyboard(inline=True)
                            if not user.filter_age_from:
                                send_kb = kb.get_empty_keyboard()
                            else:
                                kb.add_button(
                                    "Отмена",
                                    color=VkKeyboardColor.NEGATIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.CHANGE_FILTERS,
                                        "delete": True,
                                    },
                                )
                                send_kb = kb.get_keyboard()
                            write_msg(
                                user,
                                msg,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"Введите минимальный возраст кандидатов (16-{min(99, user.filter_age_to if user.filter_age_to else 100)})",
                                delete=True,
                            )
                            user.state = State.MIN_AGE_INPUT
                            user.save()
                            break

                        if user.state == State.MIN_AGE_INPUT:
                            # Проверяем введенный минимальный возраст
                            del_msg(user.to_del, vk)
                            user.to_del = ""
                            user.save()
                            if not request.isdigit():
                                s = "Вы должны ввести целое число!"
                                write_msg(
                                    user,
                                    s,
                                    format=[
                                        {
                                            "type": "bold",
                                            "offset": 0,
                                            "length": len(s),
                                        }
                                    ],
                                    delete=True,
                                )
                                # )
                                user.state = State.MIN_AGE_NEED
                            elif int(request) < 16:
                                s = "Минимальный возраст не может быть меньше 16 лет"
                                write_msg(
                                    user,
                                    s,
                                    format=[
                                        {
                                            "type": "bold",
                                            "offset": 0,
                                            "length": len(s),
                                        }
                                    ],
                                    delete=True,
                                )
                                # )
                                user.state = State.MIN_AGE_NEED
                            elif int(request) > min(
                                99, user.filter_age_to if user.filter_age_to else 100
                            ):
                                s = f"Минимальный возраст не может быть больше {min(99, user.filter_age_to if user.filter_age_to else 100)} лет"
                                write_msg(
                                    user,
                                    s,
                                    format=[
                                        {
                                            "type": "bold",
                                            "offset": 0,
                                            "length": len(s),
                                        }
                                    ],
                                    delete=True,
                                )
                                # )
                                user.state = State.MIN_AGE_NEED
                            else:
                                user.filter_age_from = int(request)
                                user.state = State.CHANGE_FILTERS
                            user.save()
                            continue

                        if user.state == State.MAX_AGE_NEED:
                            msg = (
                                format_filters_msg(user)
                                + "\n\nИзменяем максимальный возраст:"
                            )
                            kb = VkKeyboard(inline=True)
                            if not user.filter_age_to:
                                send_kb = kb.get_empty_keyboard()
                            else:
                                kb.add_button(
                                    "Отмена",
                                    color=VkKeyboardColor.NEGATIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.CHANGE_FILTERS,
                                        "delete": True,
                                    },
                                )
                                send_kb = kb.get_keyboard()
                            write_msg(
                                user,
                                msg,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"Введите максимальный возраст кандидатов ({max(16, user.filter_age_from if user.filter_age_from else 0)} - 99)",
                                delete=True,
                            )
                            user.state = State.MAX_AGE_INPUT
                            user.save()
                            break

                        if user.state == State.MAX_AGE_INPUT:
                            # Проверяем введенный минимальный возраст
                            del_msg(user.to_del, vk)
                            user.to_del = ""
                            user.save()
                            if not request.isdigit():
                                s = "Вы должны ввести целое число!"
                                write_msg(
                                    user,
                                    s,
                                    format=[
                                        {
                                            "type": "bold",
                                            "offset": 0,
                                            "length": len(s),
                                        }
                                    ],
                                    delete=True,
                                )
                                # )
                                user.state = State.MAX_AGE_NEED
                            elif int(request) < max(
                                16, user.filter_age_from if user.filter_age_from else 0
                            ):
                                s = f"Максимальный возраст не может быть меньше {max(16, user.filter_age_from if user.filter_age_from else 0)} лет"
                                write_msg(
                                    user,
                                    s,
                                    format=[
                                        {
                                            "type": "bold",
                                            "offset": 0,
                                            "length": len(s),
                                        }
                                    ],
                                    delete=True,
                                )
                                user.state = State.MAX_AGE_NEED
                            elif int(request) > 99:
                                s = "Максимальный возраст не может быть больше 99 лет"
                                write_msg(
                                    user,
                                    s,
                                    format=[
                                        {
                                            "type": "bold",
                                            "offset": 0,
                                            "length": len(s),
                                        }
                                    ],
                                    delete=True,
                                )
                                # )
                                user.state = State.MAX_AGE_NEED
                            else:
                                user.filter_age_to = int(request)
                                user.state = State.CHANGE_FILTERS
                            user.save()
                            continue

                        if user.state == State.INPUT_CITY:
                            # Проверяем введенный минимальный возраст
                            del_msg(user.to_del, vk)
                            user.to_del = ""
                            user.save()
                            msg = format_filters_msg(user) + "\n\nВыберите город:"
                            if len(request) > 15:
                                request = request[0:15]
                            write_msg(user, request, delete=True)
                            user_vk, vkuserapi = vk_refresh(user, APP_ID)
                            if not user_vk:
                                user.state = State.NEED_ACCESS_TOKEN
                                user.save()
                                continue
                            cities = vkuserapi.database.getCities(
                                q=request, count=4, need_all=1
                            )
                            print("первый запрос:")
                            pprint(cities)
                            # msg += (
                            #     f"\n{request} {cities['count']} {len(cities['items'])}"
                            # )
                            msg += "\n" + str(cities)
                            if cities["count"] > 4:
                                msg += f"\nВот несколько вариантов:`{request}`."
                                cities = vkuserapi.database.getCities(
                                    q=request, count=4, need_all=0
                                )

                            kb = VkKeyboard(inline=True)
                            msg += "\n"
                            if cities["count"]:
                                for _, city in enumerate(cities["items"]):
                                    msg += f"{_+1}. {city['title']}"
                                    if city.get("area"):
                                        msg += f", {city['area']}"
                                    if city.get("region"):
                                        msg += f", {city['region']}"
                                    msg += "\n"
                                    if _ == 2:
                                        kb.add_line()
                                    kb.add_button(
                                        f"    {_+1}. {city['title']}"[0:40],
                                        color=VkKeyboardColor.SECONDARY,
                                        payload={
                                            "command": "set_state",
                                            "state": State.CHANGE_CITY,
                                            "city_id": city["id"],
                                            "city_title": city["title"],
                                            "delete": True,
                                        },
                                    )
                            msg += "\nВыберите нажав кнопку, либо уточните название, поаторив ввод "
                            if user.filter_city:
                                if cities["count"] > 0:
                                    kb.add_line()
                                kb.add_button(
                                    "Отмена",
                                    color=VkKeyboardColor.NEGATIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.CHANGE_FILTERS,
                                        "delete": True,
                                    },
                                )
                            send_kb = kb.get_keyboard()
                            if not kb.lines[0]:
                                print("empte")
                                send_kb = kb.get_empty_keyboard()
                            print(kb.lines)
                            write_msg(
                                user,
                                msg,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"Выберите пол:",
                                delete=True,
                            )
                            user.state = State.INPUT_CITY
                            user.save()
                            break
                        if user.state == State.CHANGE_CITY:
                            del_msg(user.to_del, vk)
                            user.to_del = ""
                            # Проверяем нажата ли кнопка выбора пола
                            user.save()
                            set_city_id = payload.get("city_id", None)
                            set_city_title = payload.get("city_title", None)
                            print("city_payload", set_city_id, set_city_title)
                            user.filter_city_id = set_city_id
                            user.filter_city = set_city_title
                            user.state = State.CHANGE_FILTERS
                            user.save()
                            continue

                        if user.state == State.GENDER_NEED:
                            msg = format_filters_msg(user) + "\n\nИзменяем пол:"
                            kb = VkKeyboard(inline=True)
                            kb.add_button(
                                "Мужской",
                                color=VkKeyboardColor.SECONDARY,
                                payload={
                                    "command": "set_state",
                                    "state": State.CHANGE_GENDER,
                                    "gender": "2",
                                    "delete": True,
                                },
                            )
                            kb.add_button(
                                "Женский",
                                color=VkKeyboardColor.SECONDARY,
                                payload={
                                    "command": "set_state",
                                    "state": State.CHANGE_GENDER,
                                    "gender": "1",
                                    "delete": True,
                                },
                            )
                            kb.add_button(
                                "Любой",
                                color=VkKeyboardColor.SECONDARY,
                                payload={
                                    "command": "set_state",
                                    "state": State.CHANGE_GENDER,
                                    "gender": "0",
                                    "delete": True,
                                },
                            )
                            if user.filter_gender:
                                kb.add_line()
                                kb.add_button(
                                    "Отмена",
                                    color=VkKeyboardColor.NEGATIVE,
                                    payload={
                                        "command": "set_state",
                                        "state": State.CHANGE_FILTERS,
                                        "delete": True,
                                    },
                                )
                            send_kb = kb.get_keyboard()
                            write_msg(
                                user,
                                msg,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"Выберите пол:",
                                delete=True,
                            )
                            user.state = State.CHANGE_GENDER
                            user.save()
                            break

                        if user.state == State.CHANGE_GENDER:
                            del_msg(user.to_del, vk)
                            user.to_del = ""
                            # Проверяем нажата ли кнопка выбора пола
                            set_gender = payload.get("gender", None)
                            print("gender_payload", payload)
                            if set_gender is None:
                                s = "Выберите пол нажав на кнопку!"
                                write_msg(
                                    user,
                                    s,
                                    format=[
                                        {
                                            "type": "bold",
                                            "offset": 0,
                                            "length": len(s),
                                        }
                                    ],
                                    delete=True,
                                )
                                user.state = State.GENDER_NEED
                            else:
                                user.filter_gender = set_gender
                                print("filter_gender", user.filter_gender)
                                user.save()
                                user.state = State.CHANGE_FILTERS
                            user.save()
                            continue

                        # Другие режимы

                        # Режим настройки каждого фильтра N
                        # Возврат по истории

                        # Режим вывода избранного

                        # Режим работы с blacklist

                        # break

                    # Создание клавиатуры
                    keyboard = VkKeyboard(one_time=True)
                    send_kb = keyboard.get_empty_keyboard()
                    # kb_id = write_msg(user, "set keyboard", keyboard=send_kb)
                    # del_msg(kb_id)
                    if (
                        user.state not in State.GETTING_ACCESS_TOKEN
                        and user.state != State.FIND
                        and user.filter_age_from
                        and user.filter_age_to
                    ):
                        if user.state in State.SET_FILTERS:
                            print("BUTTON Смотреть кандидатов")
                            keyboard.add_button(
                                "Смотреть кандидатов",
                                color=VkKeyboardColor.PRIMARY,
                                payload={
                                    "command": "set_state",
                                    "state": State.SHOW,
                                    "delete": True,
                                },
                            )
                        else:
                            # print("BUTTON Условия подбора")
                            keyboard.add_button(
                                "Условия подбора",
                                color=VkKeyboardColor.PRIMARY,
                                payload={
                                    "command": "set_state",
                                    "state": State.SHOW_FILTERS,
                                    "delete": True,
                                },
                            )
                        keyboard.add_button(
                            "❤ Любимые анкеты",
                            color=VkKeyboardColor.POSITIVE,
                            payload={
                                "command": "set_state",
                                "state": State.SHOW_FAV,
                                "delete": True,
                            },
                        )
                        keyboard.add_line()
                        keyboard.add_button(
                            "⛔ Черный список",
                            color=VkKeyboardColor.NEGATIVE,
                            payload={"command": "blacklisted"},
                        )
                        keyboard.add_button(
                            "Помощь",
                            color=VkKeyboardColor.SECONDARY,
                            payload={"command": "help"},
                        )
                        keyboard.add_button(
                            "Перезапуск",
                            color=VkKeyboardColor.SECONDARY,
                            payload={"command": "restart"},
                        )
                        send_kb = keyboard.get_keyboard()

                    kb_id = write_msg(user, "set keyboard", keyboard=send_kb)
                    del_msg(kb_id)

                # if request == "привет":
                #     write_msg(event.user_id, f"Хай, {event.user_id}")
                # elif request == "пока":
                #     write_msg(event.user_id, "Пока((")
                # else:
                #     write_msg(event.user_id, "Не поняла вашего ответа...")
                # # db_update_user(user)
                # user.save()
    except requests_exceptions_ReadTimeout:
        print("\n Переподключение к серверам ВК \n")
        time_sleep(3)
