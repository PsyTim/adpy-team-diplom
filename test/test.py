import unittest

from DB import create
from User import User


class TestRecreateTables(unittest.TestCase):

    def test_recreate_tables(self, skip=True):
        # skip = False
        self.skipTest("skip tables (re)creation") if skip else ...
        create.recreate_tables()
        self.assertTrue(True)

    def test_recreate_and_fill_autorization_code(self, skip=True, add_fill={}):
        skip = False
        user = User(58174828)
        refresh_token = (
            user.refresh_token
            if user.refresh_token
            else "vk2.a.0_w2nEXumTXE0gbdD5mnE0fOET9-SE6xUulyUggMS9i3OV7ZnXc_sEpFyu72YfPFNuabCstzfq5_6311jfjGXuxgqMdByaPPLjVIcUW69_aLJ8tzlx4oz0wKubgJ4Or5ki5Dy78zTxaNS2TjIMw1lddTdXnDbe9lITzyd0WgpnnbhskT7tjap0HnK-xhxKa1KFq8p1zAhEHlzpQkg5BQ4kADby6Hwe0jMEkGqfTxHEU"
        )
        device_id = (
            user.device_id
            if user.device_id
            else "ymY4i4XRJfsmcRX7R2IxWJeqG55dWImhv2pTfhB2E0pr_ZylFjnYQWsu7JEF3q66oEIyvg-wK0eNxp6iLZQvyw"
        )
        self.skipTest("skip tables (re)creation") if skip else ...
        self.test_recreate_tables(skip=False)
        user = User(58174828)
        #                     vk2.a.5UqbLYyhPc_KtNWFxVuPrQdMwegk1yyyHDjLVeX3dOO-_677B1J9PjeLXQnRF-2n5chmNe3biVN2_QPMlG0WDauJSfX3iSHCKviJg395pzn2VeaH5DiDfwXZqCP0vozDeKA3dTnKNNsWIFrG-fy4aoxEIJJY5gHAj8yjmdn9XdeRXM9Q55CfNFRmvZA6uVB_fIeljh2H39uvuemeeKcdwooplw5jLizNdFfdxeCPjjs"
        user.refresh_token = refresh_token
        user.device_id = device_id
        print(len(user.code_verifier))
        add = add_fill.copy()
        for key, val in add.items():
            print(key, val)
            setattr(user, key, str(val))
        user.save()
        self.assertTrue(True)

    def test_recreate_and_fill_age(self, skip=True, add_fill={}):
        skip = False
        self.skipTest("skip tables (re)creation") if skip else ...
        add = add_fill.copy()
        add |= {"birthday": "1977-03-16"}
        print(add)
        self.test_recreate_and_fill_autorization_code(skip=False, add_fill=add)
        self.assertTrue(True)

    def test_recreate_and_fill_city(self, skip=True):
        skip = False
        self.skipTest("skip tables (re)creation") if skip else ...
        self.test_recreate_and_fill_age(
            skip=False, add_fill={"city_id": 1, "city": "Оренбург"}
        )
        self.assertTrue(True)
