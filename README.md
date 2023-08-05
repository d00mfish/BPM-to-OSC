# BPMtoOSC
Finally an easy, reliable and free way to keep the Resolume BPM in sync.
Just open the program, enter your resolume IP, set your audio input and hit start!

Since I was looking for something like this to avoid standing there the whole night smashing the spacebar and couldn't find anything samiliar, especially for free, I too matters into my own hands.
The app detects the beats per minute from an audio input and sending (custom) OSC commands to set the BPM-Counter inside Resolume (or any other LJ / VJ Software with OSC input).


If you want to change the OSC commands that are sent or any problems occur, edit or delete the
`%Appdata%\Roaming\BPMtoOSC\lastsession.ini` file.


<a href="url"><img src="https://user-images.githubusercontent.com/8715042/204784228-d0d6669f-5fe1-4689-aa9a-840369e1eebe.gif" align="center" width="500" ></a>


In case you want to edit the code yourself, make sure to use Python 3.9.13 and the package-versions defined in the requirements.txt file.
The beat detection itself was inspired and relies on the work from [DrLuke](https://github.com/DrLuke/aubio-beat-osc).
