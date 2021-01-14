import pywhatkit
import speech_recognition as sr
import pyttsx3

engine = pyttsx3.init()

# Initialize recognizer class (for recognizing the speech)
r = sr.Recognizer()

# Reading Microphone as source
# listening the speech and store in audio_text variable
with sr.Microphone() as source:
    r.adjust_for_ambient_noise(source)
    audio_text = r.listen(source)
    
    try:
        # using google speech recognition
        print("Text: " + r.recognize_google(audio_text))
        text = r.recognize_google(audio_text)
                
        if text == "Friday":
            engine.say("Yes, Sir. What can I do for you?")
            engine.runAndWait()
    except:
        engine.say("Sorry Sir, I did not get that")
        

pywhatkit.sendwhatmsg('+91##########', 'Gotcha!!!', 'hr', 'min')