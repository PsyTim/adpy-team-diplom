from State import State
from dlg_keyboard import Kb
from messages import write_msg, format_filters_msg, extend_message
import DB.profiles


def clean(user):
    s_tot = str(total := DB.profiles.count_blacklisted(user))
    s_cnt = str(cnt := DB.profiles.count_filter_blacklisted(user))

    if user.action == State.ACT_CLEAN_BL:
        DB.profiles.clean_bl(user)
        # user.state = State.CLEAN_BL
        user.actoion = None
        return
    elif user.action == State.ACT_CLEAN_BL_ALL:
        DB.profiles.clean_bl_all(user)
        user.state = State.SHOW
        return

    frm, msg = extend_message("", '\nОчистить "Черный список?"')

    if cnt == total or not cnt:
        Kb.add(
            f"Очистить",
            Kb.neg,
            State.CLEAN_BL,
            State.ACT_CLEAN_BL_ALL,
            inline=True,
        )
        msg += "\nПрофилей: "
        frm, msg = extend_message(msg, f"{s_tot}", frm)
    else:
        Kb.add(s_cnt, Kb.neg, State.CLEAN_BL, State.ACT_CLEAN_BL, inline=True)
        Kb.add(f"Весь ({s_tot})", Kb.neg, State.CLEAN_BL, State.ACT_CLEAN_BL_ALL)

        if user.action == State.ACT_HLP:
            msg += '\nУ вас в "Чёрном списке" профилей: '
            frm, msg = extend_message(msg, s_tot, frm)
            msg += f"\nМожно очистить его полностью, нажав кнопку "
            frm, msg = extend_message(msg, f"[  Весь ({s_tot})  ]", frm)
            msg += "\nА можно удалить только те профили, что соответствуют текущим условиям поиска, их "
            frm, msg = extend_message(msg, s_cnt, frm)
            msg += f", нажав кнопку "
            frm, msg = extend_message(msg, f"[  {s_cnt}  ]", frm)
            msg += "\n\nПосле очистки все удалённые из Черного списка анкеты вновь будут достуаны для просмотра."
        else:
            Kb.add("\nПомощь", Kb.sec, State.CLEAN_BL, State.ACT_HLP)
            msg += "\nПрофилей: "
            frm, msg = extend_message(msg, s_cnt, frm)
            msg += "🔎 /"
            frm, msg = extend_message(msg, f" {s_tot} ", frm)
        msg += "\n🔍 " + format_filters_msg(user, None)

    Kb.add("\nОтмена", Kb.pri, State.SHOW_BL)
    send_kb = Kb.get()
    write_msg(user, msg, send_kb, frm)
    return 1

    user.state = State.SHOW


def show(user):

    s_tot = str(total := DB.profiles.count_blacklisted(user))
    s_cnt = str(cnt := DB.profiles.count_filter_blacklisted(user))

    Kb.add("Дальше", Kb.pri, State.SHOW_BL, inline=True)
    #        "action": State.ACT_NEXT,
    Kb.add("❤️ Вернуть", Kb.sec, State.CHANGE_FILTERS)
    Kb.add("\nВсе (123)", Kb.pos, State.SHOW_BL)
    Kb.add("Очистить", Kb.neg, State.CLEAN_BL)
    # Kb.add("По условиям (33)", Kb.sec, State.HELP)

    send_kb = Kb.get()

    # kb.add_button(
    #     "❤️",
    #     color=VkKeyboardColor.POSITIVE,
    #     payload={
    #         "command": "set_state",
    #         "state": State.SHOW,
    #         "action": State.ACT_TO_FAV,
    #         "delete": True,
    #     },
    # )
    # kb.add_button(
    #     "➡️🗑",
    #     color=VkKeyboardColor.NEGATIVE,
    #     payload={
    #         "command": "set_state",
    #         "state": State.SHOW,
    #         "action": State.ACT_ADD_BL,
    #         "delete": True,
    #     },
    # )
    # send_kb = kb.get_keyboard()

    write_msg(
        user,
        "Просмотр Чс",
        #        f"\n\n[https://vk.com/{res['domain']}|{profile['first_name']} {profile['last_name']}]\n{res['city']}, {int(res['age'])} {declension(int(res['age']), 'год', 'года', 'лет')}",
        keyboard=send_kb,
        # attach=",".join(phsl),
    )
    return 1
