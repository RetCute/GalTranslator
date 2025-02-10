import importlib
import os
import subprocess
import psutil
import requests
from yaml import safe_load
from PyQt5.QtCore import QRect, QThread, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QPen, QPainter, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, QComboBox, \
    QMainWindow, QStackedWidget, QTextEdit, QHBoxLayout, QFileDialog, QListView, QDialog, QScrollArea, QSizePolicy
from PyQt5 import QtWidgets, QtCore, QtGui
import sys, argparse
import traceback
from PIL import Image, ImageGrab, ImageEnhance
from time import sleep
import keyboard
from threading import Thread
from paddleocr import PaddleOCR
import win32gui
import win32process

Version = "V1.2"
running = False
modules = []
O = TE = False

class OcrThread(QThread):
    def __init__(self, ocr):
        super().__init__()
        self.ocr = ocr

    def run(self):
        global O
        try:
            updateLog("Info", "初始化OCR中....")
            self.ocr.ocr = PaddleOCR(use_angle_cls=True, lang="japan")
            updateLog("Info", "OCR已启动")
            O = True
        except Exception:
            updateLog("Error", "OCR初始化失败:")
            updateLog("", traceback.format_exc())

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
        global TE
        updateLog("Info", "初始化Textractor中")
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
            updateLog("Info", "TextractorCLI.exe Successfully Launched")
            TE = True
        else:
            updateLog("Error", "TextractorCLI.exe Not Found")

    def run(self, pid):
        if self.process.poll():
            self.process = subprocess.Popen(
                Settings.tpath,
                shell=False,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=0x08000000,
                encoding='utf-16-le'
            )
        Thread(target=self.monitor_output, daemon=True).start()
        Thread(target=self.monitor, daemon=True, args=(pid,)).start()
        self.attach(pid)

    def monitor(self, pid):
        global running
        while True:
            if keyboard.is_pressed(Settings.ht2) or not psutil.pid_exists(pid):
                updateLog("Info", "已退出!")
                self.detach(pid)
                self.process.kill()
                display.exit()
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
            except Exception:
                updateLog("Error", traceback.format_exc())

class MessageWidget(QWidget):
    def __init__(self, text1, text2, key, parent=None):
        super(MessageWidget, self).__init__(parent)
        self.key = key
        vlayout = QVBoxLayout()
        vlayout.setSpacing(0)
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.label1 = QLabel("[Textractor]"+text1)
        self.label1.setWordWrap(True)
        self.label1.setFixedWidth(350)
        self.label1.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.label1)
        self.label2 = QLabel("[Translated]"+text2)
        self.label2.setWordWrap(True)
        self.label2.setFixedWidth(350)
        self.label2.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.label2)
        self.button = QPushButton("Update")
        self.button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        hlayout = QHBoxLayout(self)
        hlayout.addLayout(vlayout)
        hlayout.addWidget(self.button)

class HookcodeApp(QWidget):
    message_signal = pyqtSignal(str, str, str)
    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QVBoxLayout(self)
        self.setWindowTitle("HookCode Selector")
        self.setLayout(layout)
        self.setFixedSize(500, 500)
        self.messages = {}
        self.message_signal.connect(self.addMessage)
        self.comboBox = QtWidgets.QComboBox()
        layout.addWidget(self.comboBox)
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidget = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidget)
        self.scrollAreaLayout.setSpacing(0)
        self.scrollArea.setWidget(self.scrollAreaWidget)
        layout.addWidget(self.scrollArea)
        self.comboBox.currentIndexChanged.connect(self.updateScrollArea)
        self.show()

    def processText(self, text):
        if text.startswith("[") and "]" in text:
            end_index = text.index("]")
            key = text[1:end_index]
            value = text[end_index + 2:]
            if key not in self.messages:
                self.updateHookcode(key)
                self.messages[key] = []
            if self.comboBox.currentText() == key and not "控制台" in key and not "剪贴" in key:
                reply = translator.translate(value)
                self.message_signal.emit(key, value, reply)
                display.updateSubtitle(reply)
                self.storeMsg(key, value, reply)
            else:
                self.storeMsg(key, value, "未翻译")

    def addMessage(self, key, text, text2="未翻译"):
        if self.scrollAreaLayout.count() > 0:
            lastItem = self.scrollAreaLayout.itemAt(self.scrollAreaLayout.count() - 1)
            if lastItem.spacerItem():
                self.scrollAreaLayout.takeAt(self.scrollAreaLayout.count() - 1)
        messageWidget = MessageWidget(text, text2, key)
        messageWidget.button.clicked.connect(lambda: self.updateSubtitle(messageWidget))
        self.scrollAreaLayout.addWidget(messageWidget)
        self.scrollAreaLayout.addStretch(1)
        self.scrollArea.verticalScrollBar().setValue(self.scrollArea.verticalScrollBar().maximum())
        self.scrollArea.repaint()

    def updateSubtitle(self, msg):
        if not ("未翻译" in msg.label2.text() or "Error" in msg.label2.text()):
            display.updateSubtitle(msg.label2.text())
        else:
            text = msg.label1.text().replace("[Textractor]", "")
            reply = translator.translate(text)
            msg.label2.setText("[Translated]" + reply)
            display.updateSubtitle(reply)
            for dictionary in self.messages[msg.key]:
                if text in dictionary:
                    dictionary[text] = reply

    def storeMsg(self, key, value, reply):
        self.messages[key].append({value: reply})

    def updateHookcode(self, item):
            self.comboBox.addItem(item)

    def updateScrollArea(self):
        currentKey = self.comboBox.currentText()
        self.scrollAreaLayout.addStretch(1)
        if self.scrollAreaLayout.count() > 0:
            self.scrollAreaLayout.takeAt(self.scrollAreaLayout.count() - 1)
        for i in reversed(range(self.scrollAreaLayout.count())):
            widgetToRemove = self.scrollAreaLayout.itemAt(i).widget()
            if widgetToRemove:
                widgetToRemove.setParent(None)
        for dictionary in self.messages.get(currentKey, []):
            for msg1, msg2 in dictionary.items():
                self.addMessage(currentKey, msg1, msg2)
        self.scrollAreaWidget.setLayout(self.scrollAreaLayout)
        self.scrollArea.verticalScrollBar().setValue(self.scrollArea.verticalScrollBar().maximum())

class Settings:
    size = None
    alpha = None
    ht1 = ''
    ht2 = ''
    text_extraction_mode = None
    tpath = ''
    translate_method = None

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
Method: {Settings.translate_method}'''
    open('config.yml', 'w', encoding="utf-8").write(config)

def loadCfg():
    default_config = '''# 字幕字号
size: 20
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
Method: 1'''
    while True:
        try:
            updateLog("Info", "读取配置文件中....")
            config = safe_load(open('config.yml', 'r', errors='ignore', encoding="utf-8"))
            Settings.size = int(config["size"])
            Settings.alpha = config["alpha"]
            Settings.ht1 = config["captureHotkey"]
            Settings.ht2 = config["pauseHotkey"]
            Settings.text_extraction_mode = int(config["Text_Extraction_Mode"])
            Settings.tpath = config["TextractorPath"]
            Settings.translate_method = int(config["Method"])
            updateLog("Info", "成功!")
            break
        except:
            updateLog("Error", "加载配置文件失败,写入默认配置中....")
            open('config.yml', 'w', encoding="utf-8").write(default_config)
            sleep(2)

class captureSize:
    left = None
    right = None
    top = None
    bottom = None
    rect = None

class SubtitleApp(QtWidgets.QWidget):
    def __init__(self, pid=None):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.SplashScreen | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")
        self.label = QtWidgets.QLabel(self)
        self.label.setWordWrap(True)
        self.label.setGeometry(QtCore.QRect(0, 0, 700, 150))
        self.label.setStyleSheet(Settings.alpha)
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        font = QtGui.QFont("Arial", Settings.size)
        font.setBold(True)
        font.setStyleStrategy(QtGui.QFont.PreferOutline)
        self.label.setFont(font)
        self.label.setText("文本字幕")

        self.m_drag = False
        self.m_DragPosition = QtCore.QPoint()
        self.controlsVisible = False

        self.keepBorderCheckbox = QtWidgets.QCheckBox("保持边框状态", self)
        self.keepBorderCheckbox.setGeometry(QtCore.QRect(580, 125, 140, 30))
        self.keepBorderCheckbox.setStyleSheet("""
            QCheckBox {
                color: white;        /* 字体颜色 */
                font-family: Arial;  /* 字体族 */
                font-size: 15px;     /* 字体大小 */
                font-weight: bold;   /* 字体加粗 */
            }
            """)
        self.keepBorderCheckbox.hide()
        self.keepBorderCheckbox.stateChanged.connect(self.keepBorderStateChanged)

        self.show()
        self.autoHideTimer = QtCore.QTimer(self)
        self.autoHideTimer.setInterval(2000)
        self.autoHideTimer.timeout.connect(self.autoHideControls)
        if pid:
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(lambda: self.check_process_window(pid))
            self.timer.start(1000)

    def check_process_window(self, pid):
        hwnd = get_window_handle(pid)
        if hwnd:
            is_minimized = win32gui.IsIconic(hwnd)
            if is_minimized:
                self.hide()
            else:
                self.show()

    def exit(self):
        self.timer.stop()
        self.autoHideTimer.stop()
        self.close()

    def updateSubtitle(self, text):
        self.label.setText(text)

    def keepBorderStateChanged(self):
        if not self.keepBorderCheckbox.isChecked():
            self.toggleControls(forceHide=True)

    def toggleControls(self, forceHide=False):
        if self.keepBorderCheckbox.isChecked() and not forceHide:
            self.controlsVisible = True
            self.label.setStyleSheet(f"{Settings.alpha}; background-color: rgba(0, 0, 0, 128);")
        else:
            self.controlsVisible = not self.controlsVisible
            if self.controlsVisible:
                self.label.setStyleSheet(f"{Settings.alpha}; background-color: rgba(0, 0, 0, 128);")
                self.keepBorderCheckbox.show()
                self.autoHideTimer.start()
            else:
                self.label.setStyleSheet(f"{Settings.alpha}; background-color: rgba(0, 0, 0, 0);")
                self.keepBorderCheckbox.hide()
                self.autoHideTimer.stop()

    def autoHideControls(self):
        if self.controlsVisible:
            self.toggleControls()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()
            self.setCursor(QtGui.QCursor(QtCore.Qt.OpenHandCursor))
            if not self.controlsVisible:
                self.toggleControls()
            else:
                self.autoHideTimer.start()

    def mouseMoveEvent(self, QMouseEvent):
        if QtCore.Qt.LeftButton and self.m_drag:
            self.move(QMouseEvent.globalPos() - self.m_DragPosition)
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_drag = False
        self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

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
        for m in modules:
            self.cb.addItem(m.Manifest.module_name)
        self.cb.setCurrentIndex(Settings.translate_method)
        self.cb.currentIndexChanged.connect(self.on_translate_method_changed)
        self.layout.addWidget(self.label_cb)
        self.layout.addWidget(self.cb)

        self.author = QLabel(f"模块作者:{modules[self.cb.currentIndex()].Manifest.author}")
        self.url = QLabel(f"相关链接:<a href='{modules[self.cb.currentIndex()].Manifest.url}'>{modules[self.cb.currentIndex()].Manifest.url}</a>")
        self.url.setOpenExternalLinks(True)
        self.url.setWordWrap(True)
        self.description = QLabel(f"模块介绍:{modules[self.cb.currentIndex()].Manifest.description}")
        self.description.setWordWrap(True)
        self.cfgbutton = QPushButton("配置模块")
        self.cfgbutton.clicked.connect(modules[self.cb.currentIndex()].openSettings)
        self.layout.addWidget(self.author)
        self.layout.addWidget(self.url)
        self.layout.addWidget(self.description)
        self.layout.addWidget(self.cfgbutton)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save)
        self.layout.addWidget(self.save_button)

        self.on_translate_method_changed(self.cb.currentIndex())
        self.on_text_extraction_mode_changed(self.cb1.currentIndex())

        self.setLayout(self.layout)

    def on_translate_method_changed(self, index):
        self.author.setText(f"模块作者:{modules[index].Manifest.author}")
        self.url.setText(f"相关链接:<a href='{modules[index].Manifest.url}'>{modules[index].Manifest.url}</a>")
        self.description.setText(f"模块介绍:{modules[index].Manifest.description}")
        self.cfgbutton.clicked.disconnect()
        self.cfgbutton.clicked.connect(modules[index].openSettings)

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
        Settings.translate_method = int(self.cb.currentIndex())
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

    def accept(self):
        process_name = self.processEdit.text()
        if process_name and process_name in self.processes_map:
            super(AttachProcessDialog, self).accept()  # 正常关闭对话框
        else:
            QMessageBox.warning(self, "Warning", "请选择一个进程或者输入有效的进程名称！")

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

def get_window_handle(pid):
    def callback(hwnd, hwnds):
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid and win32gui.IsWindowVisible(hwnd):
            hwnds.append(hwnd)
        return True
    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds[0] if hwnds else None

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

def updateLog(msg_type, msg):
    logTextBox.append(f"[{msg_type}]{msg}")

def run():
    global running, display, hookcodeapp
    conditions = translator.running and O
    if Settings.text_extraction_mode != 0:
        conditions = translator.running and TE
    if not captureSize.top and Settings.text_extraction_mode == 0:
        messageBox(title="警告", message="你没有选择截图区域!")
    elif running:
        messageBox(title="警告", message="程序已经在运行中！不要重复点击!")
    elif not conditions:
        messageBox(title="警告", message="Translator或OCR/Textractor初始化失败!")
    else:
        if Settings.text_extraction_mode == 0:
            running = True
            window.showMinimized()
            updateLog("Info", "程序开始运行")
            display = SubtitleApp()
            Thread(target=monitor, daemon=True).start()
        else:
            dialog = AttachProcessDialog(get_all_processes())
            if dialog.exec_():
                running = True
                window.showMinimized()
                updateLog("Info", "程序开始运行")
                Process = dialog.selectedProcess()
                display = SubtitleApp(pid=Process[1])
                hookcodeapp = HookcodeApp()
                textractor.run(Process[1])

def monitor():
    global running
    while True:
        try:
            if keyboard.is_pressed(Settings.ht1):
                ImageGrab.grab((captureSize.left, captureSize.top, captureSize.right, captureSize.bottom)).save('now.png')
                text = ocr.readText("now.png")
                updateLog("OCR", text)
                reply = translator.translate(text)
                updateLog("Translated", reply)
                display.updateSubtitle(reply)
            elif keyboard.is_pressed(Settings.ht2):
                updateLog("Info", "已退出!")
                display.close()
                running = False
                break
        except Exception:
            updateLog("Error", traceback.format_exc())

def Annoucement():
    try:
        annoucement = requests.get("https://gh-proxy.com/https://raw.githubusercontent.com/RetCute/GalTranslator/main/Annoucement", timeout=10).text
        updateLog("Info", "获取公告中")
        messageBox("公告", annoucement)
    except:
        messageBox("Error", "获取公告失败")
        updateLog("Error", "获取公告失败，请使用代理后重试")

def CheckForUpdates():
    try:
        updateLog("Info", "Checking for updates....")
        version = requests.get("https://gh-proxy.com/https://raw.githubusercontent.com/RetCute/GalTranslator/main/Version", timeout=10).text.strip()
        if version != Version:
            messageBox("更新通知", "检测到有新版本可用,请前往Github下载")
            updateLog("Info", "New version available")
        else:
            updateLog("Info", "You are using the latest version")
    except:
        messageBox("Error", "检查更新失败")
        updateLog("Error", "检查更新失败，请使用代理后重试")

def SetProxies():
    parser = argparse.ArgumentParser(description='设置系统代理')
    parser.add_argument('-httpproxy', action='store', type=str, required=False,
                        help='设置 HTTP 代理的地址和端口。')
    parser.add_argument('-httpsproxy', action='store', type=str, required=False,
                        help='设置 HTTPS 代理的地址和端口。')
    args = parser.parse_args()
    if args.httpproxy:
        os.environ['HTTP_PROXY'] = args.httpproxy
        print(f"HTTP 代理已设置为: {args.httpproxy}")
    if args.httpsproxy:
        os.environ['HTTPS_PROXY'] = args.httpsproxy
        print(f"HTTPS 代理已设置为: {args.httpsproxy}")

class Main:
    def __init__(self):
        global window
        window = QMainWindow()
        self.window = window
        self.Init()

    def scanTranslators(self):
        for root, dirs, files in os.walk('modules'):
            for subdir in dirs:
                try:
                    module_name = f"{root}.{subdir}.translator".replace('/', '.').replace('\\', '.')
                    imported_module = importlib.import_module(module_name)
                    if hasattr(imported_module, 'Translator') and hasattr(imported_module, 'openSettings') and hasattr(imported_module, 'Manifest'):
                        modules.append(imported_module)
                    else:
                        updateLog("Error", f"导入{subdir}出错,可能该模块不符合标准格式")
                except:
                    pass

    def InitFunctions(self):
        global translator, ocr, textractor, module
        self.scanTranslators()
        if Settings.text_extraction_mode == 0:
            ocr = OCR()
        else:
            textractor = Textractor()
        module = modules[Settings.translate_method]
        translator = modules[Settings.translate_method].Translator(updateLog)
        updateLog("Info", f"您正在使用{module.Manifest.module_name}翻译模式")

    def Init(self):
        global logTextBox
        self.window.setWindowTitle("ReTranslator")
        self.window.setFixedSize(350, 450)
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
        window.showNormal()
        CheckForUpdates()
        Annoucement()
        loadCfg()
        self.InitFunctions()
        app.exec_()

if __name__ == "__main__":
    SetProxies()
    app = QApplication(sys.argv)
    try:
        Main()
    except:
        traceback.print_exc()
