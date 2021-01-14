import pyttsx3

engine = pyttsx3.init()
engine.say("Good Morning, Sir.")
engine.runAndWait()

choose = int(input("SETTINGS:\n1. Change the rate of speech\n2. Change the volume of speech\n3. Change voice\n4. Exit\n\nOption: \t"))

if choose == 1:
    change = pyttsx3.init()
    change.say("Sure, Sir. What I do?")
    change.runAndWait()
    #RATE
    rate = engine.getProperty('rate')          # getting details of current speaking rate
    #print(rate)         
    ratechange = input("Rate: ")               # printing current voice rate
    change.setProperty('rate', ratechange)     # setting up new voice rate
    #change = pyttsx3.init()
    change.say("Is my voice clearer now?")
    change.runAndWait()
    while(input("") == "No"):
            #rate = engine.getProperty('rate')          # getting details of current speaking rate
            #print(rate)                                # printing current voice rate
            ratechange = input("Rate: ")   
            change.setProperty('rate', ratechange)      # setting up new voice rate
            #change = pyttsx3.init()
            change.say("Is my voice clearer now?")
            change.runAndWait()
            if input("") == "Yes":
                    #engine = pyttsx3.init()
                    engine.setProperty('rate', ratechange) 
                    engine.say("Perfect, Sir!")
                    engine.runAndWait()
                    break
if choose == 2:
    change = pyttsx3.init()
    change.say("Sure, Sir. What I do?")
    change.runAndWait()
    #VOLUME
    volume = engine.getProperty('volume')    # getting to know current volume level (min=0 and max=1)
    #print (volume)                          # printing current volume level
    volumechange = input("Volume: ")               
    change.setProperty('volume', volumechange)     # setting up volume level  between 0 and 1
    #change = pyttsx3.init()
    change.say("Is my voice clearer now?")
    change.runAndWait()
    while(input("") == "No"):
            #volume = engine.getProperty('volume')   # getting to know current volume level (min=0 and max=1)
            #print (volume)                          # printing current volume level
            volumechange = input("Volume: ")               
            change.setProperty('volume', volumechange)     # setting up volume level  between 0 and 1
            #change = pyttsx3.init()
            change.say("Is my voice clearer now?")
            change.runAndWait()
            if input("") == "Yes":
                    #engine = pyttsx3.init()
                    engine.setProperty('volume', volumechange) 
                    engine.say("Perfect, Sir!")
                    engine.runAndWait()
                    break
if choose == 3:
    engine.say("Sure, Sir. What I do?")
    engine.runAndWait()
    #VOICE
    
    voices = engine.getProperty('voices')
    
    if input("") == "Female":
   # getting details of current voice
            engine.setProperty('voice', voices[1].id)  # changing index, changes voices. 1 for female
            engine.say("Voice change to Female")
            engine.runAndWait()
    if input("") == "Male":
            engine.setProperty('voice', voices[0].id)  # changing index, changes voices. 0 for male
            engine.say("Voice change to Male")
            engine.runAndWait()
            

#engine.say("Hello World!")
engine.say('My current speaking rate is ' + str(rate) + 
           'and I am speaking at ' + str(volume*100)+ " percent volume")
engine.runAndWait()
engine.stop()

"""
"Saving Voice to a file"
# On linux make sure that 'espeak' and 'ffmpeg' are installed
#engine.save_to_file('Hello World', 'test.mp3')
#engine.runAndWait()
"""
"""
from gtts import gTTS 
  
# This module is imported so that we can  
# play the converted audio 
import os 
  
# The text that you want to convert to audio 
mytext = 'Welcome to geeksforgeeks!'
  
# Language in which you want to convert 
language = 'en'
  
# Passing the text and language to the engine,  
# here we have marked slow=False. Which tells  
# the module that the converted audio should  
# have a high speed 
myobj = gTTS(text=mytext, lang=language, slow=False) 
  
# Saving the converted audio in a mp3 file named 
# welcome  
myobj.save("welcome.mp3") 
  
# Playing the converted file 
os.system("mpg321 welcome.mp3") 
"""