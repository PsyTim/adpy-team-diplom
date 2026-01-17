from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError as VkApiError

from messages import del_all, format_filters_msg, write_msg, declension, extend_message
import DB.profiles
from DB.profiles import (
    db_add_profiles,
    db_count_filter_profiles,
    db_profile_clean_viewed,
    db_count_filter_profiles_viewed,
    db_count_filter_fav,
    db_get_profile,
    db_profile_to_fav,
    db_profile_set_blacklisted,
    db_profile_del,
)
from State import State
from vk_auth import vk_refresh


def find(user):
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
        keyboard=kb.get_keyboard(),
    )


def finding(user):
    "Режим поиска анкет"
    del_all(user)
    write_msg(user, "Идет поиск анкет...")

    user.App.user_vk, user.App.vkuserapi = vk_refresh(user, user.App.APP_ID)
    if not user.App.user_vk:
        user.state = State.NEED_ACCESS_TOKEN
        user.save()
        # continue
        return

    user_data = (
        user.App.vkapi.users.get(
            user_ids=user.vk_id,
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
    to_insert = []
    for profile in profiles:
        _ = {"vk_id": profile["id"]}
        _["domain"] = profile["domain"]
        _["birthday"] = profile["bdate"]
        _["gender"] = profile["sex"]
        _["city_id"] = profile["city"]["id"]
        _["city"] = profile["city"]["title"]
        to_insert.append(_)
        # print(_)
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
            format=format_str,
            keyboard=kb.get_keyboard(),
        )
        # break
        return True
    db_add_profiles(
        user,
        to_insert,
        {"domain", "birthday", "gender", "city_id", "city"},
    )
    user.state = State.SHOW
    del_all(user)


def show(user):
    # Режим показа анкет
    # del_all(user)
    # user.save()
    cnt = db_count_filter_profiles(user)["count"]
    if not cnt and user.action == State.ACT_AGAIN:
        db_profile_clean_viewed(user)
        cnt = db_count_filter_profiles(user)["count"]
        pass
    viewed_cnt = db_count_filter_profiles_viewed(user)["count"]
    fav_cnt = db_count_filter_fav(user)["count"]
    cnt_blck = DB.profiles.count_filter_blacklisted(user)
    if cnt and user.action == State.ACT_TO_FAV:
        res = db_get_profile(user)
        db_profile_to_fav(user, res["id"])
        cnt -= 1
        fav_cnt += 1
        viewed_cnt += 1

    if not cnt and cnt_blck and user.action == State.ACT_CLEAN_BL:
        DB.profiles.clean_bl(user)
        cnt = db_count_filter_profiles(user)["count"]
        cnt_blck = 0
        pass

    if cnt > 0 and user.action == State.ACT_NEXT:
        res = db_get_profile(user)
        db_profile_set_viewed(user, res["id"])
        cnt -= 1
        viewed_cnt += 1
    if cnt > 0 and user.action == State.ACT_ADD_BL:
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
                "action": State.ACT_NEXT,
                #                "next": True,
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
                    "state": State.CLEAN_BL,
                    "delete": True,
                    # "action": State.ACT_CLEAN_BL,
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
        keyboard=send_kb,
    )
    if cnt:
        res = db_get_profile(user)
        user.App.user_vk, user.App.vkuserapi = vk_refresh(user, user.App.APP_ID)
        if not user.App.user_vk:
            user.state = State.NEED_ACCESS_TOKEN
            user.save()
            return 0
            # continue
        profile = user.App.vkuserapi.users.get(user_ids=res["vk_id"])[0]
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
            if type(e) == user.App.vk_api.exceptions.ApiError:
                ee: VkApiError = e
                print(
                    type(e) == VkApiError,
                    e,
                    ee.code,
                    ee.error["error_msg"],
                )
                if ee.code == 30 and ee.error["error_msg"] == "This profile is private":
                    db_profile_del(user, res["id"])
                    user.state = State.SHOW
                    user.save()
                    return 0
                    # continue
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
        phs = sorted(phs, key=lambda x: x["likes"], reverse=True)[0 : min(3, len(phs))]
        phsl = list(map(lambda x: x.get("str"), phs))
        if not phsl:
            phsl = ["photo-233543845_457239066"]

        if res:
            kb = VkKeyboard(inline=True)
            kb.add_button(
                "Дальше",
                color=VkKeyboardColor.PRIMARY,
                payload={
                    "command": "set_state",
                    "state": State.SHOW,
                    "action": State.ACT_NEXT,
                    # "next": True,
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
                    "action": State.ACT_ADD_BL,
                    "delete": True,
                },
            )
            send_kb = kb.get_keyboard()

            write_msg(
                user,
                f"\n\n[https://vk.com/{res['domain']}|{profile['first_name']} {profile['last_name']}]\n{res['city']}, {int(res['age'])} {declension(int(res['age']), 'год', 'года', 'лет')}",
                keyboard=send_kb,
                attach=",".join(phsl),
            )
            user.save()
    return 1
    # break
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
    return 0
    # continue
