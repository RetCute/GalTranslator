from yaml import safe_load
import os
from openai import OpenAI
import traceback
from time import sleep
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton, QMessageBox


class Manifest:
    module_name = "DeepSeek/ChatGPT(API)"
    author = "Retrocal"
    url = "https://github.com/RetCute/GalTranslator"
    description = "一个帮助你使用ChatGPT/DeepSeek来翻译的组件"

def openSettings():
    global window
    window = SettingsApp()
    window.show()

class Settings:
    apikey = None
    model = None
    api_base = None
    updateLog = None
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")

    @classmethod
    def loadCfg(cls, log=True):
        default_config = '''#GPT APIKEY
ApiKey: ""
#GPT模型名称
Model: "gpt3.5-turbo"
#API_Base 默认为openai的ChatGPT官方apibase 填写中转apibase可以不挂梯子 改成https://api.deepseek.com可以使用DeepSeek
Api_Base: "https://api.openai.com/v1"'''
        while True:
            try:
                if log:
                    cls.updateLog("Info", f"读取{Manifest.module_name}配置文件中....")
                config = safe_load(open(cls.cfg, 'r', errors='ignore', encoding="utf-8"))
                cls.apikey = config["ApiKey"]
                cls.model = config["Model"]
                cls.api_base = config["Api_Base"]
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
        config = f'''#GPT APIKEY
ApiKey: "{cls.apikey}"
#GPT模型名称
Model: "{cls.model}"
#API_Base 默认为openai的ChatGPT官方apibase 填写中转apibase可以不挂梯子 改成https://api.deepseek.com可以使用DeepSeek
Api_Base: "{cls.api_base}"'''
        open(cls.cfg, 'w', encoding="utf-8").write(config)

class SettingsApp(QWidget):
    def __init__(self, parent=None):
        super(SettingsApp, self).__init__(parent)
        Settings.loadCfg(log=False)
        self.setWindowTitle(f"{Manifest.module_name} Settings")
        self.resize(120, 110)
        self.layout = QVBoxLayout()
        self.label_apikey = QLabel("ApiKey")
        self.apikey = QLineEdit()
        self.label_model = QLabel("Model")
        self.model = QLineEdit()
        self.label_base = QLabel("ApiBaseUrl")
        self.apibase = QLineEdit()
        self.apibase.setText(Settings.api_base)
        self.model.setText(Settings.model)
        self.apikey.setText(Settings.apikey)
        self.layout.addWidget(self.label_apikey)
        self.layout.addWidget(self.apikey)
        self.layout.addWidget(self.label_model)
        self.layout.addWidget(self.model)
        self.layout.addWidget(self.label_base)
        self.layout.addWidget(self.apibase)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save)
        self.layout.addWidget(self.save_button)
        self.setLayout(self.layout)

    def save(self):
        Settings.apikey = self.apikey.text()
        Settings.model = self.model.text()
        Settings.api_base = self.apibase.text()
        Settings.writeCfg()
        QMessageBox.information(self, "保存成功", "保存成功,某些设置可能需要重启软件才能启用")
        Settings.loadCfg(log=False)

class Translator:
    def __init__(self, updatelog):
        Settings.updateLog = updatelog
        Settings.loadCfg()
        self.client = OpenAI(api_key=Settings.apikey, base_url=Settings.api_base)
        self.updateLog = updatelog
        self.messages = [
                    {"role": "system", "content": f"请将下面这段日文符合语气地优美地贴合原意地翻译为中文并且结合我消息记录的前几个句子进行翻译只给出翻译后的结果即可无需添加其他东西"},
                          ]
        self.running = True

    def translate(self, text):
        try:
            self.messages.append({"role": "user", "content": f"{text}"})
            response = self.client.chat.completions.create(
                model=f"{Settings.model}",
                messages=self.messages
            )
            translated_text = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": translated_text})
            return translated_text
        except Exception:
            self.updateLog("Error", traceback.format_exc())
            return "Error"