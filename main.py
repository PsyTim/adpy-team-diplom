from datetime import datetime
from db.database import session
from db.models import Users, Profiles, UserProfiles, Favorites
import random
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from pprint import pprint

TOKEN_APP = ''
USER_TOKEN = ''

vk_session = vk_api.VkApi(token=TOKEN_APP)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

user_vk = vk_api.VkApi(token=USER_TOKEN)
vk_user_api = user_vk.get_api()

profile_num = 0
favourites = []

keyboard = VkKeyboard(one_time=False)
keyboard.add_button('Начать поиск', color=VkKeyboardColor.POSITIVE)
keyboard.get_keyboard()

def write_msg(user_id, message, keyboard=None):
    vk_session.method('messages.send', {'user_id': user_id, 'message': message,  'random_id': random.randrange(10 ** 7), 'keyboard': keyboard})

def send_photo(user_id, attachment):
    vk_session.method('messages.send', {'user_id': user_id,  'random_id': random.randrange(10 ** 7), 'attachment': attachment})

def info_user(user_id):
    response_name_domain = vk.users.get(user_ids=user_id, fields='first_name,last_name,sex,city,domain,sex,bdate')

    return response_name_domain


def peoples(information, sex, min_year, max_year):

    # pprint(information, indent=4)
    city_id = information['city']['id']
    now_year = datetime.now().year
    min_year_ = now_year - max_year
    max_year_ = now_year - min_year
    years_range = range(min_year_, max_year_ + 1)

    session.query(Profiles).filter(Profiles.vk_id == user_id).update({'city': information['city']['title'], 'birthday': information['bdate']})
    session.commit()

    selection_of_people = vk_user_api.users.search(sort=1, has_photo=1, friend_status=0, online_mobile=1, count=100, status=6, sex=sex, city=city_id, birth_year=years_range, fields='city, domain, bdate, photo_max_orig, sex')

    profiles_list_full = []
    for index, profile in enumerate(selection_of_people['items']):
        if profile['is_closed'] == False:
            photos = vk_user_api.photos.get(owner_id=profile['id'], album_id='profile', rev=1, extended=1)
            if len(photos['items']) > 2:
                sorted_photos = sorted(photos['items'], key=lambda photo: photo['likes']['count'], reverse=True)
                top_3_photos = [sorted_photos[0]['owner_id'], sorted_photos[0]['id'], sorted_photos[1]['id'], sorted_photos[2]['id']]
                profiles_list = top_3_photos + [f'- {profile['first_name']} {profile['last_name']}\n- https://vk.com/id{profile['id']}\nЛучшие фотографии:']
                profiles_list_full.append(profiles_list)

                session.add(Users(vk_id=profile['id'], gender=sex, birthday=profile['bdate'], city_id=city_id, city=information['city']['title'], filter_age_from=max_year, filter_age_to=min_year, filter_gender=sex_str))
                session.commit()

    return profiles_list_full

def profiles_and_photo(profiles_list):
    write_msg(event.user_id, profiles_list[4])
    attachments = [f'photo{profiles_list[0]}_{profiles_list[i]}' for i in range(1,4)]
    send_photo(event.user_id, attachment=','.join(attachments))



for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:

        if event.to_me:
            request = event.text
            user_id = event.user_id
            try:
                if request == "Начать" or request == "Начать поиск":

                    profile_num = 0
                    keyboard2 = VkKeyboard(one_time=True)
                    keyboard2.add_button('М', color=VkKeyboardColor.PRIMARY)
                    keyboard2.add_button('Ж', color=VkKeyboardColor.NEGATIVE)
                    keyboard2.get_keyboard()

                    session.add(Profiles(vk_id=user_id))
                    session.commit()

                    write_msg(user_id, "Выберите пол: М|Ж", keyboard=keyboard2.get_keyboard())

                elif request == "М":
                    sex = 2
                    sex_str = 'М'
                    write_msg(user_id, "Выберите минимальный возраст:")
                elif request == "Ж":
                    sex = 1
                    sex_str = 'Ж'
                    write_msg(user_id, "Выберите минимальный возраст:")

                elif request == "Далее" and profile_num > 0:
                    if len(profiles_list_full) >= profile_num:
                        profiles_and_photo(profiles_list_full[profile_num])
                        profile_num += 1
                    else:
                        profile_num = 0
                        profiles_and_photo(profiles_list_full[profile_num])

                elif request == 'В избранное!':
                    try:
                        favourit_user = f'{profiles_list_full[profile_num - 1][4]}'[:-18]
                        favourites.append(favourit_user)
                        # pprint(profiles_list_full, indent=4)
                        session.add(Favorites(profile_id=user_id, favorite_id=profiles_list_full[profile_num][0], favorite_info=favourit_user))
                        session.commit()

                        write_msg(user_id, "Пользователь успешно добавлен!")
                    except NameError:
                        write_msg(user_id, 'Нажмите "Начать поиск" и найдите хотя бы одного пользователя, чтобы добавить в избранное.')

                elif request == 'Любимчики':
                    result = ''
                    for profile in favourites:
                        result += f'{profile}\n'
                    if result != '':
                        write_msg(user_id, message=result)
                    else:
                        write_msg(user_id, 'Список избранных пуст :(')

                elif isinstance(int(request), int) and 'sex' in locals() and 'min_year' not in locals():
                    min_year = int(request)
                    write_msg(user_id, "Выберите максимальный возраст:")

                elif isinstance(int(request), int) and 'min_year' in locals():

                    keyboard_1 = VkKeyboard(one_time=False)
                    keyboard_1.add_button('Далее', color=VkKeyboardColor.POSITIVE)
                    keyboard_1.add_button('В избранное!', color=VkKeyboardColor.NEGATIVE)
                    keyboard_1.add_line()
                    keyboard_1.add_button('Начать поиск', color=VkKeyboardColor.PRIMARY)
                    keyboard_1.add_button('Любимчики', color=VkKeyboardColor.NEGATIVE)
                    keyboard_1.get_keyboard()

                    write_msg(user_id, "Уже ищу самых красивых людей! Секундочку...", keyboard=keyboard_1.get_keyboard())
                    max_year = int(request)
                    information = info_user(user_id)[0]
                    profiles_list_full = peoples(information, sex, min_year, max_year)
                    profiles_and_photo(profiles_list_full[profile_num])
                    profile_num += 1

                    del min_year, max_year

                else:
                    write_msg(user_id, "Не поняла вашего ответа...")
            except ValueError:
                write_msg(user_id, 'Нажмите "Начать поиск" и найдите хотя бы одного пользователя.')