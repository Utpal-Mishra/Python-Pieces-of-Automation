import requests
import json

def send_sms(number, message):
    url = 'https://www.fast2sms.com/dev/bulk'
    params = {
        'authorization' : 'wJ06GUQCbVkDd2FS7viTsLEaRAjgXlmuyH145hqIO9KfWNx8zpvuZ8wUkK4Mf65oHeArjmzXnBWxDCpt',
        'sender_id': 'FSTSMS',
        'message': message,
        'language': 'english',
        'route': 'p',
        'numbers': number
    }
    
    response = requests.get(url, params=params)
    dic = response.json()
    print(dic)
    return dic.get('return')
    

import pyttsx3
import speech_recognition as sr 

#choose = int(input("SETTINGS:\n1. Find Covid Statistics\n\nOption: \t"))
engine = pyttsx3.init()
engine.say("Sir, what can I do for you?")
engine.runAndWait()

# Initialize recognizer class (for recognizing the speech)
r = sr.Recognizer()

# Reading Microphone as source
# listening the speech and store in audio_text variable

with sr.Microphone() as source:
    print("Please, Speak now: ")
    audio_text = r.listen(source)
    print("Gotcha, thanks!!!")
# recoginize_() method will throw a request error if the API is unreachable, hence using exception handling
    
    try:
        # using google speech recognition
        print("Text: " + r.recognize_google(audio_text))
        text = r.recognize_google(audio_text)
    except:
         engine.say("Sorry Sir, I did not get that")
         engine.runAndWait()

message = text.split('message')[1].split('to')[0].strip()
print("Message: ", message)
#message = input("Message: ")

number = int(text.split('number')[1].strip().replace(" ", ""))
print("Number: ", number)
#number = input("Enter Number: ")

send_sms(number, message)    