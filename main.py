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
    vk_refresh,
)

from User import User
from DB.profiles import (
    db_add_profiles,
    db_profile_del,
    db_count_filter_fav,
)

from messages import (
    del_all,
    del_msg,
    format_filters_msg,
    write_msg,
    declension,
    extend_message,
)
from dlg_access import dlg_access, dlg_access_wait
from dlg_show import dlg_show
import dlg_filters, dlg_fav

vk = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(
    vk,
    wait=1,
)
vkapi = vk.get_api()

# Создаем доп. экземпляр для запросов от имени пользователя
user_vk = None
vkuserapi = None


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
            print(e)
            continue
        if not len(events):
            sleep(1)
        for event in events:
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:

                    payload = json.loads(event.extra_values.get("payload", "{}"))
                    command = payload.get("command")
                    action = payload.get("action")
                    uid = event.user_id

                    # Получаем из базы инфу о пользователе. Если нету, создаем запись, если есть, обновляем запись
                    user = User(uid)
                    user.App = App
                    user.action = action
                    user.payload = payload
                    user.request = event.text
                    user.new_message = True
                    del action, payload

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
                        elif (
                            not user.refresh_token
                            and user.state not in State.GETTING_ACCESS_TOKEN
                        ):
                            # требуется авторизация
                            user.state = State.NEED_ACCESS_TOKEN
                        elif user.state == State.NEED_ACCESS_TOKEN:
                            # выводим запрос авторизации
                            dlg_access(user)
                            break

                        elif user.state == State.WAIT_ACCESS_TOKEN:
                            dlg_access_wait(user)

                        # если не указан фильтр минимального возраста
                        elif (
                            not user.filter_age_from
                            and user.state not in State.SET_MIN_AGE
                        ):

                            if user.age:
                                # берем его по возрасту пользователя
                                user.filter_age_from = int(user.age)

                            else:
                                # при отсутствии возраста пользователя, переходим в режим запроса
                                user.state = State.MIN_AGE_NEED
                                del_all(user)

                        # Режим ввода минимального возраста
                        elif user.state == State.MIN_AGE_NEED:
                            dlg_filters.min_age_need(user)
                            break

                        # Проверяем введенный минимальный возраст
                        elif user.state == State.MIN_AGE_INPUT:
                            dlg_filters.min_age_input(user)

                        # если не указан фильтр максимального возраста
                        elif not user.filter_age_to and user.state not in State.SET_AGE:

                            # берем его по возрасту пользователя
                            if user.age:
                                user.filter_age_to = int(user.age)

                            # при отсутствии возраста пользователя, переходим в режим запроса
                            elif user.state not in State.SET_MAX_AGE:
                                user.state = State.MAX_AGE_NEED
                                del_all(user)

                        # Режим ввода максимального возраста
                        elif user.state == State.MAX_AGE_NEED:
                            dlg_filters.max_age_need(user)
                            break

                        elif user.state == State.MAX_AGE_INPUT:
                            # Проверяем введенный максимальный возраст
                            dlg_filters.max_age_input(user)

                        # если не указан половой фильтр
                        elif (
                            user.filter_gender is None
                            and user.state not in State.SET_AGE | State.SET_GENDER
                        ):
                            # переходим в режим запроса
                            user.state = State.GENDER_NEED

                        # режим выбора пола
                        elif user.state == State.GENDER_NEED:
                            dlg_filters.gender_need(user)
                            break

                        # проверяем и запоминаем применяем выбранный пол
                        elif user.state == State.CHANGE_GENDER:
                            dlg_filters.change_gender(user)

                        # если не задан фильтр по городу
                        # переходим к диалогу выбора города
                        elif (
                            user.filter_city_id is None
                            and user.state
                            not in State.SET_AGE | State.SET_GENDER | State.SET_CITY
                        ):
                            user.state = State.CITY_NEED
                            del_all(user)

                        # начало диалога выбора города
                        elif user.state == State.CITY_NEED:
                            dlg_filters.city_need(user)
                            break

                        # проверяем введенный город,
                        # запрашиваем в ВК и предлагаем варианты
                        elif user.state == State.INPUT_CITY:
                            if dlg_filters.input_city(user):
                                break

                        # проверяем нажата ли кнопка выбора города
                        # и запоминаем
                        elif user.state == State.CHANGE_CITY:
                            dlg_filters.change_city(user)

                        elif user.state == State.CHANGE_FILTERS:
                            dlg_filters.change(user)
                            break

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
                            if dlg_fav.show(user):
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
                                        "state": State.CHANGE_FILTERS,
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
                                user,
                                to_insert,
                                {"domain", "birthday", "gender", "city_id", "city"},
                            )
                            print(to_insert)
                            user.state = State.SHOW
                            del_all(user)
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
                                    "state": State.CHANGE_FILTERS,
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
        # except Exception as e:
        #     print(e)
        sleep(1)
