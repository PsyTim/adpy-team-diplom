import pkce
from urllib.parse import urlencode
from random import randrange
import hashlib, base64
import requests
import State
import vk_api


def generate_code_verifier():
    return pkce.generate_code_verifier(64)


def vk_auth():
    code_verifier, code_challenge = pkce.generate_pkce_pair()
    pkce.generate_code_verifier()
    print(code_verifier, code_challenge)

    return (
        code_verifier,
        code_challenge,
    )


def gen_state(v, uid):
    return uid + "_" + pkce.get_code_challenge(v + v)


def vk_auth_link(app_id, uri, code_verifier="*" * 64, id="58174828"):
    code_challenge = pkce.get_code_challenge(code_verifier)
    state = id + "_" + pkce.get_code_challenge(code_verifier + code_verifier)
    link = (
        f"https://id.vk.ru/authorize?client_id={id}"
        # f"&redirect_uri={urlencode(uri)}"
        "https%3A%2F%2Fauth.localhost%2F"
        "&state=optional_random_string_CTdciWfh2lh"
        "&response_type=code&code_challenge=3IIljUIht5Rk7C5hjR05-C4q028apKqytHHILubDjkM&code_challenge_method=S256&display=page&vk_platform=standalone"
    )
    print(link)

    pars = {
        "client_id": app_id,
        "redirect_uri": uri,
        "state": state,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        # "display": "page",
        # "vk_platform": "standalone",
    }
    link = "https://id.vk.ru/authorize?" + urlencode(pars)
    return link


def vk_refresh(user, APP_ID):
    url = "https://id.vk.ru/oauth2/auth"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "refresh_token",
        "refresh_token": user.refresh_token,
        "device_id": user.device_id,
        "client_id": APP_ID,
        # "redirect_uri": "https://xqmtsvml-8899.euw.devtunnels.ms/auth",
        # "code": qs["code"][0],
        "code_verifier": user.code_verifier,
        "state": gen_state(user.code_verifier, str(user.vk_id)),
    }

    response = requests.post(
        url, headers=headers, params=data, data=data
    )  # данные как form-data
    r_j = response.json()
    from pprint import pprint

    pprint(r_j)
    # print(r_j.get("error"))
    if r_j.get("error") in ("invalid_grant", "invalid_request"):
        return None, None
    user.access_token = r_j["access_token"]
    user.refresh_token = r_j["refresh_token"]
    user.save()
    # print(type(json))
    # print(str(json["user_id"]) == str(uid))
    # print(json["state"] == gen_state())
    # print(len(r_j["access_token"]))
    # print(len(json["refresh_token"]))
    user_vk = vk_api.VkApi(token=r_j["access_token"])
    vkuserapi = user_vk.get_api()
    return user_vk, vkuserapi


if __name__ == "__main__":
    import tokens
    from tokens import APP_ID, AUTH_REDIRECT_URI

    vk_auth_link(APP_ID, AUTH_REDIRECT_URI)
