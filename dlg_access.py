from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.exceptions import ApiError as VkApiError

from messages import del_all, write_msg
from State import State
from vk_auth import vk_auth_link


def get(user):
    del_all(user)
    kb = VkKeyboard(inline=True)
    kb.add_openlink_button(
        "Разрешить доступ",
        vk_auth_link(
            user.App.APP_ID,
            user.App.AUTH_REDIRECT_URI,
            code_verifier=user.code_verifier,
        ),
    )
    kb.add_button(
        "Продолжить",
        color=VkKeyboardColor.POSITIVE,
        payload={"command": "auth_continue"},
    )
    write_msg(
        user,
        "Для поиска анкет в контакте нажмите на кнопку чтобы разрешить доступ",
        keyboard=kb.get_keyboard()
    )
    user.state = State.WAIT_ACCESS_TOKEN
    user.save()
    return 1


def wait(user):
    if not user.refresh_token:
        user.state = State.NEED_ACCESS_TOKEN
    else:
        del_all(user)
        user.state = State.SHOW
        user.save()
        return
    user.state = State.NEED_ACCESS_TOKEN
    user.save()
    return
