from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError as VkApiError

from messages import del_all, format_filters_msg, write_msg, declension, extend_message
from State import State
from vk_auth import vk_refresh


def change(user):
    msg = format_filters_msg(user)
    # Клавиатура для просмотра анкет
    kb = VkKeyboard(inline=True)
    if user.state == State.CHANGE_FILTERS:
        msg += ""
        kb.add_button(
            "возраст от",
            color=VkKeyboardColor.SECONDARY,
            payload={
                "command": "set_state",
                "state": State.MIN_AGE_NEED,
                "delete": True,
            },
        )
        kb.add_button(
            "возраст до",
            color=VkKeyboardColor.SECONDARY,
            payload={
                "command": "set_state",
                "state": State.MAX_AGE_NEED,
                "delete": True,
            },
        )
        kb.add_line()
        kb.add_button(
            "пол",
            color=VkKeyboardColor.SECONDARY,
            payload={
                "command": "set_state",
                "state": State.GENDER_NEED,
                "delete": True,
            },
        )
        kb.add_button(
            "город",
            color=VkKeyboardColor.SECONDARY,
            payload=f'{{"command": "set_state", "state": {State.CITY_NEED}}}',
        )
        kb.add_line()
        kb.add_button(
            "Всё хорошо, к анкетам!",
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
    )
    print("После:", user.to_del)


def min_age_need(user):
    kb = VkKeyboard(inline=True)
    if user.filter_age_from:
        msg_format = []
        msg = format_filters_msg(user) + "\n\nИзменяем минимальный возраст:"
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
        keyboard=send_kb,
    )
    write_msg(
        user,
        f"Введите минимальный возраст (16-{min(99, user.filter_age_to if user.filter_age_to else 100)}):",
    )
    user.state = State.MIN_AGE_INPUT


def min_age_input(user):
    del_all(user)
    if not user.request.isdigit():
        error_message = "Вы должны ввести целое положительное число!"
    elif int(user.request) < 16:
        error_message = "Минимальный возраст не может быть меньше 16 лет"
    elif int(user.request) > min(
        99,
        user.filter_age_to if user.filter_age_to else 100,
    ):
        error_message = f"Минимальный возраст не может быть больше {min(99, user.filter_age_to if user.filter_age_to else 100)} лет"
    else:
        if user.filter_age_from:
            user.state = State.CHANGE_FILTERS
        else:
            user.state = State.SHOW
        user.filter_age_from = int(user.request)
        return

    msg_format, msg = extend_message("", error_message, type="bold")
    write_msg(user, msg, format=msg_format)
    user.state = State.MIN_AGE_NEED


def max_age_need(user):
    kb = VkKeyboard(inline=True)
    if user.filter_age_to:
        msg_format = []
        msg = format_filters_msg(user) + "\n\nИзменяем максимальный возраст:"
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
        keyboard=send_kb,
    )
    write_msg(
        user,
        f"{'В' if user.filter_age_to else 'Теперь в' }ведите максимальный возраст ({max(user.filter_age_from ,16)} - 99):",
    )
    user.state = State.MAX_AGE_INPUT


def max_age_input(user):
    # Проверяем введенный максимальный возраст
    del_all(user)
    if not user.request.isdigit():
        error_message = "Вы должны ввести целое положительное число!"
    elif int(user.request) < max(
        16, user.filter_age_from if user.filter_age_from else 0
    ):
        error_message = f"Максимальный возраст не может быть меньше минимального! ({max(16, user.filter_age_from if user.filter_age_from else 0)} лет)"
    elif int(user.request) > 99:
        error_message = "Максимальный возраст не может быть больше 99 лет"
    else:
        if user.filter_age_to:
            user.state = State.CHANGE_FILTERS
        else:
            user.state = State.SHOW
        user.filter_age_to = int(user.request)
        return

    msg_format, msg = extend_message("", error_message, type="bold")
    write_msg(user, msg, format=msg_format)

    user.state = State.MAX_AGE_NEED


def gender_need(user):
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
    if not user.filter_gender is None:
        msg_format = []
        msg = format_filters_msg(user) + "\n\nИзменяем пол кандидатов:"
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
        keyboard=send_kb,
    )
    user.state = State.CHANGE_GENDER


def change_gender(user):
    del_all(user)
    # Проверяем нажата ли кнопка выбора пола
    set_gender = user.payload.get("gender", None)
    if set_gender is None:
        error_message = "Выберите пол нажав на кнопку!"
        user.state = State.GENDER_NEED
    else:
        if user.filter_gender is None:
            user.state = State.SHOW
        else:
            user.state = State.CHANGE_FILTERS
        user.filter_gender = set_gender
        return
    msg_format, msg = extend_message("", error_message, type="bold")
    write_msg(user, msg, format=msg_format)


def city_need(user):
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
        keyboard=send_kb,
    )
    write_msg(
        user,
        f"Введите название города или его часть:",
    )
    user.state = State.INPUT_CITY


def input_city(user):
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
    if len(user.request) > 15:
        user.request = user.request[0:15]
        # write_msg(
        #     user, "много городов, вот некоторые"
        # )
    user.App.user_vk, user.App.vkuserapi = vk_refresh(user, user.App.APP_ID)
    if not user.App.user_vk:
        user.refresh_token = ""
        user.state = State.NEED_ACCESS_TOKEN
        user.save()
        return
    cities = user.App.vkuserapi.database.getCities(q=user.request, count=4, need_all=1)
    if cities["count"] > 4:
        cities = user.App.vkuserapi.database.getCities(
            q=user.request, count=4, need_all=0
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
        msg += "\nВыберите нажав кнопку, либо уточните название, повторив ввод (название или его часть)"

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
        )
        user.state = State.CITY_NEED
        return
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
        keyboard=send_kb,
    )
    user.state = State.INPUT_CITY
    return True


def change_city(user):
    del_all(user)
    # Проверяем нажата ли кнопка выбора пола
    user.save()
    old = user.filter_city_id
    set_city_id = user.payload.get("city_id", None)
    set_city_title = user.payload.get("city_title", None)
    print("city_payload", set_city_id, set_city_title)
    user.filter_city_id = set_city_id
    user.filter_city = set_city_title
    if old is None:
        user.state = State.SHOW
    else:
        user.state = State.CHANGE_FILTERS
