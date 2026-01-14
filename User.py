from DB.user import db_get_user, db_update_user


class User:

    def __init__(self, uid=None, fetch=True):
        if uid is None:
            if hasattr(self, "vk_id"):
                uid = self.vk_id
            else:
                raise Exception("Error id")
        if fetch:
            self._data, self.is_new = db_get_user(uid)
        else:
            self.is_new = True
            self._data = {"vk_id": uid}
        self._fieldset = set(self._data)
        self._fieldlist = list(self._data)
        for key, value in self._data.items():
            self.__setattr__(key, value)

    def get_changes(self):
        changes = []
        for key in self._fieldlist:
            if self.__getattribute__(key) != self._data[key]:
                changes.append(
                    {
                        "key": key,
                        "val": self.__getattribute__(key),
                        "old": self._data[key],
                    }
                )
        return changes

    def save(self, update=True):
        changes = self.get_changes()
        if changes:
            print(f"{changes=}")
            db_update_user(self.vk_id, changes)
            if update:
                for c in changes:
                    self._data[c["key"]] = c["val"]

    def add_to_del(self, message_id):
        if not self.to_del:
            self.to_del = ""

        self.to_del = (
            ",".join((self.to_del.split(",") + [str(message_id)]))
            if self.to_del
            else str(message_id)
        )
