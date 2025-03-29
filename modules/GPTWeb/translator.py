from yaml import safe_load
import os
import traceback
from time import sleep
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
import undetected_chromedriver
from selenium.webdriver.common.keys import Keys
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, \
    QHBoxLayout, QFileDialog

class Manifest:
    module_name = "ChatGPT Web"
    author = "Retrocal"
    url = "https://github.com/RetCute/GalTranslator"
    description = "Use selenium to connect to chrome and translate text with ChatGPT"

def openSettings():
    global window
    window = SettingsApp()
    window.show()

class Settings:
    bp = None
    updateLog = None
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")

    @classmethod
    def loadCfg(cls, log=True):
        default_config = '''# Google浏览器的文件地址
Browser_Path: ""'''
        while True:
            try:
                if log:
                    cls.updateLog("Info", f"读取{Manifest.module_name}配置文件中....")
                config = safe_load(open(cls.cfg, 'r', errors='ignore', encoding="utf-8"))
                cls.bp = config["Browser_Path"]
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
        config = f'''# Google浏览器的文件地址
Browser_Path: "{cls.bp}"'''
        open(cls.cfg, 'w', encoding="utf-8").write(config)

class SettingsApp(QWidget):
    def __init__(self, parent=None):
        super(SettingsApp, self).__init__(parent)
        Settings.loadCfg(log=False)
        self.setWindowTitle(f"{Manifest.module_name} Settings")
        self.resize(120, 50)
        self.layout = QVBoxLayout()
        self.label_msg1 = QLabel("Chrome浏览器文件地址")
        self.path1 = QLineEdit()
        self.path1.setText(Settings.bp)
        self.browse = QPushButton("选取")
        self.browse.clicked.connect(lambda: self.open_file_dialog("Select Chrome.exe", self.path1))
        topLayout1 = QHBoxLayout()
        topLayout1.addWidget(self.path1)
        topLayout1.addWidget(self.browse)
        self.layout.addWidget(self.label_msg1)
        self.layout.addLayout(topLayout1)
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save)
        self.layout.addWidget(self.save_button)
        self.setLayout(self.layout)

    def open_file_dialog(self, msg, path):
        file_path, _ = QFileDialog.getOpenFileName(self, msg)
        if file_path:
            path.setText(file_path)

    def save(self):
        Settings.bp = self.path1.text()
        Settings.writeCfg()
        QMessageBox.information(self, "保存成功", "保存成功,某些设置可能需要重启软件才能启用")
        Settings.loadCfg(log=False)

class webTranslatorThread(QThread):

    def __init__(self, translator, updatelog):
        super().__init__()
        self.translator = translator
        self.updateLog = updatelog

    def run(self):
        try:
            self.updateLog("Info", "初始化ChatGPT Web中....")
            options = undetected_chromedriver.ChromeOptions()
            self.translator.driver = undetected_chromedriver.Chrome(options=options, browser_executable_path=Settings.bp)
            self.translator.driver.get("https://chat.openai.com/")
            wait = WebDriverWait(self.translator.driver, timeout=100)
            wait.until(EC.url_contains("https://auth.openai.com/authorize"))
            self.updateLog("Info", " 等待登陆中...")
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "group")))
            txtbox = self.translator.driver.find_element(By.ID, "prompt-textarea")
            txtbox.send_keys("请将下列我给出的日文符合语气地优美地贴合原意地并结合我消息记录的前几个句子翻译为中文只给出翻译后的结果即可无需添加其他东西，括号前面或者冒号前可能为人名结合语境不要翻译成其他的,如果表达的为人说的话记得加:")
            send_button = self.translator.driver.find_element(By.CSS_SELECTOR, '[data-testid="send-button"]')
            send_button.click()
            self.updateLog("Info", "Translator初始化成功")
            self.translator.running = True
        except Exception:
            self.updateLog("Error", "Translator初始化失败:")
            self.updateLog("", traceback.format_exc())

class Translator:
    def __init__(self, updatelog):
        self.driver = None
        self.running = False
        self.updateLog = updatelog
        if not os.path.exists("chromedriver.exe"):
            self.updateLog("Error", "未找到chromedriver 请下载对应版本的driver丢到目录下 或者切换其他翻译方式")
        else:
            Settings.updateLog = updatelog
            Settings.loadCfg()
            self.init_thread = webTranslatorThread(self, updatelog)
            self.init_thread.start()

    def translate(self, text):
        self.ask(text)
        return self.getLastReply()

    def ask(self, text):
        global display
        txtbox = self.driver.find_element(By.ID, "prompt-textarea")
        txtbox.send_keys(text)
        send_button = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="send-button"]')
        send_button.click()
        try:
            WebDriverWait(self.driver, timeout=10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".result-streaming")))
        except:
            pass

    def getLastReply(self, timeout=20):
        t = 0
        while self.driver.find_elements(By.CSS_SELECTOR, ".result-streaming") != []:
            if t >= timeout:
                return "Timeout!"
            sleep(0.5)
            t += 0.5
        ReplyList = self.getReplyList()
        reply = ReplyList[-1].text
        return reply

    def getReplyList(self):
        return self.driver.find_elements(By.CSS_SELECTOR, ".markdown")
