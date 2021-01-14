import speech_recognition as sr
import pyttsx3
import pandas as pd
import numpy as np
import pickle

#Directory = {}

"""engine = pyttsx3.init()

# Initialize recognizer class (for recognizing the speech)
r = sr.Recognizer()

# Reading Microphone as source
# listening the speech and store in audio_text variable
with sr.Microphone() as source:
    print("Please, Speak now: ")
    #r.adjust_for_ambient_noise(source, duration=0.2) 
    audio_text = r.listen(source)
    #print("Gotcha, thanks!!!")
    
    try:
        #print("Talk")  
        # using google speech recognition
        print("Text: " + r.recognize_google(audio_text))
        text = r.recognize_google(audio_text)
        
        engine.say("Sure, Sir. Opening Phone Directory")
        engine.runAndWait()
        print("Recorded!!!")
    except:
         print("Sorry, I did not get that")
    

r = sr.Recognizer()

# Reading Microphone as source
# listening the speech and store in audio_text variable
with sr.Microphone() as source:
    print("\nAdd Record: ")
    r.adjust_for_ambient_noise(source, duration=0.2) 
    audio_text = r.listen(source)
    #print("Gotcha, thanks!!!")
    
    try:
        #print("Talk")  
        # using google speech recognition
        print("Text: " + r.recognize_google(audio_text))
        text = r.recognize_google(audio_text)
        
        Directory[text.split('name')[1].replace(" ", "").strip()] = text.split('number')[1].strip().replace(" ","")[0:10]
        
        engine.say("New contact " + text.split('name')[1].replace(" ", "").strip() + " added")
        engine.runAndWait()
        
        print("Recorded!!!")
        print(Directory)
    
        
    except:
         print("Sorry, I did not get that")"""
         
Directory = [{"Name": "XXXXX", "Number": '##########'}, 
              {"Name": "YYYYY", "Number": "##########"}, 
              {"Name": "ZZZZZ", "Number": "##########"}, 
              {"Name": "WWWWW", "Number": "##########"}]

Directory = pd.DataFrame.from_dict(Directory)

Directory.index = np.arange(1, len(Directory) + 1)

Directory.to_csv("Directory.csv")

#open a file when we want to store the data
file = open('Directory.pkl', 'wb')

#dump information to file
pickle.dump(Directory, file)