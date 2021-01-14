from covid_india import states
import pandas as pd

#print(states.getdata('Total')

States =[]
Total = []
Active = []
Cured = []
Death = []

for i, (k, v) in enumerate(states.getdata().items()): 
    States.append(k)
    Total.append(v["Total"])
    Active.append(v["Active"])
    Cured.append(v["Cured"])
    Death.append(v["Death"])

CovidIndia = pd.DataFrame({"States": States,
                           "Total": Total,
                           "Active": Active,
                           "Cured": Cured,
                           "Death": Death}).set_index("States")

from covid import Covid

CovidWorld = pd.DataFrame(Covid().get_data()).sort_values("country").drop(['id', 'last_update'], axis=1).dropna()
CovidWorld

#!conda install -c conda-forge folium=0.5.0 --yes
import folium
import webbrowser
from geopy.geocoders import Nominatim
#from IPython.display import Image 
#from IPython.core.display import HTML 
from IPython.display import display

address = 'India'

geolocator = Nominatim(user_agent="ny_explorer")
location = geolocator.geocode(address)
latitude = location.latitude
longitude = location.longitude
print('The geograpical coordinate of India are {}, {}.'.format(latitude, longitude))

Map = folium.Map(location=[latitude, longitude], zoom_start=2)
incidents = folium.map.FeatureGroup()

# loop through the 100 crimes and add each to the incidents feature group
for lat, lng, in zip(CovidWorld.latitude, CovidWorld.longitude):
    incidents.add_child(
        folium.CircleMarker(
            [lat, lng],
            radius=5, # define how big you want the circle markers to be
            color='yellow',
            fill=True,
            fill_color='blue',
            fill_opacity=0.6
        )
    )

# add pop-up text to each marker on the map
latitudes = list(CovidWorld.latitude)
longitudes = list(CovidWorld.longitude)
labels = list(CovidWorld["country"])

for lat, lng, label in zip(latitudes, longitudes, labels):
    folium.Marker([lat, lng], popup=label).add_to(Map)    
    
# add incidents to map
Map.add_child(incidents).save("CovidMap.html")
#webbrowser.open("CovidMap.html")
#display(Map)

import pyttsx3
import speech_recognition as sr 

#choose = int(input("SETTINGS:\n1. Find Covid Statistics\n\nOption: \t"))
engine = pyttsx3.init()
engine.say("Sir, what should I search for you")
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
         print("Sorry, I did not get that")

cc = int(CovidWorld[CovidWorld['country']==text.split()[-1]]['confirmed'])
ac = int(CovidWorld[CovidWorld['country']==text.split()[-1]]['active'])
dc = int(CovidWorld[CovidWorld['country']==text.split()[-1]]['deaths'])
rc = int(CovidWorld[CovidWorld['country']==text.split()[-1]]['recovered'])

engine.say(r.recognize_google(audio_text).split()[-1] + " has witnessed " + str(ac) + " cases with " + str(round(ac*100/cc)) + " percent active cases, " + str(round(dc*100/cc)) + " percent deaths and " + str(round(rc*100/cc)) + " percent recovery")
engine.runAndWait()