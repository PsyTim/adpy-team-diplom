from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError as VkApiError

from messages import del_all, format_filters_msg, write_msg, declension, extend_message
import DB.profiles
from DB.profiles import (
    db_count_filter_fav,
    db_profile_del,
)
from State import State
from vk_auth import vk_refresh
from dlg_keyboard import Kb


def show(user):
    "Просмотр очередной анкеты в избранном и обработка действий с ней"
    # Количество анкет в избраном по текушим фильтрам
    cnt_filtered = db_count_filter_fav(user)["count"]
    # Обшее количество анкет в избраном
    cnt_total = DB.profiles.count_fav_total(user)["count"]
    cnt = cnt_total
    if cnt:
        # Если
        res = DB.profiles.get_fav(user)
        if user.action == State.ACT_NEXT:
            DB.profiles.set_viewed(user, res["id"])
            res = DB.profiles.get_fav(user)
        write_msg(user, str(res))
        user.App.user_vk, user.App.vkuserapi = vk_refresh(user, user.App.APP_ID)
        if not user.App.user_vk:
            user.state = State.NEED_ACCESS_TOKEN
            user.save()
            return
        profile = user.App.vkuserapi.users.get(user_ids=res["vk_id"])[0]
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
            if type(e) == VkApiError:
                ee: VkApiError = e
                print(
                    type(e) == VkApiError,
                    e,
                    ee.code,
                    ee.error["error_msg"],
                )
                if ee.code == 30 and ee.error["error_msg"] == "This profile is private":
                    print("delete")
                    db_profile_del(user, res["id"])
                    user.state = State.SHOW
                    user.save()
                    return
            print(type(e), e)
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

            if "msg_format" in locals():
                print("in_locals")
                del msg_format
            msg_format, msg = extend_message(
                "",
                "Вы просматриваете любимые анкеты\n",
                type="bold",
            )

            msg = f"{msg}\n\n[https://vk.com/{res['domain']}|{profile['first_name']} {profile['last_name']}]\n{res['city']}, {int(res['age'])} {declension(int(res['age']), 'год', 'года', 'лет')}"

            write_msg(
                user,
                msg,
                format=msg_format,
                keyboard=send_kb,
                attach=",".join(phsl),
            )
    else:
        Kb.add("Вернуться к просмотру кандидатов", Kb.pri, State.SHOW, inline=True)

        msg = "В избранном пусто"
        write_msg(
            user,
            msg,
            keyboard=Kb.get(),
        )

    return True
