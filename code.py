import board
import displayio
import digitalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_button import Button
import adafruit_touchscreen
from adafruit_display_shapes.roundrect import RoundRect
import time
from adafruit_progressbar import ProgressBar
from adafruit_display_shapes.rect import Rect

initialgrid = 6.0
grindDelay = 0.4

display = board.DISPLAY
font = bitmap_font.load_font("/fonts/Arial-16.bdf")

grindctl = digitalio.DigitalInOut(board.D3)
grindbtn = digitalio.DigitalInOut(board.D4)

grindctl.direction = digitalio.Direction.OUTPUT

grindbtn.direction = digitalio.Direction.INPUT
grindbtn.pull = digitalio.Pull.DOWN

screen_width = 320
screen_height = 240
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000),
                                                   (5800, 57000)),
                                      size=(screen_width, screen_height))

rootgroup = displayio.Group(max_size=10)
rootgroup.append(Rect(x=0, y=0, width=320, height=240, fill=0xAAAAFF))
rootgroup.append(label.Label(font, text="Welcome",
                             color=0xFFFFFF, x=120, y=120))

# Show it
display.show(rootgroup)


class SubScreen:

    def __init__(self):
        self.buttons = []
        self.subscreens = []
        self.dgroup = displayio.Group(max_size=20)

    def translate(self, touch):
        return [touch[0] - self.dgroup.x, touch[1] - self.dgroup.y, touch[2]]

    def checkButtons(self, touch):
        translated = self.translate(touch)
        touched = False
        for b in self.buttons:
            btn = b["button"]
            if b["enabled"] == True and btn.contains(translated):
                touched = True
                b["callback"]()
        for s in self.subscreens:
            if s.checkButtons(translated):
                touched = True
        return touched

    def addButton(self, x, y, w, h, label, callback, **kwargs):
        btn = Button(x=x, y=y, width=w, height=h, label=label,
                     label_font=font, selected_fill=0x008800)
        self.buttons.append(
            {"button": btn, "callback": callback, "enabled": False})
        for b in self.buttons:
            bt = b["button"]
            bid = id(bt)
        return btn

    def showButton(self, button):
        self.dgroup.append(button)
        for b in self.buttons:
            btn = b["button"]
            if btn is button:
                b["enabled"] = True

    def hideButton(self, button):
        self.dgroup.remove(button)
        for b in self.buttons:
            btn = b["button"]
            if btn is button:
                b["enabled"] = False

    def addSubscreen(self, subscreen):
        self.dgroup.append(subscreen.dgroup)
        self.subscreens.append(subscreen)


class Screen(SubScreen):

    def __init__(self):
        super(Screen, self).__init__()
        self.touchClear = True
        self.active = True
        self.buttonState = False

    def loop(self):
        return True

    def grindButton(self):
        pass

    def show(self):
        self.active = True
        savedGroup = rootgroup[1]
        rootgroup.pop()
        rootgroup.append(self.dgroup)
        while self.loop():
            touch = ts.touch_point
            if touch and touch[2] > 30000:
                #print(f"Point {touch}")
                if self.touchClear == True:
                    self.touchClear = False
                    if not self.checkButtons(touch):
                        self.touchClear = True
            else:
                self.touchClear = True

            if self.buttonState != grindbtn.value:
                self.buttonState = grindbtn.value
                if self.buttonState == True:
                    self.grindButton()

        rootgroup.remove(self.dgroup)
        rootgroup.append(savedGroup)


class GrindSettings(SubScreen):

    def __init__(self, x, y, amount, text, setGrind):
        super(GrindSettings, self).__init__()
        self.setGrind = setGrind
        self.dgroup.x = x
        self.dgroup.y = y
        self.grindAmount = amount
        self.selectButton = self.addButton(
            10, 0, 140, 100, text, self.select, fill_color=0xAAFFAA)
        self.showButton(self.selectButton)
        self.showButton(self.addButton(10, 110, 40, 40, "-", self.minus))
        self.showButton(self.addButton(110, 110, 40, 40, "+", self.plus))
        self.selected = False

        self.grindLabel = label.Label(
            font, text=str(self.grindAmount), color=0xFFFFFF)
        self.grindLabel.x = 70
        self.grindLabel.y = 130
        self.dgroup.append(self.grindLabel)

    def plus(self):
        self.grindAmount += 1
        if(self.grindAmount > 30):
            self.grindAmount = 30
        self.grindLabel.text = str(self.grindAmount)
        if(self.selected):
            self.setGrind(self, self.grindAmount)

    def minus(self):
        self.grindAmount -= 1
        if(self.grindAmount < 0):
            self.grindAmount = 0
        self.grindLabel.text = str(self.grindAmount)
        if(self.selected):
            self.setGrind(self, self.grindAmount)

    def select(self):
        self.selected = True
        self.selectButton.selected = True
        #self.selectButton.fill_color = 0xAAFFAA
        self.setGrind(self, self.grindAmount)

    def deselect(self):
        self.selected = False
        self.selectButton.selected = False
        #self.selectButton.fill_color = 0xFFFFFF


class MainScreen(Screen):

    def __init__(self):
        super(MainScreen, self).__init__()
        self.grindAmount = 19

        self.showButton(self.addButton(10, 190, 140, 40, "Setup", self.setup))
        self.showButton(self.addButton(170, 190, 140, 40, "Grind", self.grind))

        self.single = GrindSettings(0, 10, 9, "Single", self.grindCallback)
        self.double = GrindSettings(160, 10, 19, "Double", self.grindCallback)

        self.addSubscreen(self.single)
        self.addSubscreen(self.double)

        self.double.select()

        self.prog = SetupScreen()
        self.grindScreen = GrindScreen()

    def grindCallback(self, control, amount):
        if(control is self.single):
            self.double.deselect()
        if(control is self.double):
            self.single.deselect()
        self.grindAmount = amount

    def setup(self):
        self.prog.show()

    def grind(self):
        self.grindScreen.grindGrams(self.grindAmount)
        self.grindScreen.show()

    def grindButton(self):
        self.grind()


class ProgressScreen(Screen):

    def __init__(self):
        super(ProgressScreen, self).__init__()

        self.bar = ProgressBar(x=0, y=0, width=300, height=30, progress=0.0,
                               bar_color=0x00AA00, outline_color=0xFFFFFF, stroke=3)
        self.bargroup = displayio.Group(max_size=10, x=10, y=210)
        self.bargroup.append(self.bar)

        self.cancelButton = self.addButton(
            120, 160, 80, 40, "Cancel", self.cancel)

        self.progress = 0
        self.grinding = False
        self.startTime = 0.0
        self.endTime = 0.0

    def setProgress(self, progress):
        self.progress = progress
        self.bar.progress = progress / 100

    def cancel(self):
        self.stopGrind()

    def grindFor(self, seconds):
        print(f"Running for {seconds + grindDelay}s")
        self.startTime = time.monotonic()
        self.endTime = self.startTime + seconds + grindDelay
        self.startGrind()

    def startGrind(self):
        grindctl.value = True
        self.bar.progress = 0.0
        self.dgroup.append(self.bargroup)
        self.dgroup.append(self.cancelButton)
        self.grinding = True

    def stopGrind(self):
        grindctl.value = False
        self.dgroup.remove(self.bargroup)
        self.dgroup.remove(self.cancelButton)
        self.grinding = False

    def doneGrind(self):
        pass

    def loop(self):
        if self.grinding:
            if time.monotonic() > self.endTime:
                self.stopGrind()
                self.doneGrind()
            else:
                total = self.endTime - self.startTime
                me = time.monotonic() - self.startTime
                self.setProgress(me / total * 100)
        return self.active


class SetupScreen(ProgressScreen):

    def __init__(self):
        super(SetupScreen, self).__init__()
        self.stage = 0
        self.startButton = self.addButton(
            100, 10, 120, 40, "Start", self.start)
        self.topupButton = self.addButton(
            100, 10, 120, 40, "Top up", self.start)

        self.grams = 100
        self.rate = 300

        ll = 70
        rl = 210
        tt = 70
        bt = 110

        self.gramsUp = self.addButton(ll, tt, 40, 40, "+", self.gUp)
        self.gramsDown = self.addButton(ll, bt, 40, 40, "-", self.gDown)
        self.milisUp = self.addButton(rl, tt, 40, 40, "+", self.mUp)
        self.milisDown = self.addButton(rl, bt, 40, 40, "-", self.mDown)

        self.gLabel = label.Label(font, text=str(self.grams/10), x=130, y=110)

        self.showButton(self.startButton)

    def gUp(self):
        self.grams += 10
        self.gLabel.text = str(self.grams/10)

    def gDown(self):
        self.grams -= 10
        self.gLabel.text = str(self.grams/10)

    def mUp(self):
        self.grams += 1
        self.gLabel.text = str(self.grams/10)

    def mDown(self):
        self.grams -= 1
        self.gLabel.text = str(self.grams/10)

    def saveValue(self):
        with open("/rate.txt", "w") as fp:
            fp.write('{0:f}\n'.format(self.rate))
            fp.flush()

    def start(self):
        if(self.stage == 0):
            self.dgroup.remove(self.startButton)
            self.grindFor(initialgrid)
        elif(self.stage == 1):
            self.rate = initialgrid / (self.grams / 10)
            self.saveValue()
            self.dgroup.remove(self.topupButton)
            runfor = (19 - (self.grams / 10)) * self.rate
            self.grindFor(runfor)

    def grindButton(self):
        self.start()

    def doneGrind(self):
        if self.stage == 0:
            self.dgroup.append(self.topupButton)
            self.stage = 1
            self.showButton(self.gramsUp)
            self.showButton(self.gramsDown)
            self.showButton(self.milisUp)
            self.showButton(self.milisDown)
            self.dgroup.append(self.gLabel)
        elif self.stage == 1:
            self.dgroup.append(self.startButton)
            self.stage = 0
            self.active = False
            self.hideButton(self.gramsUp)
            self.hideButton(self.gramsDown)
            self.hideButton(self.milisUp)
            self.hideButton(self.milisDown)
            self.dgroup.remove(self.gLabel)


class GrindScreen(ProgressScreen):

    def __init__(self):
        super(GrindScreen, self).__init__()
        self.rate = 0.0

    def doneGrind(self):
        self.active = False

    def loadValue(self):
        with open("/rate.txt", "r") as fp:
            self.rate = float(fp.readline())
            print(f"Got rate {self.rate}")

    def grindGrams(self, grams):
        self.loadValue()
        self.grindFor(self.rate * grams)


ms = MainScreen()
ms.show()
