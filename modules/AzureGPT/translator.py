from yaml import safe_load
import os
from openai import AzureOpenAI
import traceback
from time import sleep
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton, QMessageBox


class Manifest:
    module_name = "AzureGPT"
    author = "Retrocal"
    url = "https://github.com/RetCute/GalTranslator"
    description = "一个帮助你使用GPTAPI(Azure)来翻译的组件"

def openSettings():
    global window
    window = SettingsApp()
    window.show()

class Settings:
    apikey = None
    endpoint = None
    api_version = None
    depoly_name = None
    updateLog = None
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")

    @classmethod
    def loadCfg(cls, log=True):
        default_config = '''#资源的APIKEY
ApiKey: ""
#资源的Endpoint
Endpoint: ""
#API版本
API_Version: ""
#所部署的模型名称(你创建时自己填写的)
Deploy_Name: ""'''
        while True:
            try:
                if log:
                    cls.updateLog("Info", f"读取{Manifest.module_name}配置文件中....")
                config = safe_load(open(cls.cfg, 'r', errors='ignore', encoding="utf-8"))
                cls.apikey = config["ApiKey"]
                cls.endpoint = config["Endpoint"]
                cls.api_version = config["API_Version"]
                cls.depoly_name = config["Deploy_Name"]
                if log:
                    cls.updateLog("Info", "成功!")
                break
            except:
                if log:
                    cls.updateLog("Error", f"加载{Manifest.module_name}配置文件失败,写入默认配置中....")
                open(cls.cfg, 'w', encoding="utf-8").write(default_config)
                sleep(2)

    @classmethod
    def writeCfg(cls):
        config = f'''#资源的APIKEY
ApiKey: "{cls.apikey}"
#资源的Endpoint
Endpoint: "{cls.endpoint}"
#API版本
API_Version: "{cls.api_version}"
#所部署的模型名称(你创建时自己填写的)
Deploy_Name: "{cls.depoly_name}"'''
        open(cls.cfg, 'w', encoding="utf-8").write(config)

class SettingsApp(QWidget):
    def __init__(self, parent=None):
        super(SettingsApp, self).__init__(parent)
        Settings.loadCfg(log=False)
        self.setWindowTitle(f"{Manifest.module_name} Settings")
        self.resize(120, 150)
        self.layout = QVBoxLayout()
        self.label_apikey = QLabel("APIKey")
        self.apikey = QLineEdit()
        self.label_ep = QLabel("Endpoint")
        self.ep = QLineEdit()
        self.label_av = QLabel("API Version")
        self.av = QLineEdit()
        self.label_model = QLabel("部署名")
        self.model = QLineEdit()
        self.model.setText(Settings.depoly_name)
        self.apikey.setText(Settings.apikey)
        self.av.setText(Settings.api_version)
        self.ep.setText(Settings.endpoint)
        self.layout.addWidget(self.label_apikey)
        self.layout.addWidget(self.apikey)
        self.layout.addWidget(self.label_ep)
        self.layout.addWidget(self.ep)
        self.layout.addWidget(self.label_av)
        self.layout.addWidget(self.av)
        self.layout.addWidget(self.label_model)
        self.layout.addWidget(self.model)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save)
        self.layout.addWidget(self.save_button)
        self.setLayout(self.layout)

    def save(self):
        Settings.apikey = self.apikey.text()
        Settings.endpoint = self.ep.text()
        Settings.api_version = self.av.text()
        Settings.depoly_name = self.model.text()
        Settings.writeCfg()
        QMessageBox.information(self, "保存成功", "保存成功,某些设置可能需要重启软件才能启用")

class Translator:
    def __init__(self, updatelog):
        self.running = False
        Settings.updateLog = updatelog
        Settings.loadCfg()
        self.client = AzureOpenAI(api_key=Settings.apikey, api_version=Settings.api_version, azure_endpoint=Settings.endpoint)
        self.updateLog = updatelog
        self.messages = [
                    {"role": "system", "content": f"请将下面这段日文符合语气地优美地贴合原意地翻译为中文并且结合我消息记录的前几个句子进行翻译只给出翻译后的结果即可无需添加其他东西"},
                          ]
        self.running = True

    def translate(self, text):
        try:
            self.messages.append({"role": "user", "content": f"{text}"})
            response = self.client.chat.completions.create(
                model=f"{Settings.depoly_name}",
                messages=self.messages
            )
            translated_text = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": translated_text})
            return translated_text
        except Exception:
            self.updateLog("Error", traceback.format_exc())
            return "Error"