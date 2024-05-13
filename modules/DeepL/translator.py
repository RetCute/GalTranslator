import deepl
from yaml import safe_load
import os
import traceback
from time import sleep
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton, QMessageBox


class Manifest:
    module_name = "DeepL"
    author = "Retrocal"
    url = "https://github.com/RetCute/GalTranslator"
    description = "一个帮助你使用DeepL来翻译的组件"

def openSettings():
    global window
    window = SettingsApp()
    window.show()

class Settings:
    authkey = None
    serverurl = None
    updateLog = None
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")

    @classmethod
    def loadCfg(cls, log=True):
        default_config = '''# DeepL AuthKey
AuthKey: "Put your authkey here if you enable deeplapi"
#DeepL Server Url 若为Pro则填https://api.deepl-pro.com Free保持默认
ServerUrl: "https://api-free.deepl.com"'''
        while True:
            try:
                if log:
                    cls.updateLog("Info", f"读取{Manifest.module_name}配置文件中....")
                config = safe_load(open(cls.cfg, 'r', errors='ignore', encoding="utf-8"))
                cls.authkey = config["AuthKey"]
                cls.serverurl = config["ServerUrl"]
                if log:
                    cls.updateLog("Info", "成功!")
                break
            except Exception as e:
                if log:
                    cls.updateLog("Error", f"加载{Manifest.module_name}配置文件失败,写入默认配置中....")
                open(cls.cfg, 'w', encoding="utf-8").write(default_config)
                sleep(2)

    @classmethod
    def writeCfg(cls):
        config = f'''# DeepL AuthKey
AuthKey: "{cls.authkey}"
#DeepL Server Url 若为Pro则填https://api.deepl-pro.com Free保持默认
ServerUrl: "{cls.serverurl}"'''
        open(cls.cfg, 'w', encoding="utf-8").write(config)

class SettingsApp(QWidget):
    def __init__(self, parent=None):
        super(SettingsApp, self).__init__(parent)
        Settings.loadCfg(log=False)
        self.setWindowTitle(f"{Manifest.module_name} Settings")
        self.resize(120, 80)
        self.layout = QVBoxLayout()
        self.label_apikey = QLabel("AuthKey")
        self.apikey = QLineEdit()
        self.label_model = QLabel("Server Url")
        self.model = QLineEdit()
        self.model.setText(Settings.authkey)
        self.apikey.setText(Settings.serverurl)
        self.layout.addWidget(self.label_apikey)
        self.layout.addWidget(self.apikey)
        self.layout.addWidget(self.label_model)
        self.layout.addWidget(self.model)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save)
        self.layout.addWidget(self.save_button)
        self.setLayout(self.layout)

    def save(self):
        Settings.authkey = self.apikey.text()
        Settings.serverurl = self.model.text()
        Settings.writeCfg()
        QMessageBox.information(self, "保存成功", "保存成功,某些设置可能需要重启软件才能启用")

class Translator:
    def __init__(self, updatelog):
        self.running = False
        self.updateLog = updatelog
        Settings.updateLog = updatelog
        Settings.loadCfg()
        self.translator = deepl.Translator(auth_key=Settings.authkey, server_url=Settings.serverurl)
        self.running = True

    def translate(self, text):
        try:
            return self.translator.translate_text(text, target_lang="zh").text
        except Exception:
            self.updateLog("Error", traceback.format_exc())
            return "Error"