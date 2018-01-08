# -*- coding: utf-8 -*-
#****************************************************************************************
#****************************************************************************************
#**   Reaper Radio Show Rendering Utility (RenderShow.py)
#**
#**   Copyright (C) 2017 - Mike Soultanian - mike@soultanian.com
#**
#**   This program is free software; you can redistribute it and/or
#**   modify it under the terms of the GNU General Public License
#**   as published by the Free Software Foundation; either version 2
#**   of the License, or (at your option) any later version.
#**
#**   This program is distributed in the hope that it will be useful,
#**   but WITHOUT ANY WARRANTY; without even the implied warranty of
#**   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#**   GNU General Public License for more details.
#**
#**   You should have received a copy of the GNU General Public License
#**   along with this program; if not, write to the Free Software
#**   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#**
#**   This header must appear on all derivatives of this code.
#****************************************************************************************
#****************************************************************************************
#
#v1.0 - Initial release (ported from vbScript)
#
#
#This script is used to render the Soul-Titanium radio show for multiple radio stations.
#The Reaper file is structured in such a way that the station track is automaticically
#populated with station-specific spots instead of having to record them manually.  Also,
#those spots are selected at random from a batch of station spots so that it doesn't
#sound the same every week.
#
#A few things to note - the reason that there is a marker and an associated empty ITEM
#in the template is so that the script is modifying an ITEM that is generated instead
#of writing it how I think it should be written.  While the ITEM format probably won't
#change any time soon, I don't want to assume it should be written one way and then
#there is a software change and the script no longer works.  I figured it's a bit safer
#this way.  This is also why there is a position tolerance value that checks that the
#marker is too far away from it's associated ITEM.
#

#INSTRUCTIONS
#- USING "IMPORT" MATCHING TO FIGURE OUT WHICH SPOTS TO IMPORT
#- THE ITEM NEEDS TO MATCH THE MARKER
#- -r for random spot
#- write how the options work -r for random, -c for commercial -rc (random and commercial, etc)
#- how are random files to be named?  explain that here
# - for imported audio that isn't random, the audio file must match the name of the marker/item except for IMPORT prefix and options

#confirmed instructions
# - moving markers will update the positions of processed spots
# - options are set in the markers, not the spot name
# - marker name must match the item, except for the item name - that shouldn't include options

#TODO:
# - maybe make the IMPORT an option?  -I?
# - make commercials station-specific (and maybe have global ones, too?)
# - for the template that's generated every time, reset the markers back to their original
#	which is where the items are (because I'm not moving them)
# - need to figure out what to do if assets are repeatedly copied when the script is done - should
#	the script delete the contents, or is that going to break what was in the original render.
#	Need to be careful here...
# - notify user if and IMPORT spot's associated marker isn't found (stop script?)
# - need to gracefully handle a spot-marker mismatch (name of spot doesn't exactly match
#	associated marker)
# - still need to figure out how commercials get brough in - are they recorded and then
#	placed in the show folder - probably, because they can't go in the assets folder as
#	that's used for all the shows being rendered
# - make it so when it's parsing through ITEMs that it finds the associated marker (or
#	works the other way around and finds the ITEM associated with a marker), and then
#	uses the time specified in the marker to move the ITEM to where it needs to go.  If
#	it doesn't find the marker/ITEM match, it generates an error
# - might be related to the above - don't use the tolerance, instead match the marker
#	 name to the ITEM
# - think about adding a processing indicator to the name of the marker and ITEM so the
#   script knows whether it should process or ignore an item
# - make "norender" option something that's selectable instead of having to put it in
#	the batch file
# - need to create two rendermodes - initial and replay - this way the initial mode
#	will include commercials and the replay mode will ignore commercials
# - need to create additional markers for commercials that are only included for
#	the initial render mode
# - will need to create special tags so that the system knows that the marker is a
#	commercial and not a regular spot
# - clean up the paths because lots are hard-coded
# - document the purpose for the tolerance - decide if it's actually needed
# - Update instructions as I keep forgetting how the script knows when it's supposed
#   to process an ITEM - does it need an associated marker, is there a keyword it's
#   looking for, etc?  Right now I keep forgetting and I have to read the code to
#   figure out what I did.
# - currently script copies all the spots from the assets folder to the project folder
#	and I'm guessing that's good because you want to keep whatever assets were used.  Now
#	if you render a replay, you'll want to probably copy new assets as the station might
#	have made changes to their stuff... this will be interesting how to handle replays



import winsound
import sys
import os
import re
import pathlib
import random
import wave
import contextlib
import shlex
import shutil
import subprocess
import argparse

#these values need to be modified to match the Reaper audio configuration
intRequiredBatchVersion = 3 #required version of the batch file
conPathToReaper = "C:\\Program Files\\REAPER (x64)\\reaper.exe"
blnUseCLArgs = True #use commandline arguments or override with test arguments in code?

#-Do not change anything below here---------------------------------------------------------------------'
RenderMP3 = 1
RenderWAV = 2
conRenderFilePrefix = "  RENDER_FILE "
conMarkerLabel = "MARKER"
conRenderConfigLabel = "RENDER_CFG"
RenderCfgMP3 = "    bDNwbUABAAABAAAABQAAAP////8EAAAAQAEAAAAAAAA="
RenderCfgWAV = "    ZXZhdxAA"
strTrackNameToFind = "Station VT"
conMarkerOptionDesignator = "-"
conProjectTemplate = "newtemplate"
conSpotPositionTolerance = 5 #how far the spot's position (sec) is allowed to be from the associated marker position
conTemplateDefaultSpotLength = 2 #default length (sec) for the template spots when inserting the silent wav
conSilentWAVFilename = "5-SecondSilence.wav"
conSpotEndSnapOption = "e" #option for when a spot should be snapped to its end instead of the beginning (default)
conSpotRandomOption = "r" #option for when random files are to be used for a spot
conAudioFolderName = "Audio" #name of folder where audio is stored in the script folder and project folder
conRandomSpotsSrcFolder = "Random spots" #folder name where random spots are stored for each station
conITEMProcessKeyword = "IMPORT " #lets  script know that marker/ITEM should be processed - include all whitespaces
conCursorLabel =  "  CURSOR"
conDefaultCursorValue = "  CURSOR 0"
conZoomLabel = "  ZOOM"
conDefaultZoomValue = "  ZOOM 0.13521563292539 0 0"

if not blnUseCLArgs:
	print()
	input("WARNING: SCRIPT IS USING INTERNAL COMMAND-LINE ARGUMENTS!  Press Enter to continue")
	print()

strScriptPath = os.path.abspath(os.path.dirname(sys.argv[0]))
print('Python script directory:\n', strScriptPath) 

#retrieve the arguments from the calling batch file
objCLParser = argparse.ArgumentParser(description="Really cool show processing script")
objCLParser.add_argument("--projectpath", required=True, metavar="[path]", help="path to the Reaper project files to be processed")
objCLParser.add_argument("--renderpath", required=True, metavar="[path]", help="path to where there rendered files should be output")
objCLParser.add_argument("--assetspath", required=True, metavar="[path]", help="path to where the show assets are")
objCLParser.add_argument("--stations", required=True, metavar="[station list]", help="comma separated list of stations to process")
objCLParser.add_argument("--scriptversion", required=True, metavar="[version number]", help="this integer value needs to match the version in the script")
objCLParser.add_argument("--projectfile", required=False, metavar="[reaper project file]", help="bypasses the project file selection menu - only specify file name (i.e. show.RPP)")
objCLParser.add_argument("--renderformat", required=False, metavar="[MP3|WAV]", help="bypasses the render format selection menu")
objCLParser.add_argument("--norender", required=False, action="store_true", help="useful if you only want to generate the project files")
if blnUseCLArgs:
	objCLArgs = objCLParser.parse_args()
else:
	objCLArgs = objCLParser.parse_args(["--projectpath", "C:\\Users\\mike\\Documents\\REAPER Media\\Soul-Titanium\\show xx - DEV TEMPLATE (v3)\\Show",
									"--renderpath", "C:\\Users\\mike\\Documents\\REAPER Media\\Soul-Titanium",
									"--assetspath", "C:\\Users\\mike\\Documents\\REAPER Media\\Soul-Titanium\\Show Assets",
									"--stations", "KtKE   ,    KKJZ   ,Web    ",
									"--scriptversion", "3",
									"--projectfile", "show-master-template.RPP",
									"--renderformat", "mp3",
									"--norender"])

if objCLArgs.projectfile:
	print("Project file:", objCLArgs.projectfile)
if objCLArgs.renderformat.lower() == "mp3" or objCLArgs.renderformat.lower() == "wav":
	print("Render format:", objCLArgs.renderformat)
else:
	print("WARNING: Invalid render format specified on the command-line")
	sys.exit()
	
if objCLArgs.norender:
	print("Rendering DISABLED")
	blnRenderOn = False
else:
	print("Rendering ENABLED")
	blnRenderOn = True

strProjectPath = objCLArgs.projectpath
strRenderOutputPath = objCLArgs.renderpath
strAssetsPath = objCLArgs.assetspath

#check if the project folder exists
if os.path.exists(strProjectPath):
	print("Reaper project folder:\n", strProjectPath)
else:
	print("Project folder specified does not exist:\n", strProjectPath)
	sys.exit()

#check if the render output folder exists
if os.path.exists(strRenderOutputPath):
	print("Render output folder:\n", strRenderOutputPath)
else:
	print("Render output folder specified does not exist:\n", strRenderOutputPath)
	sys.exit()

#clean up the station list provided by the batch file
strStations = objCLArgs.stations.replace(" ", "").lower()

print("Stations from batch file: %s" % strStations)
#convert the string list of station names to process to a list so it's easier to loop through
lstStations = strStations.split(",")

#add template identifier to the list of stations to output a template version of the show
lstStations.append(conProjectTemplate)

#will need to retrieve batch version from batch file
tempbatchversion = objCLArgs.scriptversion
intBatchVersion = int(tempbatchversion)
if intBatchVersion == intRequiredBatchVersion:
	print("Batch version: %i" % intBatchVersion)
else:
	print("Batch file is not the correction version.  Quitting.")
	sys.exit()

#pull the guest DJ name and show number from the path
strParentFolder = str(pathlib.Path(strProjectPath).parent)
strShowNameNum = os.path.basename(strParentFolder)
#split the name and number into a list
lstShowNameNum = strShowNameNum.split("-")
#split the first list element of lstShowNameNum (show ##) and store the second element (number)
strShowNumber = shlex.split(lstShowNameNum[0])[1]
#strip the witespace off of the second element (name) in lstShowNameNum
strDJName = lstShowNameNum[1].strip()

print("DJ name: %s | show number: %s" % (strDJName, strShowNumber))

#retrieve the files from the folder where the batch file is run
lstProjectFolderFiles = [f for f in os.listdir(strProjectPath) if os.path.isfile(os.path.join(strProjectPath, f))]

#pick out the valid reaper files from the file listing
lstProjectFolderFiles = [x.lower() for x in lstProjectFolderFiles]
lstValidFiles = []
for strFileName in lstProjectFolderFiles:
	if ".rpp" in strFileName and not ".rpp-bak" in strFileName:
		lstValidFiles.append(strFileName)

#project file selection menu
if objCLArgs.projectfile:
	#show file name specified on command-line
	strMasterProjectFilePath = os.path.join(strProjectPath,objCLArgs.projectfile)
else:
	#no command-line arguments were specified, show menu
	blnValidSelection = False
	while blnValidSelection != True:
		print()
		for i,f in enumerate(lstValidFiles,start=1):
			print("%i. %s" %(i,f))
	
		strInput = input("Select which Reaper file you'd like to process (default=show.RPP, x=exit): ")
	
		if strInput == "":
			#default to "show.RPP"		
			strMasterProjectFilePath = os.path.join(strProjectPath,"show.RPP")
			blnValidSelection = True
		elif strInput.isnumeric():
			strInput = int(strInput.lower().strip())
			if strInput > 0 and strInput <= len(lstValidFiles):
				#build complete path to the reaper project file		
				strMasterProjectFilePath = os.path.join(strProjectPath,lstValidFiles[strInput-1])
				blnValidSelection = True
			else:		
				print("\nInvalid selection - please make another selection.\n")
		elif strInput == "x":
			sys.exit()
		else:
			print("\nInvalid selection - please make another selection.\n")

	print("\nSelected Reaper project:\n %s\n" % strMasterProjectFilePath)

if objCLArgs.renderformat:
	#render format specified on the command-line
	if objCLArgs.renderformat.lower() == "mp3":
		strRenderExt = ".mp3"
		blnRenderMP3 = True
		strRenderCfg = RenderCfgMP3
	elif objCLArgs.renderformat.lower() == "wav":
		strRenderExt = ".wav"
		blnRenderMP3 = False
		strRenderCfg = RenderCfgWAV
	else:
		print("WARNING: Should never get here - there was a problem")
		sys.exit
else:
	#no command-line arguments where specified, show format selection menu
	blnValidSelection = False
	while blnValidSelection != True:
		print("\nSelect which format you'd like to render to:\n")
		print(str(RenderMP3) + ". MP3")
		print(str(RenderWAV) + ". WAV")
	
		strInput = input("Select render format (default=1): ")
	
		if strInput == "":
			strRenderExt = ".mp3"
			strRenderCfg = RenderCfgMP3
			blnValidSelection = True
		elif strInput.isnumeric:
			strInput = int(strInput.lower().strip())
			if strInput == RenderMP3:
				blnRenderMP3 = True
				blnValidSelection = True
			elif strInput == RenderWAV:
				blnRenderMP3 = False
				blnValidSelection = True
			else:
				print("\nInvalid selection - please make another selection.\n")
		else:
			sys.exit()
	
	print("Selected render config: ", end="")
	if blnRenderMP3:
		print("MP3")
	else:
		print("WAV")
	print()
	
if blnRenderMP3:
	strRenderExt = ".mp3"
	strRenderCfg = RenderCfgMP3
else:
	strRenderExt = ".wav"
	strRenderCfg = RenderCfgWAV
	
intTotalRenderAttempts = 0
intRenderSuccessCnt = 0
intRenderFailureCnt = 0
lstFailedStationRender = []

#delete imported folder if it exists
shutil.rmtree(os.path.join(strProjectPath,"Audio\\Imported"),True)

for strStation in lstStations:
	print("\nProcessing " + strStation + "...")

	#find out how many random files there are for this station
	if strStation != conProjectTemplate:
		#finding random files for the stations, but not the template
		
		strStationRandomWAVPath = os.path.join(strAssetsPath, conAudioFolderName, strStation, conRandomSpotsSrcFolder)
#		print(" Random wav folder:\n",strStationRandomWAVPath)
		#check if the random wav folder exists
		if not os.path.exists(strStationRandomWAVPath):
			print(" random wav folder for %s is missing" % strStation)
			sys.exit()

		#build a list with all the random wavs in the folder
		lstRandomWAVsFilenames = [f for f in os.listdir(strStationRandomWAVPath) if os.path.isfile(os.path.join(strStationRandomWAVPath, f)) and
							re.search(r'\.wav$', f, re.IGNORECASE)]
		
#		print(" Found %i spots in the random audio folder" % (len(lstRandomWAVsFilenames)))
			
	#start parsing through the main project file and open the generated station file for writing
	strStationProjectFilePath = os.path.join(strProjectPath, "show-" + strShowNumber + "-" + strStation + ".RPP")
	with open(strMasterProjectFilePath, "r") as fShowTemplate, \
		open(strStationProjectFilePath, "w") as fOutFile:  
		#start moving line by line through the show template
		dictMarkers = {}
		for strLine in fShowTemplate:
			#find the markers and save them in a dictionary
			if conMarkerLabel.lower() in strLine.lower():
				#the marker label was found, split it into a list

				#let's check to see if it's associated with an importable spot
				if "import" not in strLine.lower():
					#this marker doesn't have the processing keyword so just write this line to the reaper file
					fOutFile.write(strLine)
				else:
					#this MARKER has the processing keyword so let's process it

					#remove the ITEM processing keyword split marker into a list
					lstMarkerDetails = shlex.split( strLine.lower().replace(conITEMProcessKeyword.lower(), "") )

#					print(" Processing: \"%s\"" % lstMarkerDetails[3])
					
					#lstMarkerDetails has the following:
					#	0:marker label, 1:id, 2:position, 3:marker name, ...other stuff I'm not using
					if conMarkerOptionDesignator in lstMarkerDetails[3]:
						#options have been found, let's save them and the marker name
						strMarkerName = lstMarkerDetails[3].split("-")[0].lower()
						strMarkerOptions = lstMarkerDetails[3].split("-")[1]
					else:
						#no options found, just save the marker name
						strMarkerName = lstMarkerDetails[3].lower()
						strMarkerOptions = ""
						
					#store position		
					strMarkerPosition = lstMarkerDetails[2]
					
					#check for duplicate markers
					if strMarkerName not in dictMarkers:
						# this is not a duplicate - save the marker details to a dictionary
						#	{"marker name":["marker position","marker options"]}
						#	options currently are E=end snap, R=Random spot
						dictMarkers[strMarkerName] = [strMarkerPosition,strMarkerOptions]
					else:
						print(" Duplicate marker found")
						sys.exit()
					fOutFile.write(strLine.upper())

			#update the render format with the one selected
			elif conRenderConfigLabel.lower() in strLine.lower():
				fOutFile.write(strLine)
				fOutFile.write(strRenderCfg + "\n")
				#this if is writing two lines to the project file so we'll advance the input project file pointer as well
				next(fShowTemplate)

			#reset the cursor position
			elif conCursorLabel.lower() in strLine.lower():
				fOutFile.write(conDefaultCursorValue + "\n")

			#reset the zoom
			elif conZoomLabel.lower() in strLine.lower():
				fOutFile.write(conDefaultZoomValue + "\n")

			#update the rendered file name
			elif conRenderFilePrefix.lower().strip() in strLine.lower():
				fOutFile.write(conRenderFilePrefix + "\"" + os.path.join(strRenderOutputPath, "show-" + strShowNumber + "-" + strStation + strRenderExt) + "\"\n")
			
			#search for the Station VT track
			elif strTrackNameToFind.lower() not in strLine.lower():
				#station VT track was not found so let's just write the current line
				fOutFile.write(strLine)
			elif strTrackNameToFind.lower() in strLine.lower():
				#we're now inside the Station VT track
				fOutFile.write(strLine)
				lstRandomList = []
				intRandomSpotCnt = 0
				#move through the station vt track until we find the ITEM header
				for strLine in fShowTemplate:
					if "item" not in strLine.lower():
						#item marker not found so just write the current line to the output file
						fOutFile.write(strLine)
					else:
						#ITEM header was found - let's process its elements

						#store how many spaces the ITEM marker is indented to use when writing other elements
						intItemIndent = strLine.lower().find("item")-1
						
						#the for loop we're in advanced the pointer so we need to grab this line and add it to the
						#	list that's going to store each line within the element
						lstItem = []
						lstItem.append(strLine)
						
						#step through all the elements in the ITEM and put them in a list
						for strLine in fShowTemplate:
#							print("%s" % strLine,end="")
							lstItem.append(strLine)
							if ">" in strLine and (len(strLine) - len(strLine.lstrip())) == intItemIndent:
								#end of the ITEM
								break
					
						#now check to make sure all elements are where we expect them to be as a new
						#	version of Reaper might change how ITEM elements are ordered.
						#lstItem reference:
						#	1:position, 3:length, 4: loop, 13:name, 20:file
						
						if "position"  in lstItem[1].lower():
							fltItemPosition = float(shlex.split(lstItem[1])[1])
						else:
							print("ERROR: POSITION element wasn't where it was expected to be!")
							print("Found this instead:",lstItem[1])
							sys.exit()
						
						if "length" in lstItem[3].lower():
							fltItemLength = float(shlex.split(lstItem[3])[1])
						else:
							print("ERROR: LENGTH element wasn't where it was expected to be!")
							print("Found this instead:",lstItem[3])
							sys.exit()
							
						if "loop" in lstItem[4].lower():
							intItemLoop = int(shlex.split(lstItem[4])[1])
						else:
							print("ERROR: LENGTH element wasn't where it was expected to be!")
							print("Found this instead:",lstItem[4])
							sys.exit()

						if "name" in lstItem[13].lower():
							strItemName = shlex.split(lstItem[13])[1].lower()
						else:
							print("ERROR: NAME element wasn't where it was expected to be!")
							print("Found this instead:",lstItem[13])
							sys.exit()
						
						if "file" in lstItem[20].lower():
							strItemFile = shlex.split(lstItem[20])[1]
						else:
							print("ERROR: FILE element wasn't where it was expected to be!")
							print("Found this instead:",lstItem[20])
							sys.exit()

						#let's check to see if this is an importable spot
						if "import" not in strItemName.lower():
							print(" Spot \"%s\" does not contain IMPORT - skipping" % strItemName)
						else:
							#this ITEM has the IMPORT keyword so let's process it

							#check if item name exists in marker dictionary

######### todo check exist in marker ditionary
							
							#remove the item processing keyword
							strItemName = strItemName.replace(conITEMProcessKeyword.lower(), "")

							#store this spot's associated marker options in a variable
							strItemOptions = dictMarkers[strItemName][1].lower()
	#						print(" spot options:", strItemOptions)

							if conSpotEndSnapOption in strItemOptions:
								#this spot's position is snapped to the end of the spot
	#							print( " snapped to end of spot")
								blnEndSnap = True
							else:
								#this spot's position is snapped to the beginning of the spot
	#							print( " snapped to beginning of spot")
								blnEndSnap = False
							
							#update the elements within this spot's ITEM block
							if strStation != conProjectTemplate:
								#check to make sure that this spots ITEM name has an associated marker
								if strItemName.lower() not in dictMarkers.keys():
									print(),print(" This spot (%s) does not have an associated marker" % strItemName)
									sys.exit()

								#update file location stored for this spot
								if conSpotRandomOption in strItemOptions:
									#this is a random spot
									#check to make sure there are enough random files to match the number of spots
									intRandomSpotCnt += 1
									if intRandomSpotCnt > len(lstRandomWAVsFilenames):
										print(" Not enough WAVs in the %s folder to fill all the spots.  Expecting at least %i spots" % (strStation,intRandomSpotCnt))
										print()
										sys.exit()

									#select a random spot but make sure it hasn't been used already
									while True:
										#random number needs to be offset by one because the list of random WAVs starts at 0
										intFileNumber = random.randint(0,len(lstRandomWAVsFilenames)-1)
										if intFileNumber not in lstRandomList:
											lstRandomList.append(intFileNumber)
											break
									
									#build the full path the selected random file
									strWavSrcPath = os.path.join(strAssetsPath, "Audio", strStation, "Random spots",lstRandomWAVsFilenames[intFileNumber])
									strWavSrcFolder = str(pathlib.Path(strWavSrcPath))

									#verify that file has station name in it just to be sure we're not accidentally 
									#pulling ling the wrong files
									if (strStation + "-") not in os.path.basename(strWavSrcPath):
										print(" \"%s\" needs to contain [station hypen] at the beginning of the filename" % os.path.basename(strWavSrcPath))
										sys.exit()
								else:
									#this is general (non-random) spot
									strWavSrcPath = os.path.join(strAssetsPath, "Audio", strStation, "General", strStation + "-" + strItemName + ".wav")
									strWavSrcFolder = str(pathlib.Path(strWavSrcPath).parent)

								#build the path to where the audio assets will be copied
								strWavDestPath = os.path.join(strProjectPath,"Audio\\Imported",strStation,os.path.basename(strWavSrcPath))
								strWavDestFolder = str(pathlib.Path(strWavDestPath).parent)

								lstItem[20] = " "*(intItemIndent+4) + "FILE \"" + strWavDestPath + "\"\n"

								#turn off looping as we don't want the spot to ever to loop if the length is wrong
								lstItem[4] = " "*(intItemIndent+2) + "LOOP 0\n"

								#update the length of the spot
	#							print("item length: %f" % fltItemLength)
	#							print("wav: %s" % strWavSrcPath)
								with contextlib.closing(wave.open(strWavSrcPath,'r')) as f:
									frames = f.getnframes()
									rate = f.getframerate()
									fltWAVDuration = round(frames / float(rate),14)

								lstItem[3] = " "*(intItemIndent+2) + "LENGTH " + str(fltWAVDuration) + "\n"

#								Gonna get rid of this and just place the item where the marker is								
#								
#								#update the position of the spot
#								#check to make sure that the spot position is within a certain distance from the
#								#	position specified by the marker
#								if  blnEndSnap:
#									#this spot's position is snapped to the end of the spot
#									fltItemPositionDiff = abs(float(dictMarkers[strItemName][0]) - fltItemPosition - fltItemLength)
#								else:
#									#this spot's position is snapped to the beginning of the spot
#									fltItemPositionDiff = abs(float(dictMarkers[strItemName][0]) - fltItemPosition)
#		
#								#check that the position is within tolerance, and if so, use that position
#								if fltItemPositionDiff <= conSpotPositionTolerance:
#									#spot is within required distance from marker, so we'll use marker position:
#									if blnEndSnap:
#										#snapped to end of spot
#										fltNewItemPosition = float(dictMarkers[strItemName][0]) - fltWAVDuration
#									else:
#										#snapped to beginning of spot
#										fltNewItemPosition = float(dictMarkers[strItemName][0])
#								else:
#									print("\"%s\" is too far away from where its marker expected it to be (end snap = %s)" % (strItemName, blnEndSnap) )
#									print("Current location: %f\nMarker position: %s\nNew ITEM position based on WAV length: %f\nWAV length: %s\nDifference: %f\nPosition tolerance setting: %s" % (fltItemPosition, dictMarkers[strItemName][0], fltNewItemPosition, fltWAVDuration, fltItemPositionDiff, conSpotPositionTolerance) )
#
#									sys.exit()
#
#								print("\nITEM: %s (end snap: %s)\nLocation of beginning of ITEM: %f\nLocation of end of ITEM: %f\nMarker position: %s\nNew ITEM position based on WAV length: %f\nWAV length: %s\nDifference: %f\nPosition tolerance setting: %s" % (strItemName, blnEndSnap, fltItemPosition,fltItemPosition+fltItemLength, dictMarkers[strItemName][0], fltNewItemPosition, fltWAVDuration, fltItemPositionDiff, conSpotPositionTolerance) )


								if blnEndSnap:
									#snapped to end of spot
									fltNewItemPosition = float(dictMarkers[strItemName][0]) - fltWAVDuration
								else:
									#snapped to beginning of spot
									fltNewItemPosition = float(dictMarkers[strItemName][0])

								lstItem[1] = " "*(intItemIndent+2) + "POSITION " + str(fltNewItemPosition) + "\n"
								
	#							print(" using \"%s\"" % (os.path.basename(strWavSrcPath)))
		
#		getting rid of this - always copying						if blnRenderOn:
#									#rendering is enabled - check if destination folder exists

								if not os.path.exists(strWavDestFolder):
									os.makedirs(strWavDestFolder)
		
								if os.path.isfile(strWavSrcPath) and os.path.exists(strWavSrcPath):
									if not os.path.exists(os.path.join(strProjectPath,"Audio\\Imported",strStation)):
										print(" creating station folder in audio folder")
										os.makedirs(os.path.join(strProjectPath,"Audio\\Imported",strStation))
									shutil.copyfile(strWavSrcPath, strWavDestPath)
								else:
									print(" WARNING - file not found")
									print(strWavSrcPath)
									sys.exit()

							else:	
								#generating spots for new template
								#update the position of the spot
								if blnEndSnap:
									#snapped to end of spot
									fltNewItemPosition = float(dictMarkers[strItemName.lower()][0]) - conTemplateDefaultSpotLength
								else:
									#snapped to beginning of spot
									fltNewItemPosition = float(dictMarkers[strItemName.lower()][0])
								
								#we're not going to do this any more because we want to keep the original template ITEM
								# positions in place.
								#lstItem[1] = " "*(intItemIndent+2) + "POSITION " + str(fltNewItemPosition) + "\n"

								#we're not going to do this any more because we want to keep the original template ITEM
								# length in place.
								#lstItem[3] = " "*(intItemIndent+2) + "LENGTH " + str(conTemplateDefaultSpotLength) + "\n"
								
								#turn on looping so that any length can be used for the silent wav
								lstItem[4] = " "*(intItemIndent+2) + "LOOP 1\n"

								#we're not going to do this any more because we want to keep the original template ITEM
								# filename in place.
								#lstItem[20] = " "*(intItemIndent+4) + "FILE \"Audio\\Template\\" + conSilentWAVFilename + "\"\n"

	#							#this is here because the template uses a different style assets source folder layout than the stations
								strWavSrcPath = os.path.join(strAssetsPath, "Audio\\General", conSilentWAVFilename)
								strWavSrcFolder = str(pathlib.Path(strWavSrcPath).parent)
								strWavDestPath = os.path.join(strProjectPath,"Audio\\Template",os.path.basename(strWavSrcPath))
								strWavDestFolder = str(pathlib.Path(strWavDestPath).parent)

							#commit all the changes made above
							for strEntry in lstItem:
								fOutFile.write(strEntry)
			else:
				print("I'm not sure how I got here - figure it out!")
				sys.exit()
				
#	print(" %s project file saved" % strStation)

	if strStation != conProjectTemplate:
		try:
			os.remove(os.path.join(strRenderOutputPath, "show-" + strShowNumber + "-" + strStation + strRenderExt))
		except OSError:
			pass

	#render the projects
	#due to a bug in reaper, I need to check to see if the rendered file is created.  If not, I need
	#to call the rendere again
	intStationRenderAttempt = 0
	if blnRenderOn:
		while True:
			if strStation != conProjectTemplate:
				#this is not the template, go ahead and render the show and update the mp3 tag
				intTotalRenderAttempts += 1
				intStationRenderAttempt += 1
				print(" rendering attempt %i for %s" % (intStationRenderAttempt, strStation))
				subprocess.run("\"" + conPathToReaper + "\" -renderproject \"" + strStationProjectFilePath + "\"")
		#		print("output:",subprocess.CompletedProcess)
			else:
				#this is the template - don't render
				break

			#check to see if the MP3 rendered correctly
			if os.path.exists(os.path.join(strRenderOutputPath, "show-" + strShowNumber + "-" + strStation + strRenderExt)):
				#file was rendered, tag it if it's an mp3
				if blnRenderMP3:
					#apply ID3 tag to newly created MP3
					print(" tagging MP3")
					subprocess.call("\"" + os.path.join(strScriptPath, "id3.exe") + "\" -12 -v -t \"Soul-Titanium Radio Show " + strShowNumber + " - " + strDJName.title() + "\" -a \"Mike Soultanian\" -g \"House\" \"" + os.path.join(strRenderOutputPath, "show-" + strShowNumber + "-" + strStation + strRenderExt) + "\"")

				print(" done!")
				intRenderSuccessCnt += 1
				break
			else:
				print(" This station's MP3 did not render correctly, trying again...")
#				winsound.Beep(1000, 1000)
				intRenderFailureCnt += 1
				if strStation not in lstFailedStationRender:
					lstFailedStationRender.append(strStation)

if intTotalRenderAttempts > len(lstStations)-1:
	print("Station(s) requiring re-render:")
	for strFailedStation in lstFailedStationRender:
		print(strFailedStation)
	print("%i render(s) failed out of a total of %i render attempt(s) for %i station(s)" % (intRenderFailureCnt, intTotalRenderAttempts, len(lstStations)-1))

winsound.Beep(1000, 50)
winsound.Beep(1000, 50)
print("Done")