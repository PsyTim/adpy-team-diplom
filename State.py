class State:  # этапы диалога
    START = 0  # начало
    FIRST = 1  # после отправки приветственного сообщения
    SHOW = 2  # показать анкету
    MIN_AGE_NEED = 3  # Требуется установка фильтра минимального возраста
    MIN_AGE_INPUT = 4  # Ожидание ввода фильтра минимального возраста
    SHOW_FILTERS = 5  # показать условия подбора
    CHANGE_FILTERS = 6  # показать варианты изменения фильтров
    FILTERS_FINISH = 7
    MAX_AGE_NEED = 8
    MAX_AGE_INPUT = 9

    NEED_ACCESS_TOKEN = 10
    WAIT_ACCESS_TOKEN = 11

    GENDER_NEED = 12
    CHANGE_GENDER = 13

    FIND = 14
    FINDING = 15

    SHOW_FAV = 16  # показать анкету

    CITY_NEED = 17
    INPUT_CITY = 18
    CHANGE_CITY = 19

    ACT_CLEAR_BL = 1
    ACT_NEXT = 2
    ACT_AGAIN = 3
    ACT_TO_BL = 4
    ACT_TO_FAV = 5

    GETTING_ACCESS_TOKEN = {NEED_ACCESS_TOKEN, WAIT_ACCESS_TOKEN}
    SET_FILTERS = {
        SHOW_FILTERS,
        CHANGE_FILTERS,
        MIN_AGE_INPUT,
        MIN_AGE_NEED,
        MAX_AGE_NEED,
        MAX_AGE_INPUT,
    }
    SET_MIN_AGE = {MIN_AGE_NEED, MIN_AGE_INPUT}
    SET_MAX_AGE = {MAX_AGE_NEED, MAX_AGE_INPUT}
