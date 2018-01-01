@ECHO OFF
python "%USERPROFILE%\Documents\GitHub\soultitanium-radio-show\Python\RenderShow.py" --projectpath "%CD%" --renderpath "%USERPROFILE%\Documents\REAPER Media\Soul-Titanium" --assetspath "%USERPROFILE%\Documents\REAPER Media\Soul-Titanium\Show Assets" --stations "KTKE,KKJZ,Web" --scriptversion 3 --projectfile "show-master-template.RPP" --renderformat mp3
pause