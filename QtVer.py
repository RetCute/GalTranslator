from yaml import safe_load
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
from PyQt5 import QtCore, QtGui
import sys
from PIL import Image, ImageGrab, ImageEnhance
from time import sleep
from openai import OpenAI
import keyboard
from threading import Thread
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
import undetected_chromedriver
from selenium.webdriver.common.keys import Keys
from paddleocr import PaddleOCR
import deepl

running = False

class apitranslator:
    def __init__(self):
        self.client = OpenAI(api_key=Settings.apikey)

    def translate(self, text):
        try:
            response = self.client.chat.completions.create(
                model=f"{Settings.model}",
                messages=[
                    {"role": "system", "content": f"You are a translator who specialize in Japanese to Chinese translation"},
                    {"role": "user", "content": f"{text}"}
                          ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return str(e)

class webtranslator:
    def __init__(self):
        print("初始化ChatGPT中....")
        print("请在100s内登录你的ChatGPT账号")
        self.reply_cnt = 0
        options = undetected_chromedriver.ChromeOptions()
        self.driver = undetected_chromedriver.Chrome(options=options)
        self.driver.get("https://chat.openai.com/auth/login")
        WebDriverWait(self.driver, timeout=100).until(EC.url_to_be("https://chat.openai.com/"))
        print("初始化成功")

    def translate(self, text):
        self.ask("请将这段日文符合语气地优美地贴合原意地翻译为中文只给出翻译后的结果即可无需添加其他东西" + text)
        return translator.getLastReply()

    def ask(self, text):
        global display
        txtbox = self.driver.find_element(By.ID, "prompt-textarea")
        txtbox.send_keys(text)
        txtbox.send_keys(Keys.ENTER)
        try:
            WebDriverWait(self.driver, timeout=10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".result-streaming")))
        except:
            display.update_subtitle("Timeout Error")

    def getLastReply(self, timeout=20):
        reply = ""
        t = 0
        while self.driver.find_elements(By.CSS_SELECTOR, ".result-streaming") != []:
            if t >= timeout:
                return "Timeout!"
            sleep(1)
            t += 1
        ReplyList = self.getReplyList()
        if len(ReplyList) <= self.reply_cnt and self.driver.find_elements(By.CSS_SELECTOR, ".result-streaming") == []:
            return "Error"
        for i in range(self.reply_cnt, len(ReplyList)):
            reply += ReplyList[i].text + "\n"
        self.reply_cnt = len(ReplyList)
        return reply

    def getReplyList(self):
        return self.driver.find_elements(By.CSS_SELECTOR, ".markdown")

class deepltranslator:
    def __init__(self):
        #如果是deepl pro的话 记得把server_url改为https://api.deepl-pro.com
        self.translator = deepl.Translator(auth_key=Settings.authkey, server_url=Settings.serverurl)

    def translate(self, text):
        try:
            return self.translator.translate_text(text, target_lang="zh").text
        except Exception as e:
            return str(e)

class OCR:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang="japan")

    def readText(self, image):
        result = self.ocr.ocr(image, cls=True)
        text = ''
        for idx in range(len(result)):
            res = result[idx]
            for r in res:
                text = text + r[1][0]
        return text

class Settings:
    size = None
    alpha = None
    ht1 = None
    ht2 = None
    translate_method = None
    apikey = ''
    model = ''
    serverurl = ''
    authkey = ''

def writeCfg():
    config = f'''# 字幕字号
size: "{Settings.size}"
# 字幕文字颜色和透明度 前面三个是rgb数值 后面是透明度 范围都为0-255
alpha: "{Settings.alpha}"
# 截图热键
captureHotkey: "{Settings.ht1}"
# 停止热键
pauseHotkey: "{Settings.ht2}"
# 翻译方式
Method: {Settings.translate_method}
# GPT APIKEY
ApiKey: "{Settings.apikey}"
# GPT模型名称
Model: "{Settings.model}"
# DeepL AuthKey
AuthKey: "{Settings.authkey}"
#DeepL Server Url 若为Pro则填https://api.deepl-pro.com Free保持默认
ServerUrl: "{Settings.serverurl}"'''
    open('config.yml', 'w', encoding="utf-8").write(config)

def loadCfg():
    default_config = '''# 字幕字号
size: 36
# 字幕文字颜色和透明度 前面三个是rgb数值 后面是透明度0-100 越高越不透明
alpha: "color:rgba(255,0,0,100);"
# 截图热键
captureHotkey: "w"
# 停止热键
pauseHotkey: "q"
# 翻译方式
Method: 1
# ApiKey
ApiKey: "Put your api key here if you enable gptapi"
# 模型名称
Model: "gpt-3.5-turbo"
# DeepL AuthKey
AuthKey: "Put your authkey here if you enable deeplapi"
#DeepL Server Url 若为Pro则填https://api.deepl-pro.com Free保持默认
ServerUrl: "https://api-free.deepl.com"'''
    while True:
        try:
            config = safe_load(open('config.yml', 'r', errors='ignore', encoding="utf-8"))
            Settings.size = int(config["size"])
            Settings.alpha = config["alpha"]
            Settings.ht1 = config["captureHotkey"]
            Settings.ht2 = config["pauseHotkey"]
            Settings.translate_method = int(config["Method"])
            Settings.apikey = config["ApiKey"]
            Settings.model = config["Model"]
            Settings.authkey = config["AuthKey"]
            Settings.serverurl = config["ServerUrl"]
            break
        except:
            print("加载配置文件失败,写入默认配置中....")
            open('config.yml', 'w', encoding="utf-8").write(default_config)
            sleep(2)

class captureSize:
    left = None
    right = None
    top = None
    bottom = None
    rect = None

class SubtitleApp(QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")
        self.label = QtWidgets.QLabel(self)
        self.label.setWordWrap(True)
        self.label.setGeometry(QtCore.QRect(0, 0, 1000, 300))
        self.label.setStyleSheet(Settings.alpha)
        self.label.setFont(QtGui.QFont("微软雅黑", Settings.size))
        self.label.setText("文本字幕")
        self.show()

    def updateSubtitle(self, text):
        self.label.setText(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))

    def mouseMoveEvent(self, QMouseEvent):
        if Qt.LeftButton and self.m_drag:
            self.move(QMouseEvent.globalPos() - self.m_DragPosition)
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_drag = False
        self.setCursor(QCursor(Qt.ArrowCursor))

class GetAreaInfo(QWidget):
    def __init__(self, png):
        super().__init__()
        self.startPos = None
        self.endPos = None
        self.rect = QRect()
        self.setMouseTracking(True)

        self.original_image = QPixmap(png)
        self.image = QPixmap(self.original_image)
        self.label = QLabel(self)
        self.label.setPixmap(self.image)

        vbox = QVBoxLayout()
        vbox.addWidget(self.label)
        self.setLayout(vbox)

        self.setGeometry(0, 0, self.image.width(), self.image.height())
        self.setWindowTitle('Draw Rectangle on Image')
        self.showFullScreen()

    def mousePressEvent(self, event):
        self.startPos = event.pos()
        self.rect.setTopLeft(self.startPos)
        self.rect.setBottomRight(self.startPos)
        self.update()

    def mouseMoveEvent(self, event):
        if not self.startPos:
            return
        self.endPos = event.pos()
        self.rect.setBottomRight(self.endPos)
        self.update()

    def mouseReleaseEvent(self, event):
        self.startPos = None
        self.endPos = None
        self.captureSize = self.rect.normalized()
        captureSize.rect = self.rect
        captureSize.left = self.captureSize.left()
        captureSize.right = self.captureSize.right()
        captureSize.top = self.captureSize.top()
        captureSize.bottom = self.captureSize.bottom()
        self.close()
        self.update()

    def paintEvent(self, event):
        if self.startPos and self.endPos:
            self.image = QPixmap(self.original_image)  # Reset the image
            painter = QPainter(self.image)
            painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
            painter.drawRect(self.rect)
            self.label.setPixmap(self.image)

class SettingsApp(QWidget):
    def __init__(self, parent=None):
        super(SettingsApp, self).__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(120, 230)

        self.layout = QVBoxLayout()

        self.label_size = QLabel("字幕字号")
        self.size = QLineEdit()
        self.size.setText(str(Settings.size))
        self.layout.addWidget(self.label_size)
        self.layout.addWidget(self.size)

        self.label_alpha = QLabel("字幕文字颜色和透明度")
        self.alpha = QLineEdit()
        self.alpha.setText(str(Settings.alpha))
        self.layout.addWidget(self.label_alpha)
        self.layout.addWidget(self.alpha)

        self.label_ht1 = QLabel("截图热键")
        self.ht1 = QLineEdit()
        self.ht1.setText(Settings.ht1)
        self.layout.addWidget(self.label_ht1)
        self.layout.addWidget(self.ht1)

        self.label_ht2 = QLabel("退出热键")
        self.ht2 = QLineEdit()
        self.ht2.setText(Settings.ht2)
        self.layout.addWidget(self.label_ht2)
        self.layout.addWidget(self.ht2)

        self.label_cb = QLabel("翻译方式")
        self.cb = QComboBox(self)
        self.cb.addItem('ChatGPT网页版')
        self.cb.addItem('GPT API')
        self.cb.addItem('DeepL API')
        self.cb.setCurrentIndex(Settings.translate_method)
        self.cb.currentIndexChanged.connect(self.on_translate_method_changed)
        self.layout.addWidget(self.label_cb)
        self.layout.addWidget(self.cb)

        self.stacked_widget = QStackedWidget(self)
        self.layout.addWidget(self.stacked_widget)

        self.page0 = QWidget()
        self.page0_layout = QVBoxLayout(self.page0)
        self.label_msg1 = QLabel("该选项不需要设置捏~")
        self.label_msg2 = QLabel('觉得不错的话请Github给个Star<a href="https://github.com/RetCute/GalTranslator">Github</a>')
        self.label_msg2.setOpenExternalLinks(True)
        self.label_msg3 = QLabel('或者B站三连支持一下UP!<a href="https://space.bilibili.com/441114907">Bilibili</a>')
        self.label_msg3.setOpenExternalLinks(True)
        self.page0_layout.addWidget(self.label_msg1)
        self.page0_layout.addWidget(self.label_msg2)
        self.page0_layout.addWidget(self.label_msg3)

        # 创建每个页面的布局
        self.page1 = QWidget()
        self.page1_layout = QVBoxLayout(self.page1)
        self.label_apikey = QLabel("ApiKey")
        self.apikey = QLineEdit()
        self.label_model = QLabel("Model")
        self.model = QLineEdit()
        self.model.setText(Settings.model)
        self.apikey.setText(Settings.apikey)
        self.page1_layout.addWidget(self.label_apikey)
        self.page1_layout.addWidget(self.apikey)
        self.page1_layout.addWidget(self.label_model)
        self.page1_layout.addWidget(self.model)

        self.page2 = QWidget()
        self.page2_layout = QVBoxLayout(self.page2)
        self.label_authkey = QLabel("AuthKey")
        self.authkey = QLineEdit()
        self.label_url = QLabel("Server Url")
        self.serverurl = QLineEdit()
        self.serverurl.setText(Settings.serverurl)
        self.authkey.setText(Settings.authkey)
        self.page2_layout.addWidget(self.label_authkey)
        self.page2_layout.addWidget(self.authkey)
        self.page2_layout.addWidget(self.label_url)
        self.page2_layout.addWidget(self.serverurl)

        # 添加页面到QStackedWidget
        self.stacked_widget.addWidget(self.page0)
        self.stacked_widget.addWidget(self.page1)
        self.stacked_widget.addWidget(self.page2)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save)
        self.layout.addWidget(self.save_button)

        self.on_translate_method_changed(self.cb.currentIndex())

        self.setLayout(self.layout)

    def on_translate_method_changed(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def save(self):
        Settings.size = int(self.size.text())
        Settings.alpha = self.alpha.text()
        Settings.ht1 = self.ht1.text()
        Settings.ht2 = self.ht2.text()
        Settings.translate_method = int(self.cb.currentIndex())
        Settings.apikey = self.apikey.text()
        Settings.model = self.model.text()
        Settings.authkey = self.authkey.text()
        Settings.serverurl = self.serverurl.text()
        writeCfg()
        QMessageBox.information(self, "保存成功", "保存成功,某些设置可能需要重启软件才能启用")

def buttonClick():
    global window2
    window.showMinimized()
    sleep(0.2)
    filename = 'temp.png'
    im = ImageGrab.grab()
    im.save(filename)
    im.close()
    image = Image.open(filename)
    image = image.convert("RGB")
    enhancer = ImageEnhance.Color(image)
    enhanced_image = enhancer.enhance(3)
    enhanced_image.save(filename)
    window2 = GetAreaInfo(filename)

def buttonClick2():
    global window3
    window3 = SettingsApp()
    window3.show()

def messageBox(title, message):
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Information)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()

def run():
    global running, display
    if not captureSize.top:
        messageBox(title="错误", message="你没有选择截图区域!")
    elif running:
        messageBox(title="警告", message="程序已经在运行中！不要重复点击!")
    else:
        running = True
        display = SubtitleApp()
        Thread(target=monitor, daemon=True).start()

def monitor():
    global running, display
    ocr = OCR()
    while True:
        if keyboard.is_pressed(Settings.ht1):
            ImageGrab.grab((captureSize.left, captureSize.top, captureSize.right, captureSize.bottom)).save('now.png')
            text = ocr.readText("now.png")
            print(text)
            reply = translator.translate(text)
            print(reply)
            display.updateSubtitle(reply)
        elif keyboard.is_pressed(Settings.ht2):
            print('Quit!')
            display.close()
            messageBox(title="提醒", message="已关闭")
            running = False
            break

if __name__ == "__main__":
    loadCfg()
    if Settings.translate_method == 1:
        translator = apitranslator()
    elif Settings.translate_method == 2:
        translator = deepltranslator()
    else:
        translator = webtranslator()
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("GalTranslator")
    window.setFixedSize(100, 150)
    widget = QWidget()
    layout = QVBoxLayout()
    widget.setLayout(layout)
    window.setCentralWidget(widget)
    button1 = QPushButton('选择截图区域')
    button1.clicked.connect(buttonClick)
    layout.addWidget(button1)
    button2 = QPushButton('设置')
    button2.clicked.connect(buttonClick2)
    layout.addWidget(button2)
    button3 = QPushButton('启动！')
    button3.clicked.connect(run)
    layout.addWidget(button3)
    window.show()
    app.exec_()