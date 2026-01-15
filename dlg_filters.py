from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError as VkApiError

from messages import del_all, format_filters_msg, write_msg, declension, extend_message
from DB.profiles import (
    db_count_filter_profiles,
    db_profile_clean_viewed,
    db_count_filter_profiles_viewed,
    db_count_filter_fav,
    db_count_filter_profiles_blacklisted,
    db_get_profile,
    db_profile_to_fav,
    db_profile_set_viewed,
    db_profile_clean_bl,
    db_profile_set_blacklisted,
    db_profile_del,
)
from State import State
from vk_auth import vk_refresh


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
        delete=True,
        keyboard=send_kb,
    )
    write_msg(
        user,
        f"Введите минимальный возраст (16-{min(99, user.filter_age_to if user.filter_age_to else 100)}):",
        delete=True,
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
    write_msg(user, msg, format=msg_format, delete=True)
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
        delete=True,
        keyboard=send_kb,
    )
    write_msg(
        user,
        f"{'В' if user.filter_age_to else 'Теперь в' }ведите максимальный возраст ({max(user.filter_age_from ,16)} - 99):",
        delete=True,
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
    write_msg(user, msg, format=msg_format, delete=True)

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
        delete=True,
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
    write_msg(user, msg, format=msg_format, delete=True)
