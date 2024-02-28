import win32net
import ntsecuritycon


if __name__ == "__main__":
    win32net.NetUserAdd("FELIX.local", 1, {"name": "tist",
                                           "password": "QWERTY123456",
                                           "password_age": 0,
                                           "priv": 0,
                                           "home_dir": None,
                                           "comment": "tist user"})
