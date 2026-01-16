import json
from time import sleep

from vk_api.longpoll import VkEventType

# from requests.exceptions import ReadTimeout as requests_exceptions_ReadTimeout
import requests.exceptions

from App import App
from State import State
from User import User
import dlg_access, dlg_show, dlg_filters, dlg_fav, dlg_keyboard
from messages import del_all


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
            dlg_access.get(user)
            break

        elif user.state == State.WAIT_ACCESS_TOKEN:
            dlg_access.wait(user)

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
            if dlg_show.show(user):
                break

        elif user.state == State.SHOW_BL:
            user.state = State.SHOW


def process_event(event):
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
        user.__init__(uid, True, App, action, payload, event, True)
    elif len(user.to_del) > 30:
        del_all(user)

    if command == "set_state":
        user.state = json.loads(event.extra_values.get("payload", "{}")).get("state")
        if json.loads(event.extra_values.get("payload", "{}")).get("delete", False):
            del_all(user)
    from pprint import pprint

    print("user.App = ", end="")
    pprint(user.App)
    dlg_keyboard.main_menu(user, menu_message=True)

    states_processing(user)

    dlg_keyboard.main_menu(user)
    user.save()


def main():
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
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    process_event(event)

        except requests.exceptions.ReadTimeout:
            print("\n Переподключение к серверам ВК \n")
            sleep(3)
        # except Exception as e:
        #     print(e)


if __name__ == "__main__":
    main()
