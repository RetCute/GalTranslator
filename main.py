from paddleocr import PaddleOCR
import tkinter
import tkinter.messagebox
import os
from PIL import ImageGrab, Image, ImageEnhance
from time import sleep
import keyboard
from threading import Thread
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
import undetected_chromedriver
from selenium.webdriver.common.keys import Keys
from yaml import safe_load
from openai import OpenAI

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

class captureSize:
    left = None
    right = None
    top = None
    bottom = None

class Settings:
    size = None
    alpha = None
    ht1 = None
    ht2 = None
    api = False
    apikey = ''
    model = ''

class translator:
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

class getAreainfo:
    def __init__(self, png):
        self.X = tkinter.IntVar(value=0)
        self.Y = tkinter.IntVar(value=0)
        screenWidth = root.winfo_screenwidth()
        screenHeight = root.winfo_screenheight()
        self.top = tkinter.Toplevel(root, width=screenWidth, height=screenHeight)
        self.top.overrideredirect(True)
        self.canvas = tkinter.Canvas(self.top, bg='white', width=screenWidth, height=screenHeight)
        self.image = tkinter.PhotoImage(file=png)
        self.canvas.create_image(screenWidth // 2, screenHeight // 2, image=self.image)

        def onLeftButtonDown(event):
            self.X.set(event.x)
            self.Y.set(event.y)
            self.sel = True

        def onLeftButtonMove(event):
            if not self.sel:
                return
            global lastDraw
            try:
                self.canvas.delete(lastDraw)
            except:
                pass
            lastDraw = self.canvas.create_rectangle(self.X.get(), self.Y.get(), event.x, event.y, outline='red')

        def onLeftButtonUp(event):
            self.sel = False
            try:
                self.canvas.delete(lastDraw)
            except:
                pass
            sleep(0.1)
            captureSize.left, captureSize.right = sorted([self.X.get(), event.x])
            captureSize.top, captureSize.bottom = sorted([self.Y.get(), event.y])
            self.top.destroy()

        self.canvas.bind('<Button-1>', onLeftButtonDown)
        self.canvas.bind('<B1-Motion>', onLeftButtonMove)
        self.canvas.bind('<ButtonRelease-1>', onLeftButtonUp)
        self.canvas.pack(fill=tkinter.BOTH, expand=tkinter.YES)

class SubtitleApp:
    def __init__(self, root):
        self.root = tkinter.Toplevel(root)
        self.root.geometry(Settings.size)
        self.root.title("字幕")
        self.root.attributes('-topmost', 1)
        self.root.attributes("-alpha", Settings.alpha)

        self.subtitle_label = tkinter.Label(self.root, text="文字字幕", font=("Helvetica", 20), wraplength=int(Settings.size.split("x")[0]))
        self.subtitle_label.grid(sticky="W")
        self.subtitle_label.place(x=0, y=0)

    def update_subtitle(self, new_subtitle):
        self.subtitle_label.config(text=new_subtitle)

class SettingsApp:
    def __init__(self):
        self.root = tkinter.Toplevel(root)
        self.root.geometry("120x230")
        self.root.title("Settings")
        tkinter.Label(self.root, text="字幕大小", font=("微软雅黑", 10)).place(x=5, y=0, width=50, height=30)
        self.size = tkinter.Entry(self.root, relief="solid")
        self.size.insert(0, Settings.size)
        self.size.place(x=64, y=5, width=50, height=20)
        tkinter.Label(self.root, text="字幕透明度", font=("微软雅黑", 9)).place(x=2, y=30, width=65, height=30)
        self.alpha = tkinter.Entry(self.root, relief="solid")
        self.alpha.insert(0, Settings.alpha)
        self.alpha.place(x=64, y=35, width=50, height=20)
        tkinter.Label(self.root, text="截图热键", font=("微软雅黑", 10)).place(x=2, y=60, width=65, height=30)
        self.ht1 = tkinter.Entry(self.root, relief="solid")
        self.ht1.insert(0, Settings.ht1)
        self.ht1.place(x=64, y=65, width=50, height=20)
        tkinter.Label(self.root, text="退出热键", font=("微软雅黑", 10)).place(x=2, y=90, width=65, height=30)
        self.ht2 = tkinter.Entry(self.root, relief="solid")
        self.ht2.insert(0, Settings.ht2)
        self.ht2.place(x=64, y=95, width=50, height=20)
        self.apivar = tkinter.BooleanVar()
        self.api = tkinter.Checkbutton(self.root, text="启用API模式", variable=self.apivar)
        self.apivar.set(Settings.api)
        self.api.place(x=2, y=120)
        tkinter.Label(self.root, text="ApiKey", font=("微软雅黑", 10)).place(x=2, y=140, width=65, height=30)
        self.apikey = tkinter.Entry(self.root, relief="solid")
        self.apikey.insert(0, Settings.apikey)
        self.apikey.place(x=64, y=145, width=50, height=20)
        tkinter.Label(self.root, text="Model", font=("微软雅黑", 10)).place(x=2, y=170, width=65, height=30)
        self.model = tkinter.Entry(self.root, relief="solid")
        self.model.insert(0, Settings.model)
        self.model.place(x=64, y=175, width=50, height=20)
        btn = tkinter.Button(self.root, text="保存", command=self.save)
        btn.place(x=35, y=203, width=50, height=20)

    def save(self):
        Settings.size = self.size.get()
        Settings.alpha = float(self.alpha.get())
        Settings.ht1 = self.ht1.get()
        Settings.ht2 = self.ht2.get()
        Settings.api = self.apivar.get()
        Settings.apikey = self.apikey.get()
        Settings.model = self.model.get()
        writeCfg()
        tkinter.messagebox.showinfo(message="保存成功")

def buttonClick(button):
    root.state('icon')
    sleep(0.1)
    filename = 'temp.png'
    im = ImageGrab.grab()
    im.save(filename)
    im.close()
    image = Image.open(filename)
    image = image.convert("RGB")
    enhancer = ImageEnhance.Color(image)
    enhanced_image = enhancer.enhance(3)
    enhanced_image.save(filename)
    w = getAreainfo(filename)
    button.wait_window(w.top)
    root.state('normal')
    os.remove(filename)

def monitor():
    global running, display
    ocr = OCR()
    display = SubtitleApp(root)
    while True:
        if keyboard.is_pressed(Settings.ht1):
            ImageGrab.grab((captureSize.left, captureSize.top, captureSize.right, captureSize.bottom)).save('now.png')
            text = ocr.readText("now.png")
            print(text)
            reply = translator.translate(text)
            print(reply)
            display.update_subtitle(reply)
        elif keyboard.is_pressed(Settings.ht2):
            print('Quit!')
            display.root.withdraw()
            tkinter.messagebox.showinfo(message="已关闭")
            root.title("GalTranslator")
            running = False
            break

def writeCfg():
    config = f'''# 字幕大小(宽*高)
size: "{Settings.size}"
# 字幕透明度 0-1 越小越透明 不过tkinter上的控件也会随之透明
alpha: {Settings.alpha}
# 截图热键
captureHotkey: "{Settings.ht1}"
# 停止热键
pauseHotkey: "{Settings.ht2}"
# 是否启用Api模式(保存后重启生效)
ApiMode: {Settings.api}
# ApiKey
ApiKey: "{Settings.apikey}"
# 模型名称
Model: "{Settings.model}"'''
    open('config.yml', 'w', encoding="utf-8").write(config)

def loadCfg():
    default_config = '''# 字幕大小(宽*高)
size: "500x200"
# 字幕透明度 0-1 越小越透明 不过tkinter上的控件也会随之透明
alpha: 0.5
# 截图热键
captureHotkey: "w"
# 停止热键
pauseHotkey: "q"
# 是否启用Api模式(保存后重启生效)
ApiMode: false
# ApiKey
ApiKey: "Put your api key here if you enable apimode"
# 模型名称
Model: "gpt-3.5-turbo"'''
    while True:
        try:
            config = safe_load(open('config.yml', 'r', errors='ignore', encoding="utf-8"))
            Settings.size = config["size"]
            Settings.alpha = float(config["alpha"])
            Settings.ht1 = config["captureHotkey"]
            Settings.ht2 = config["pauseHotkey"]
            Settings.api = bool(config["ApiMode"])
            Settings.apikey = config["ApiKey"]
            Settings.model = config["Model"]
            break
        except:
            print("加载配置文件失败,写入默认配置中....")
            open('config.yml', 'w', encoding="utf-8").write(default_config)
            sleep(2)

def run():
    global running
    if not captureSize.top:
        tkinter.messagebox.showerror(title="错误", message="你没有选择截图区域!")
    elif running:
        tkinter.messagebox.showwarning(title="警告", message="程序已经在运行中！不要重复点击!")
    else:
        running = True
        root.title("GalTranslator - Running")
        Thread(target=monitor, daemon=True).start()

if __name__ == "__main__":
    loadCfg()
    if Settings.api:
        translator = apitranslator()
    else:
        translator = translator()
    root = tkinter.Tk()
    root.title("GalTranslator")
    root.geometry("100x150")
    root.resizable(False, False)
    button1 = tkinter.Button(root, text='选择截图区域', command=lambda: buttonClick(button1))
    button1.place(x=10, y=10, width=80, height=30)
    button2 = tkinter.Button(root, text='设置', command=SettingsApp)
    button2.place(x=10, y=50, width=80, height=30)
    button3 = tkinter.Button(root, text='启动！', command=run)
    button3.place(x=10, y=90, width=80, height=30)
    root.mainloop()


