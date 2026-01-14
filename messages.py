from random import randrange
from User import User
import json


def del_all(user):

    del_msg(user.to_del, user.App.vk)
    user.to_del = ""
    user.save()


def del_msg(message_id, vk):  # user_id,
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


def format_filters_msg(user, title="Условия подбора кандидатов:\n"):
    no_value = "Не задан"
    genders = ["Любой", "Женский", "Мужской"]
    min_age = user.filter_age_from if user.filter_age_from else no_value
    max_age = user.filter_age_to if user.filter_age_to else no_value
    gender = (
        genders[int(user.filter_gender)] if not user.filter_gender is None else no_value
    )
    city = user.filter_city if not user.filter_city is None else no_value
    return (
        title + f"\n        Минимальный возраст: {min_age}"
        f"\n        Максимальный возраст: {max_age}"
        f"\n\n        Пол: {gender}"
        f"\n\n        Город: {city}"
    )


def write_msg(user, message, keyboard=None, format=None, delete=False, attach=None):
    if isinstance(user, User):
        user_id = user.vk_id
    else:
        user_id = user
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
    res = user.App.vk.method(
        "messages.send",
        pars,
    )
    if delete:
        if delete and isinstance(user, User):
            user.add_to_del(res)
    return res


def add_to_del(user, message_id):
    if not user.to_del:
        user.to_del = ""

    user.to_del = (
        ",".join((user.to_del.split(",") + [str(message_id)]))
        if user.to_del
        else str(message_id)
    )


def declension(n, for_1, for_234, for_other):
    d = n % 10

    if d == 1 and n % 100 != 11:
        return for_1

    if d in [2, 3, 4] and not (n % 100 in [12, 13, 14]):
        return for_234

    return for_other
