import json
from time import sleep

from vk_api.longpoll import VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from requests.exceptions import ReadTimeout as requests_exceptions_ReadTimeout

from App import App
from State import State
from User import User
from messages import (
    del_all,
    del_msg,
    write_msg,
)
from dlg_access import dlg_access, dlg_access_wait
from dlg_show import dlg_show
import dlg_filters, dlg_fav


def states_processing(user):
    # обработка состояний диалога
    # Цикл выполняется пока не нужен ввод пользователя
    while True:
        print(f"{user.state = }")
        if not user.state:
            # При первом запуске переходим в режим вывода анкет
            user.state = State.SHOW
        elif not user.refresh_token and user.state not in State.GETTING_ACCESS_TOKEN:
            # требуется авторизация
            user.state = State.NEED_ACCESS_TOKEN
        elif user.state == State.NEED_ACCESS_TOKEN:
            # выводим запрос авторизации
            dlg_access(user)
            break

        elif user.state == State.WAIT_ACCESS_TOKEN:
            dlg_access_wait(user)

        # если не указан фильтр минимального возраста
        elif not user.filter_age_from and user.state not in State.SET_MIN_AGE:

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
            and user.state not in State.SET_AGE | State.SET_GENDER | State.SET_CITY
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
            dlg_show.find(user)
            break

        # Режим поиска анкет
        elif user.state == State.FINDING:
            if dlg_show.finding(user):
                break

        elif user.state == State.SHOW_FAV:
            if dlg_fav.show(user):
                break

        elif user.state == State.SHOW:
            if dlg_show(user):
                break


while True:
    try:
        # for event in longpoll.listen():
        try:
            events = App.longpoll.check()
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
                    user = User(uid, True, App, action, payload, event, True)

                    if user.is_new:
                        user_data = user.App.vkapi.users.get(
                            user_ids=uid,
                            fields="city, sex, birth_year, bdate",
                        )[0]
                        user.birthday = user_data["bdate"]
                        user.save()
                        user.__init__()
                    elif len(user.to_del) > 30:
                        del_all(user)

                    if command == "set_state":
                        user.state = json.loads(
                            event.extra_values.get("payload", "{}")
                        ).get("state")
                        if json.loads(event.extra_values.get("payload", "{}")).get(
                            "delete", False
                        ):
                            del_all(user)
                        user.save()

                    states_processing(user)
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
