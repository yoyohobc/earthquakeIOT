from socket import*
import os
import requests
import requests.packages.urllib3
import datetime
import time
import json
import Adafruit_ADXL345
import RPi.GPIO as GPIO

iothost="iot.cht.com.tw"

iotkey="DKAATHUUHZU3A3UTGU"
device="13998539789"

#參數調整
standard = 0.0255
G=256
LED_PIN = 26

client = None

newData = False

requests.packages.urllib3.disable_warnings()

accel = Adafruit_ADXL345.ADXL345()
max_x=0
max_y=0
max_z=0
print('按 Ctrl-C 結束程式 ')
print('載入中...')
#參數校正功能
def adjustment():
    print('校正中...')
    ajx=0
    ajy=0
    ajz=0
    for num in range(0,20):
        # Read the X, Y, Z axis acceleration values and print them.
        x, y, z = accel.read()
        ajx+=x
        ajy+=y
        ajz+=z
        # Wait half a second and repeat.
        time.sleep(0.25)
    ajx/=20
    ajy/=20
    ajz/=20
    ajx=int(ajx)
    ajy=int(ajy)
    ajz=int(ajz)
    #print('X={0}, Y={1}, Z={2}'.format(ajx, ajy, ajz))
    print('校正完成!')
    return ajx,ajy,ajz

#換算G值並上傳至IOT
def PGA(sec):
    # Read the X, Y, Z axis acceleration values and print them.
    x, y, z = accel.read()
    x-=ajx
    y-=ajy
    z-=ajz
    x/=G
    y/=G
    z/=G
    x=round(x,4)
    y=round(y,4)
    z=round(z,4)
    print('X={0}G, Y={1}G, Z={2}G'.format(x, y, z))
    rawdatas = [{"id":"x","save":True,"value":[format(x)]},{"id":"y","save":True,"value":[format(y)]},{"id":"z","save":True,"value":[format(z)]}]
    headers = {"accept": "application/json","CK": iotkey}
    url="https://"+iothost+"/iot/v1/device/"+device+"/rawdata"
    try:
        response = requests.post(url, data=json.dumps(rawdatas), headers=headers, timeout=1)
    except requests.exceptions.Timeout:
        print('讀取or連線超時')
    time.sleep(sec)
    #print(response.status_code)
    maxPGA(x,y,z)
    return x,y,z

#上傳單一值/文字至IOT
def IOTpost(rawdata):
    headers = {"accept": "application/json","CK": iotkey}
    url="https://"+iothost+"/iot/v1/device/"+device+"/rawdata"
    try:
        response = requests.post(url, data=json.dumps(rawdata), headers=headers, timeout=1)
    except:
        print('讀取or連線超時')
#洗白IOT數據
def wipe():
    wipe=' '
    rawdata = [{"id":"MAX","save":True,"value":[format(wipe)]}]
    IOTpost(rawdata)
    rawdata = [{"id":"datetime","save":True,"value":[format(wipe)]}]
    IOTpost(rawdata)
    rawdata = [{"id":"endtime","save":True,"value":[format(wipe)]}]
    IOTpost(rawdata)
    rawdata = [{"id":"level","save":True,"value":[format(wipe)]}]
    IOTpost(rawdata)

#計算x,y,z最大地動加速度
def maxPGA(x,y,z):
    x=abs(x)
    y=abs(y)
    z=abs(z)
    if(x>max_x):
        global max_x
        max_x=x
        rawdata = [{"id":"mx","save":True,"value":[format(max_x)]}]
        IOTpost(rawdata)

    if(y>max_y):
        global max_y
        max_y=y
        rawdata = [{"id":"my","save":True,"value":[format(max_y)]}]
        IOTpost(rawdata)

    if(z>max_z):
        global max_z
        max_z=z
        rawdata = [{"id":"mz","save":True,"value":[format(max_z)]}]
        IOTpost(rawdata)

#上傳最新地震開始時間
def SendTime():
    i = datetime.datetime.now()
    now = i.strftime("%c")
    #print (now)
    rawdate = [{"id":"datetime","save":True,"value":[format(now)]}]
    IOTpost(rawdate)

#上傳最新地震結束時間
def SendTimeEnd():
    i = datetime.datetime.now()
    now = i.strftime("%c")
    #print (now)
    rawdate = [{"id":"endtime","save":True,"value":[format(now)]}]
    IOTpost(rawdate)

#地震級數換算(交通部中央氣象局)&取出三軸最大地動加速度 並上傳至IOT
def E_level(max_x,max_y,max_z):
    global MAX
    if(max_x>max_y and max_x>max_z):
        MAX=max_x
    if(max_y>max_x and max_y>max_z):
        MAX=max_y
    if(max_z>max_x and max_z>max_y):
        MAX=max_z
    global Level
    if(MAX>0.0255 and MAX<0.081):
        Level="4級"	
    elif(MAX>0.081 and MAX<0.255):
        Level="5級"	
    elif(MAX>0.255 and MAX<0.408):
        Level="6級"	
    else:
        Level="7級"	
    rawdata = [{"id":"level","save":True,"value":[format(Level)]}]
    IOTpost(rawdata)
    rawdata = [{"id":"MAX","save":True,"value":[format(MAX)]}]
    IOTpost(rawdata)

#警報及地震時間計算
def beep():
    a=10
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    while  a>0:
        print("地震警報!")
        GPIO.output(LED_PIN,GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(LED_PIN,GPIO.LOW)
        x,y,z=PGA(0)
        x=abs(x)
        y=abs(y)
        z=abs(z)
        if(x<0.008 and y<0.008 and z<0.008):
            a-=1
            if(MAX<max_x or MAX<max_y or MAX<max_z):
                SendTimeEnd()
                E_level(max_x,max_y,max_z)
            else:
                continue
    GPIO.cleanup()
    global max_x
    max_x=0
    global max_y
    max_y=0
    global max_z
    max_z=0

#主程式
wipe()
while True:
    print('請平放儀器，五秒後開始校正')
    time.sleep(5)
    ajx,ajy,ajz=adjustment()
    for num in range(0,1200):
        MAX=0
        x,y,z=PGA(0.5)
        if(x>standard or x<-standard or y>standard or y<-standard or z>standard or z<-standard):
            SendTime()
            beep()
    GPIO.cleanup()
    
