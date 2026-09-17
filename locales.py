import json
import pathlib

class Locale:
    LOCALES: dict[str, str] = {}
    DEFAULT = "404"
    DEFAULT_PATH = pathlib.Path("locales.json") # place here everystring that be presented to user

    @classmethod
    def loadLocales(cls, path = DEFAULT_PATH):
        try:
            with open(path, "r", encoding="UTF-8") as f:
                cls.LOCALES = json.loads(f.read())
                print("Loaded locales")
                return True
        except Exception as e: print(e)
        return False

    @classmethod
    def getLocale(cls, key):
        return cls.LOCALES.get(key, cls.DEFAULT)

    @classmethod
    def getFormatted(cls, key, **kwargs):
        return cls.getLocale(key).format(**kwargs)
    
    @classmethod
    def get(cls, key, **kwargs): # to type less smh ts
        return cls.getFormatted(key, **kwargs)