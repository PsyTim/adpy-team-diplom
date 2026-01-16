from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from random import randrange
from messages import del_msg, write_msg
from State import State


def edit(user, message_id, message, keyboard=None):
    pars = {
        "peer_id": user.vk_id,
        "message_id": message_id,
        "message": message,
        "random_id": randrange(10**7),
        "keyboard": keyboard,
    }

    res = user.App.vk.method(
        "messages.edit",
        pars,
    )


class Kb:
    pri = VkKeyboardColor.PRIMARY
    sec = VkKeyboardColor.SECONDARY
    pos = VkKeyboardColor.POSITIVE
    neg = VkKeyboardColor.NEGATIVE

    self: object = None

    @classmethod
    def check(cls, inline=None):
        if not cls.self or not inline is None:
            cls.new(inline)

    @classmethod
    def new(cls, inline=False):
        cls.self = Kb(inline)

    def __init__(self, inline=False):
        # print("init")
        self.self = self
        self.keyboard = VkKeyboard(False, inline)
        self.send_kb = self.keyboard.get_empty_keyboard()

    @classmethod
    def get(cls):
        new_lines = []
        cls.check()
        for i, l in enumerate(cls.self.keyboard.keyboard["buttons"]):
            if l:
                new_lines.append(l)
        cls.self.keyboard.keyboard["buttons"] = new_lines
        # print(new_lines)
        kb = cls.self.keyboard.get_keyboard()
        cls.self = None
        return kb

    @classmethod
    def add(
        cls,
        label,
        color=VkKeyboardColor.SECONDARY,
        state=None,
        delete=True,
        command=None,
        inline=None,
    ):
        cls.check(inline)
        payload = {}
        if state:
            payload["command"] = "set_state"
            payload["state"] = state
        if delete:
            payload["delete"] = True
        if label[0] == "\n":
            cls.nl()
        cls.self.keyboard.add_button(label, color, payload)
        if label[-1] == "\n":
            cls.nl()

    @classmethod
    def nl(cls):
        cls.self.keyboard.add_line()


def main_menu(user, menu_message=False):
    if menu_message:
        user.kb_id = write_msg(user, ".")
        return
    # Создание клавиатуры

    # send_kb = keyboard.get_empty_keyboard()
    if (
        user.state not in State.GETTING_ACCESS_TOKEN
        and user.state != State.FIND
        and user.state
        not in State.SET_AGE | State.SET_CITY | State.SET_GENDER | {State.FIND}
        # and user.filter_age_from
        # and user.filter_age_to
    ):
        if user.state in State.SET_FILTERS:
            Kb.add("Смотреть кандидатов", Kb.pri, State.SHOW)
        else:
            Kb.add("Условия подбора", Kb.sec, State.CHANGE_FILTERS)
        Kb.add("❤ Любимые анкеты", Kb.pos, State.SHOW_FAV)
        Kb.nl()
        Kb.add("⛔ Черный список", Kb.neg, State.SHOW_BL)
        Kb.add("Помощь", Kb.sec, State.HELP),
        Kb.add("Перезапуск", Kb.sec, State.RESTART),

    send_kb = Kb.get()
    # print(send_kb)
    edit(user, user.kb_id, "..", keyboard=send_kb)
    del_msg(user.kb_id, user.App.vk)
