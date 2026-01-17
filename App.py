import vk_api
from tokens import TOKEN, APP_ID, AUTH_REDIRECT_URI
from vk_api.longpoll import VkLongPoll

# vk = vk_api.VkApi(token=TOKEN)
# vkapi = vk.get_api()

# Создаем доп. экземпляр для запросов от имени пользователя
# user_vk = None
# vkuserapi = None


class App:
    APP_ID = APP_ID
    AUTH_REDIRECT_URI = AUTH_REDIRECT_URI
    vk = vk_api.VkApi(token=TOKEN)
    vkapi = vk.get_api()
    longpoll = None
    # Создаем доп. экземпляр для запросов от имени пользователя
    user_vk = None
    vkuserapi = None

    @classmethod
    def init(cls):
        cls.longpoll = VkLongPoll(
            cls.vk,
            wait=1,
        )
