from random import randrange
import json
from pprint import pprint

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from tokens import TOKEN, APP_ID, AUTH_REDIRECT_URI
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from requests.exceptions import ReadTimeout as requests_exceptions_ReadTimeout

from vk_api.exceptions import ApiError

from time import sleep

from State import State

from vk_auth import (
    vk_auth_link,
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

from messages import del_all, del_msg, format_filters_msg, write_msg, declension
from dlg_access import dlg_access, dlg_access_wait
from dlg_show import dlg_show

# token = input('Token: ')
vk = vk_api.VkApi(token=TOKEN)
# longpoll = VkLongPoll(vk)
longpoll = VkLongPoll(
    vk,
    wait=1,
)
vkapi = vk.get_api()

# Создаем доп. экземпляр для запросов от имени пользователя
user_vk = None
vkuserapi = None


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


# def connect():
#     conn = psycopg2.connect(database="vk_dating", user="postgres", password="postgres")
#     return conn


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
class App:
    APP_ID = APP_ID
    AUTH_REDIRECT_URI = AUTH_REDIRECT_URI
    vk = vk
    vkapi = vkapi
    user_vk = user_vk
    vkuserapi = vkuserapi


del APP_ID, vk, vkapi, user_vk, vkuserapi


while True:
    try:
        # for event in longpoll.listen():
        try:
            events = longpoll.check()
        except Exception as e:
            continue

        for event in events:
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:

                    payload = json.loads(event.extra_values.get("payload", "{}"))
                    command = payload.get("command")
                    action = payload.get("action")

                    uid = event.user_id
                    request = event.text
                    new_message = True

                    # Получаем из базы инфу о пользователе. Если нету, создаем запись, если есть, обновляем запись
                    user = User(uid)
                    user.App = App
                    user.action = action
                    # user.new
                    del action
                    if user.is_new:
                        user_data = user.App.vkapi.users.get(
                            user_ids=uid,
                            fields="city, sex, birth_year, bdate",
                        )[0]
                        user.birthday = user_data["bdate"]
                        user.save()
                        user.__init__()

                    if command == "set_state":
                        user.state = json.loads(
                            event.extra_values.get("payload", "{}")
                        ).get("state")
                        if json.loads(event.extra_values.get("payload", "{}")).get(
                            "delete", False
                        ):
                            del_all(user)
                        user.save()

                    # обработка состояний диалога
                    # Цикл выполняется пока не нужен ввод пользователя
                    while True:
                        print(f"{user.state = }")
                        if not user.state:
                            # При первом запуске переходим в режим вывода анкет
                            user.state = State.SHOW
                            # continue
                        elif (
                            not user.refresh_token
                            and user.state not in State.GETTING_ACCESS_TOKEN
                        ):
                            # требуется авторизация
                            user.state = State.NEED_ACCESS_TOKEN
                            # user.save()
                        elif user.state == State.NEED_ACCESS_TOKEN:
                            # выводим запрос авторизации
                            dlg_access(user)
                            break
                        elif user.state == State.WAIT_ACCESS_TOKEN:
                            dlg_access_wait(user)
                            # continue
                        elif (
                            not user.filter_age_from
                            and user.state not in State.SET_MIN_AGE
                        ):
                            if user.age:
                                user.filter_age_from = int(user.age)
                                user.save()
                            elif user.state not in State.SET_MIN_AGE:
                                user.state = State.MIN_AGE_NEED
                                del_all(user)
                                user.save()
                                command = None
                                payload = {}
                        elif not user.filter_age_to and user.state not in State.SET_AGE:
                            if user.age:
                                user.filter_age_to = int(user.age)
                                user.save()
                            elif user.state not in State.SET_MAX_AGE:
                                del_all(user)
                                user.state = State.MAX_AGE_NEED
                                user.save()
                                command = None
                                payload = {}
                        elif (
                            user.filter_gender is None
                            and user.state not in State.SET_AGE | State.SET_GENDER
                        ):
                            user.state = State.GENDER_NEED
                            user.save()
                            print("after_save")
                            command = None
                            payload = {}
                        elif (
                            user.filter_city_id is None
                            and user.state
                            not in State.SET_AGE | State.SET_GENDER | State.SET_CITY
                        ):
                            user.state = State.CITY_NEED
                            del_all(user)
                            user.save()
                            command = None
                            payload = {}
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
                        elif user.state == State.SHOW_FAV:
                            del_all(user)
                            user.save()
                            fav_cnt = db_count_filter_fav(user)["count"]
                            fav_cnt_total = db_count_fav_total(user)["count"]
                            if fav_cnt:
                                res = db_get_fav(user)
                                write_msg(user, str(res))
                                pprint(res)
                                print(type(res["birthday"]))
                                user.App.user_vk, user.App.vkuserapi = vk_refresh(
                                    user, user.App.APP_ID
                                )
                                if not user.App.user_vk:
                                    user.state = State.NEED_ACCESS_TOKEN
                                    user.save()
                                    continue
                                profile = user.App.vkuserapi.users.get(
                                    user_ids=res["vk_id"]
                                )[0]
                                pprint(profile)
                                write_msg(user, str(profile))
                                photos = []
                                try:
                                    photos = user.App.vkuserapi.photos.get(
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
                        elif user.state == State.SHOW:
                            res = dlg_show(user)
                            if res == 1:
                                break
                            elif not res:
                                continue
                        elif user.state == State.FINDING:
                            # Режим поиска анкет
                            del_all(user)
                            write_msg(user, "Идет поиск анкет...", delete=True)

                            user.App.user_vk, user.App.vkuserapi = vk_refresh(
                                user, user.App.APP_ID
                            )
                            if not user.App.user_vk:
                                user.state = State.NEED_ACCESS_TOKEN
                                user.save()
                                continue

                            user_data = (
                                user.App.vkapi.users.get(
                                    user_ids=event.user_id,
                                    fields="city, sex, birth_year, bdate",
                                )[0],
                            )

                            # birth_year = user_data["bdate"][5::]
                            # sex = (not (user_data["sex"] - 1)) + 1
                            profiles = user.App.vkuserapi.users.search(
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
                            del_all(user)
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
                        elif user.state == State.FILTERS_FINISH:
                            del_msg(user["to_del"])
                        elif user.state == State.CITY_NEED:
                            kb = VkKeyboard(inline=True)
                            if not user.filter_city_id:
                                msg_format, msg = extend_message(
                                    "",
                                    "Теперь нужно указать город для поиска кандидатов",
                                    type="bold",
                                )
                                send_kb = kb.get_empty_keyboard()
                            else:
                                msg_format = []
                                msg = format_filters_msg(user) + "\n\nИзменяем город:"
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
                                format=msg_format,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"Введите название города или его часть:",
                                delete=True,
                            )
                            user.state = State.INPUT_CITY
                            break
                        elif user.state == State.MIN_AGE_NEED:
                            print("MIN_AGE_NEED")
                            kb = VkKeyboard(inline=True)
                            if user.filter_age_from:
                                msg_format = []
                                msg = (
                                    format_filters_msg(user)
                                    + "\n\nИзменяем минимальный возраст:"
                                )
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
                            else:
                                msg_format, msg = extend_message(
                                    "",
                                    "Для начала нужно указать диапазон возраста кандидатов\n",
                                    type="bold",
                                )

                                send_kb = kb.get_empty_keyboard()
                            write_msg(
                                user,
                                msg,
                                format=msg_format,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"Введите минимальный возраст (16-{min(99, user.filter_age_to if user.filter_age_to else 100)}):",
                                delete=True,
                            )
                            user.state = State.MIN_AGE_INPUT
                            user.save()
                            break

                        elif user.state == State.MIN_AGE_INPUT:
                            # Проверяем введенный минимальный возраст
                            del_msg(user.to_del, user.App.vk)
                            user.to_del = ""
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

                        elif user.state == State.MAX_AGE_NEED:
                            kb = VkKeyboard(inline=True)
                            if user.filter_age_to:
                                msg_format = []
                                msg = (
                                    format_filters_msg(user)
                                    + "\n\nИзменяем максимальный возраст:"
                                )
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
                            else:
                                msg_format, msg = extend_message(
                                    "",
                                    "Для начала нужно указать диапазон возраста кандидатов\n",
                                    type="bold",
                                )
                                msg += "Вы уже задали минимальный возраст: "
                                msg_format, msg = extend_message(
                                    msg,
                                    str(user.filter_age_from),
                                    msg_format,
                                    type="bold",
                                )
                                msg_format, msg = extend_message(
                                    msg,
                                    "\nПозже вы сможете изменить его и остальные фильтры в любой момент...",
                                    msg_format,
                                    type="italic",
                                )

                                send_kb = kb.get_empty_keyboard()
                            write_msg(
                                user,
                                msg,
                                format=msg_format,
                                delete=True,
                                keyboard=send_kb,
                            )
                            write_msg(
                                user,
                                f"{'В' if user.filter_age_to else 'Теперь в' }ведите максимальный возраст ({max(user.filter_age_from ,16)} - 99):",
                                delete=True,
                            )
                            user.state = State.MAX_AGE_INPUT
                            break

                        elif user.state == State.MAX_AGE_INPUT:
                            # Проверяем введенный минимальный возраст
                            del_all(user)
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
                                s = f"Максимальный возраст не может быть меньше минимального! ({max(16, user.filter_age_from if user.filter_age_from else 0)} лет)"
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

                        elif user.state == State.INPUT_CITY:
                            # Проверяем введенный город
                            del_all(user)
                            kb = VkKeyboard(inline=True)
                            msg_format = []
                            if not user.filter_city_id:
                                msg_format, msg = extend_message(
                                    "",
                                    "Теперь нужно указать город для поиска кандидатов",
                                    type="bold",
                                )
                            else:
                                msg = format_filters_msg(user) + "\n\nВыберите город:"
                                # msg = format_filters_msg(user) + "\n\nИзменяем город:"
                                # kb.add_button(
                                #     "Отмена",
                                #     color=VkKeyboardColor.NEGATIVE,
                                #     payload={
                                #         "command": "set_state",
                                #         "state": State.CHANGE_FILTERS,
                                #         "delete": True,
                                #     },
                                # )
                            if len(request) > 15:
                                request = request[0:15]
                                # write_msg(
                                #     user, "много городов, вот некоторые", delete=True
                                # )
                            user.App.user_vk, user.App.vkuserapi = vk_refresh(
                                user, user.App.APP_ID
                            )
                            if not user.App.user_vk:
                                user.refresh_token = ""
                                user.state = State.NEED_ACCESS_TOKEN
                                user.save()
                                continue
                            cities = user.App.vkuserapi.database.getCities(
                                q=request, count=4, need_all=1
                            )
                            if cities["count"] > 4:
                                cities = user.App.vkuserapi.database.getCities(
                                    q=request, count=4, need_all=0
                                )
                            if cities["count"]:
                                msg += f"\nВот что мы нашли по вашему запросу:\n"
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
                                msg += "\nВыберите нажав кнопку, либо уточните название, поаторив ввод (название или его часть)"
                            else:
                                del_all(user)
                                msg_format, msg = extend_message(
                                    "",
                                    "Мы ничего не нашли по вашему запросу, попробуйте ввести уточненное название",
                                    type="bold",
                                )
                                write_msg(
                                    user,
                                    msg,
                                    format=msg_format,
                                    delete=True,
                                )
                                user.state = State.CITY_NEED
                                continue
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
                                format=msg_format,
                                delete=True,
                                keyboard=send_kb,
                            )
                            user.state = State.INPUT_CITY
                            break
                        elif user.state == State.CHANGE_CITY:
                            del_all(user)
                            # Проверяем нажата ли кнопка выбора пола
                            user.save()
                            old = user.filter_city_id
                            set_city_id = payload.get("city_id", None)
                            set_city_title = payload.get("city_title", None)
                            print("city_payload", set_city_id, set_city_title)
                            user.filter_city_id = set_city_id
                            user.filter_city = set_city_title
                            if old is None:
                                user.state = State.SHOW
                            else:
                                user.state = State.CHANGE_FILTERS
                            user.save()
                            continue

                        elif user.state == State.GENDER_NEED:
                            print("State.GENDER_NEED")
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
                                msg_format = []
                                msg = (
                                    format_filters_msg(user)
                                    + "\n\nИзменяем пол кандидатов:"
                                )
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
                            else:
                                msg_format, msg = extend_message(
                                    "",
                                    "Теперь нужно указать пол кандидатов\n",
                                    type="bold",
                                )
                            send_kb = kb.get_keyboard()
                            write_msg(
                                user,
                                msg,
                                format=msg_format,
                                delete=True,
                                keyboard=send_kb,
                            )
                            user.state = State.CHANGE_GENDER
                            break

                        elif user.state == State.CHANGE_GENDER:
                            del_all(user)
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
                                old_gender = user.filter_gender
                                user.filter_gender = set_gender
                                if old_gender is None:
                                    user.state = State.SHOW
                                else:
                                    user.state = State.CHANGE_FILTERS
                            user.save()
                            continue

                        user.save()
                    user.save()
                    # Создание клавиатуры
                    keyboard = VkKeyboard(one_time=False)
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
                    del_msg(kb_id, user.App.vk)

                    user.save()

    except requests_exceptions_ReadTimeout:
        print("\n Переподключение к серверам ВК \n")
        sleep(3)
    sleep(1)
