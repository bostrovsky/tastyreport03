import os
import requests

def get_tastytrade_api_config():
    env = os.environ.get("TT_API_ENV", "prod").lower()
    if env == "sandbox":
        return {
            "base_url": os.environ["TT_SANDBOX_API_BASE_URL"],
            "username": os.environ["TT_SANDBOX_API_USERNAME"],
            "password": os.environ["TT_SANDBOX_API_PASSWORD"],
            "env": "sandbox",
        }
    else:
        return {
            "base_url": os.environ["TT_API_BASE_URL"],
            "username": os.environ["TT_API_USERNAME"],
            "password": os.environ["TT_API_PASSWORD"],
            "env": "prod",
        }

def tastytrade_login(username=None, password=None, base_url=None):
    config = get_tastytrade_api_config()
    url = (base_url or config["base_url"]).rstrip("/") + "/sessions"
    data = {
        "login": username or config["username"],
        "password": password or config["password"],
    }
    resp = requests.post(url, json=data)
    try:
        resp.raise_for_status()
    except Exception as e:
        return {"success": False, "error": str(e), "response": resp.text}
    return resp.json()

def get_environment_for_user(user):
    return 'sandbox' if user.is_superuser else 'prod'
