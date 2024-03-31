import os
import re
import subprocess
import psutil
from yaml import safe_load
from PyQt5.QtCore import QRect, QThread, Qt
from PyQt5.QtGui import QCursor, QPixmap, QPen, QPainter, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, QComboBox, \
    QMainWindow, QStackedWidget, QTextEdit, QHBoxLayout, QFileDialog, QListView, QDialog
from PyQt5 import QtWidgets, QtCore, QtGui
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
O = T = TE = True

class apitranslator:
    def __init__(self):
        self.client = OpenAI(api_key=Settings.apikey)
        self.messages = [
                    {"role": "system", "content": f"请将下面这段日文符合语气地优美地贴合原意地翻译为中文并且结合我消息记录的前几个句子进行翻译只给出翻译后的结果即可无需添加其他东西"},
                          ]

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
        except Exception as e:
            logTextBox.append(str(e))
            return "Error"

class webTranslatorThread(QThread):

    def __init__(self, translator):
        super().__init__()
        self.translator = translator

    def run(self):
        global T
        try:
            logTextBox.append("[INFO]初始化ChatGPT Web中....")
            logTextBox.append("[INFO]请在100s内登录你的ChatGPT账号")
            self.translator.reply_cnt = 0
            options = undetected_chromedriver.ChromeOptions()
            self.translator.driver = undetected_chromedriver.Chrome(options=options, browser_executable_path=Settings.bp)
            self.translator.driver.get("https://chat.openai.com/auth/login")
            WebDriverWait(self.translator.driver, timeout=100).until(EC.url_to_be("https://chat.openai.com/"))
            logTextBox.append("[INFO]Translator初始化成功")
        except Exception as e:
            logTextBox.append("[Error]Translator初始化失败:" + str(e))
            T = False

class webtranslator:
    def __init__(self):
        global T
        self.driver = None
        if not os.path.exists("chromedriver.exe"):
            logTextBox.append("[Error]未找到chromedriver 请下载对应版本的driver丢到目录下 或者切换其他翻译方式")
            T = False
        else:
            self.init_thread = webTranslatorThread(self)
            self.init_thread.start()

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
            pass

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
            reply += ReplyList[i].text
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
            logTextBox.append(str(e))
            return "Error"

class OcrThread(QThread):
    def __init__(self, ocr):
        super().__init__()
        self.ocr = ocr

    def run(self):
        global O
        try:
            logTextBox.append("[INFO]初始化OCR中....")
            self.ocr.ocr = PaddleOCR(use_angle_cls=True, lang="japan")
            logTextBox.append("[INFO]OCR已启动")
        except Exception as e:
            logTextBox.append("[Error]OCR初始化失败:" + str(e))
            O = False

class OCR:
    def __init__(self):
        self.ocr = None
        self.thread = OcrThread(self)
        self.thread.start()

    def readText(self, image):
        result = self.ocr.ocr(image, cls=True)
        text = ''
        for idx in range(len(result)):
            res = result[idx]
            for r in res:
                text = text + r[1][0]
        return text

class Textractor:
    def __init__(self):
        logTextBox.append("[Info]初始化Textractor中")
        if os.path.exists(Settings.tpath):
            self.process = subprocess.Popen(
                Settings.tpath,
                shell=False,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=0x08000000,
                encoding='utf-16-le'
            )
            logTextBox.append("[Info]TextractorCLI.exe Successfully Launched")
        else:
            global TE
            logTextBox.append("[Error]TextractorCLI.exe Not Found")
            TE = False

    def run(self, process):
        Thread(target=self.monitor_output, daemon=True).start()
        Thread(target=self.monitor, daemon=True, args=(process,)).start()
        self.attach(process[1])

    def is_running(self, processName):
        try:
            tasks = subprocess.check_output(['tasklist'], shell=True)
            return processName in str(tasks)
        except Exception as e:
            logTextBox.append(f"[Error]{e}")
            return False

    def monitor(self, process):
        global running
        while True:
            if keyboard.is_pressed(Settings.ht2) or not self.is_running(process[0]):
                logTextBox.append("[INFO]已退出!")
                self.detach(process[1])
                display.close()
                hookcodeapp.close()
                running = False
                break

    def attach(self, pid):
        self.process.stdin.write(f"attach -P {pid}\n")
        self.process.stdin.flush()

    def detach(self, pid):
        self.process.stdin.write(f"detach -P {pid}\n")
        self.process.stdin.flush()

    def monitor_output(self):
        global running
        while running:
            try:
                output = self.process.stdout.readline().strip()
                if output:
                    hookcodeapp.processText(output)
            except Exception as e:
                logTextBox.append("[Error]" + str(e))

class HookcodeApp(QWidget):
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle("HookCode Selector")
        self.setLayout(layout)
        self.setFixedSize(400, 400)
        self.messages = {}
        self.comboBox = QtWidgets.QComboBox()
        layout.addWidget(self.comboBox)
        self.textEdit = QtWidgets.QTextEdit()
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)
        self.comboBox.currentIndexChanged.connect(self.updateTextEdit)
        self.show()

    def processText(self, text):
        if text.startswith("[") and "]" in text:
            end_index = text.index("]")
            key = text[1:end_index]
            value = "[Textractor]"+text[end_index + 2:]
            if key not in self.messages:
                self.comboBox.addItem(key)
                self.messages[key] = []
            self.messages[key].append(value)
            if self.comboBox.currentText() == key:
                self.textEdit.append(value)
                reply = translator.translate(value)
                display.updateSubtitle(reply)

    def updateHookcode(self, item):
        self.comboBox.addItem(item)

    def updateTextEdit(self):
        currentKey = self.comboBox.currentText()
        if currentKey in self.messages:
            self.textEdit.setText("\n".join(self.messages[currentKey]))
        else:
            self.textEdit.clear()

class Settings:
    size = None
    alpha = None
    ht1 = ''
    ht2 = ''
    text_extraction_mode = None
    tpath = ''
    bp = ''
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
# 文字提取方式 0为OCR 1为Textractor
Text_Extraction_Mode: {Settings.text_extraction_mode}
# TextractorCLI.exe的文件地址
TextractorPath: "{Settings.tpath}"
# 翻译方式
Method: {Settings.translate_method}
# Google浏览器的文件地址
Browser_Path: "{Settings.bp}"
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
alpha: "color:rgba(255,0,0,255);"
# 截图热键
captureHotkey: "w"
# 停止热键
pauseHotkey: "q"
# 文字提取方式 0为OCR 1为Textractor
Text_Extraction_Mode: 0
# TextractorCLI.exe的文件地址
TextractorPath: ""
# 翻译方式
Method: 1
# Google浏览器的文件地址
Browser_Path: ""
# GPTApiKey
ApiKey: "Put your api key here if you enable gptapi"
# GPT模型名称
Model: "gpt-3.5-turbo"
# DeepL AuthKey
AuthKey: "Put your authkey here if you enable deeplapi"
#DeepL Server Url 若为Pro则填https://api.deepl-pro.com Free保持默认
ServerUrl: "https://api-free.deepl.com"'''
    while True:
        try:
            logTextBox.append("[INFO]读取配置文件中....")
            config = safe_load(open('config.yml', 'r', errors='ignore', encoding="utf-8"))
            Settings.size = int(config["size"])
            Settings.alpha = config["alpha"]
            Settings.ht1 = config["captureHotkey"]
            Settings.ht2 = config["pauseHotkey"]
            Settings.text_extraction_mode = int(config["Text_Extraction_Mode"])
            Settings.tpath = config["TextractorPath"]
            Settings.translate_method = int(config["Method"])
            Settings.bp = config["Browser_Path"]
            Settings.apikey = config["ApiKey"]
            Settings.model = config["Model"]
            Settings.authkey = config["AuthKey"]
            Settings.serverurl = config["ServerUrl"]
            logTextBox.append("[INFO]成功!")
            break
        except:
            logTextBox.append("[Error]加载配置文件失败,写入默认配置中....")
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
        font = QtGui.QFont("黑体", Settings.size)
        font.setBold(True)
        font.setStyleStrategy(QtGui.QFont.PreferOutline)
        self.label.setFont(font)
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
        window.showNormal()
        os.remove("temp.png")

    def paintEvent(self, event):
        if self.startPos and self.endPos:
            self.image = QPixmap(self.original_image)
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

        self.lcb = QLabel("文字提取方式")
        self.cb1 = QComboBox(self)
        self.cb1.addItem('OCR')
        self.cb1.addItem('Textractor')
        self.cb1.setCurrentIndex(Settings.text_extraction_mode)
        self.cb1.currentIndexChanged.connect(self.on_text_extraction_mode_changed)
        self.layout.addWidget(self.lcb)
        self.layout.addWidget(self.cb1)

        self.stacked_widget1 = QStackedWidget(self)
        self.layout.addWidget(self.stacked_widget1)
        self.p0 = QWidget()
        self.p0_layout = QVBoxLayout(self.p0)
        self.msg1 = QLabel("该选项不需要设置捏~")
        self.msg2 = QLabel("在速度和效率上更推荐Textractor")
        self.p0_layout.addWidget(self.msg1)
        self.p0_layout.addWidget(self.msg2)
        self.p1 = QWidget()
        self.p1_layout = QVBoxLayout(self.p1)
        self.label_path = QLabel("TextractorCLI.exe的地址")
        self.path = QLineEdit()
        self.path.setText(Settings.tpath)
        self.browse_button = QPushButton("选取")
        self.browse_button.clicked.connect(lambda: self.open_file_dialog("Select TextractorCLI.exe", self.path))
        topLayout = QHBoxLayout()
        topLayout.addWidget(self.path)
        topLayout.addWidget(self.browse_button)
        self.p1_layout.addWidget(self.label_path)
        self.p1_layout.addLayout(topLayout)

        self.stacked_widget1.addWidget(self.p0)
        self.stacked_widget1.addWidget(self.p1)

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
        self.label_msg1 = QLabel("Chrome浏览器文件地址")
        self.path1 = QLineEdit()
        self.path1.setText(Settings.bp)
        self.browse = QPushButton("选取")
        self.browse.clicked.connect(lambda: self.open_file_dialog("Select Chrome.exe", self.path1))
        topLayout1 = QHBoxLayout()
        topLayout1.addWidget(self.path1)
        topLayout1.addWidget(self.browse)
        self.p1_layout.addWidget(self.label_path)
        self.p1_layout.addLayout(topLayout)
        self.label_msg2 = QLabel('觉得不错的话请Github给个Star<a href="https://github.com/RetCute/GalTranslator">Github</a>')
        self.label_msg2.setOpenExternalLinks(True)
        self.label_msg3 = QLabel('或者B站三连支持一下UP!<a href="https://space.bilibili.com/441114907">Bilibili</a>')
        self.label_msg3.setOpenExternalLinks(True)
        self.page0_layout.addWidget(self.label_msg1)
        self.page0_layout.addLayout(topLayout1)
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
        self.on_text_extraction_mode_changed(self.cb1.currentIndex())

        self.setLayout(self.layout)

    def on_translate_method_changed(self, index):
        self.stacked_widget.setCurrentIndex(index)

    def on_text_extraction_mode_changed(self, index):
        self.stacked_widget1.setCurrentIndex(index)

    def open_file_dialog(self, msg, path):
        file_path, _ = QFileDialog.getOpenFileName(self, msg)

        if file_path:
            path.setText(file_path)

    def save(self):
        Settings.size = int(self.size.text())
        Settings.alpha = self.alpha.text()
        Settings.ht1 = self.ht1.text()
        Settings.ht2 = self.ht2.text()
        Settings.tpath = self.path.text()
        Settings.text_extraction_mode = int(self.cb1.currentIndex())
        Settings.bp = self.path1.text()
        Settings.translate_method = int(self.cb.currentIndex())
        Settings.apikey = self.apikey.text()
        Settings.model = self.model.text()
        Settings.authkey = self.authkey.text()
        Settings.serverurl = self.serverurl.text()
        writeCfg()
        QMessageBox.information(self, "保存成功", "保存成功,某些设置可能需要重启软件才能启用")

class AttachProcessDialog(QDialog):
    def __init__(self, processes_map, parent=None):
        super(AttachProcessDialog, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.processes_map = processes_map
        self.setWindowTitle("SELECT_PROCESS")
        self.label = QLabel("选择进程")
        self.processList = QListView()
        self.processEdit = QLineEdit()
        self.okButton = QPushButton("OK")
        self.cancelButton = QPushButton("Cancel")

        self.model = QStandardItemModel(self)
        self.processList.setModel(self.model)

        transparent = QPixmap(100, 100)
        transparent.fill(Qt.transparent)
        for process in self.processes_map.keys():
            item = QStandardItem(process)
            item.setEditable(False)
            self.model.appendRow(item)

        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        self.processList.clicked.connect(self.onProcessClicked)
        self.processList.doubleClicked.connect(self.accept)
        self.processEdit.textEdited.connect(self.onProcessEdited)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.processList)
        layout.addWidget(self.processEdit)
        layout.addWidget(self.okButton)
        layout.addWidget(self.cancelButton)
        self.setLayout(layout)

    def onProcessClicked(self, index):
        self.processEdit.setText(self.model.itemFromIndex(index).text())

    def onProcessEdited(self, text):
        for i in range(self.model.rowCount()):
            self.processList.setRowHidden(i, text.lower() not in self.model.item(i).text().lower())

    def selectedProcess(self):
        return self.processEdit.text(), self.processes_map[self.processEdit.text()]

def get_all_processes():
    processes_map = {}
    files = []

    for process in psutil.process_iter(attrs=['pid', 'name', 'exe']):
        try:
            exe_path = process.info['exe']
            if exe_path and "\\Windows\\" not in exe_path:
                file_name = os.path.basename(exe_path)
                if file_name not in files:
                    processes_map[file_name] = process.info["pid"]
                    files.append(file_name)
        except:
            pass
    return processes_map

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
    global running, display, hookcodeapp
    conditions = not T or not O
    if Settings.text_extraction_mode != 0:
        conditions = not T or not TE
    if not captureSize.top and Settings.text_extraction_mode == 0:
        messageBox(title="警告", message="你没有选择截图区域!")
    elif running:
        messageBox(title="警告", message="程序已经在运行中！不要重复点击!")
    elif conditions:
        messageBox(title="警告", message="Translator或OCR/Textractor初始化失败!")
    else:
        if Settings.text_extraction_mode == 0:
            running = True
            window.showMinimized()
            logTextBox.append("[INFO]程序开始运行")
            display = SubtitleApp()
            Thread(target=monitor, daemon=True).start()
        else:
            dialog = AttachProcessDialog(get_all_processes())
            if dialog.exec_():
                running = True
                window.showMinimized()
                logTextBox.append("[INFO]程序开始运行")
                display = SubtitleApp()
                Process = dialog.selectedProcess()
                hookcodeapp = HookcodeApp()
                textractor.run(Process)

def monitor():
    global running
    while True:
        try:
            if keyboard.is_pressed(Settings.ht1):
                ImageGrab.grab((captureSize.left, captureSize.top, captureSize.right, captureSize.bottom)).save('now.png')
                text = ocr.readText("now.png")
                logTextBox.append("[OCR]"+text)
                reply = translator.translate(text)
                logTextBox.append("[Translated]"+reply)
                display.updateSubtitle(reply)
            elif keyboard.is_pressed(Settings.ht2):
                logTextBox.append("已退出!")
                display.close()
                running = False
                break
        except Exception as e:
            logTextBox.append("[Error]" + str(e))

class Main:
    def __init__(self):
        global window
        window = QMainWindow()
        self.window = window
        self.Init()

    def InitFunctions(self):
        global translator, ocr, textractor
        if Settings.text_extraction_mode == 0:
            ocr = OCR()
        else:
            textractor = Textractor()
        if Settings.translate_method == 1:
            logTextBox.append("[INFO]您正在使用OpenAI GPT API翻译模式")
            translator = apitranslator()
        elif Settings.translate_method == 2:
            logTextBox.append("[INFO]您正在使用DeepL API翻译模式")
            translator = deepltranslator()
        else:
            logTextBox.append("[INFO]您正在使用ChatGPT Web翻译模式")
            translator = webtranslator()

    def Init(self):
        global logTextBox
        self.window.setWindowTitle("GalTranslator")
        self.window.setFixedSize(300, 300)
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        self.window.setCentralWidget(widget)
        button1 = QPushButton('选择截图区域')
        button1.clicked.connect(buttonClick)
        layout.addWidget(button1)
        button2 = QPushButton('设置')
        button2.clicked.connect(buttonClick2)
        layout.addWidget(button2)
        button3 = QPushButton('启动！')
        button3.clicked.connect(run)
        layout.addWidget(button3)
        label = QLabel("运行日志:")
        layout.addWidget(label)
        logTextBox = QTextEdit()
        logTextBox.setReadOnly(True)
        layout.addWidget(logTextBox)
        window.show()
        loadCfg()
        self.InitFunctions()
        app.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    try:
        Main()
    except Exception as e:
        print(str(e))
