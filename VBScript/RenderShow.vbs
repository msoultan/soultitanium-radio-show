'****************************************************************************************
'****************************************************************************************
'**   Reaper Radio Show Rendering Utility (RenderShow.vbs)
'**
'**   Copyright (C) 2015 - Mike Soultanian - mike@soultanian.com
'**
'**   This program is free software; you can redistribute it and/or
'**   modify it under the terms of the GNU General Public License
'**   as published by the Free Software Foundation; either version 2
'**   of the License, or (at your option) any later version.
'**
'**   This program is distributed in the hope that it will be useful,
'**   but WITHOUT ANY WARRANTY; without even the implied warranty of
'**   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
'**   GNU General Public License for more details.
'**
'**   You should have received a copy of the GNU General Public License
'**   along with this program; if not, write to the Free Software
'**   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'**
'**   This header must appear on all derivatives of this code.
'****************************************************************************************
'****************************************************************************************

'v1.0 - Initial release
'v1.1 - Added menu to select file to render and what format to render
'v1.2 - Made the track names that need to be muted sent via command-line argument and
'		and added batch version check

'TODO: need to do a check that makes sure it finds all of the tracks specified in the
'		tracklisting before starting


'This script is used to render the Soul-Titanium radio show for multiple radio stations.
'The Reaper file is structured in such a way that there are station-specific tracks that
'contain station-specific audio like commercials and station IDs.  Usually you'd have to
'manually un-mute each of these tracks and then render that station's show, but this script
'automatically does that for you.


'these values need to be modified to match the Reaper audio configuration
Const PathToReaper = "c:\Program Files\REAPER (x64)\reaper.exe"
Const RenderPath = "C:\Users\Mike\Documents\REAPER Media\Soul-Titanium\"
Const BatchVersion = 2 'required version of the batch file

'-Do not change anything below here---------------------------------------------------------------------'
Const RenderMP3 = 1
Const RenderWAV = 2
Const RenderFilePrefix = "  RENDER_FILE "
Const RenderCfgMP3 = "    bDNwbQABAAABAAAA//////////8EAAAAAAEAAAAAAAA=", RenderCfgWAV = "    ZXZhdxAA"
Const DontWaitUntilFinished = false, ShowWindow = 1, DontShowWindow = 0, WaitUntilFinished = true
Const ForReading = 1, ForWriting = 2, ForAppending = 8 
Const UnMuted = "    MUTESOLO 0 0 0", Muted = "    MUTESOLO 1 0 0"

Set objFSO = CreateObject("Scripting.FileSystemObject")
set objShell = WScript.CreateObject("WScript.Shell")


'-------------------
'set a reference to the WshArguments collection (save on typing)
Set colNamedArguments = WScript.Arguments.Named
strBatchPath = LCase(colNamedArguments.Item("path")) & "\"

if strBatchPath <> "" Then
	Wscript.Echo "Path: " & strBatchPath
else
	Wscript.Echo "Path not provided from calling script.  Quitting."
	Wscript.Quit
end if

TrackNames = LCase(colNamedArguments.Item("tracks"))
if TrackNames <> "" Then
	Wscript.Echo "Tracks: " & TrackNames
else
	Wscript.Echo "Tracks not provided from calling script.  Quitting."
	Wscript.Quit
end if

intBatchVersion = LCase(colNamedArguments.Item("batchversion"))
if CInt(intBatchVersion) = BatchVersion Then
	Wscript.Echo "Batch Version: " & intBatchVersion
else
	Wscript.Echo "Batch file is not the correction version.  Quitting."
	Wscript.Quit
end if


'convert the list of track names to process to an array so it's easier to loop through
strTrackNames = LCase(TrackNames)
arrStationTracks = Split(strTrackNames, ",")

For Track = LBound(arrStationTracks) to UBound(arrStationTracks)
	arrStationTracks(Track) = Trim(arrStationTracks(Track))
Next



Set objFolder = objFSO.GetFolder(strBatchPath)
Set colFiles = objFolder.Files
Set lstFileList = CreateObject("System.Collections.ArrayList")  


 
For Each File In colFiles 
	lstFileList.Add File.Name
Next  
 
arrFileList = lstFileList.ToArray()
Set lstValidFiles = CreateObject("System.Collections.ArrayList")
For intStation = 0 to UBound(arrFileList)
	If InStr(UCase(arrFileList(intStation)), ".RPP") and NOT InStr(UCase(arrFileList(intStation)), ".RPP-BAK") Then
		strFileList = strFileList & intStation & ". " & arrFileList(intStation) & vbNewLine
		lstValidFiles.Add CInt(intStation)
	End If
Next

strFileList = "Show folder: " & strBatchPath & VbNewLine & vbNewLine & strFileList
blnValidSelection = FALSE
do
	strInput = Inputbox(strFileList,"Select which Reaper file you'd like to process")

	if strInput = "" Then
		'cancel, escape, or empty input
		wscript.quit
	End If
		
	If IsNumeric(strInput) Then
		strInput = CInt(LCase(Trim(strInput)))
		if IsNumeric(strInput) and lstValidFiles.Contains(strInput)then
			blnValidSelection = TRUE
		Else
			'the user entered junk so we'll just assume it's an invalid input
			'invalid selection				
			MsgBox _
			"Invalid selection." & vbNewLine & vbNewLine &_
			"Please make another selection.", vbSystemModal + vbInformation + vbOKOnly, "Invalid selection"
		end if
	else
		wscript.quit
	End If
loop while NOT blnValidSelection

ReaperFile = arrFileList(strInput)

'read show.RPP file into array
Set objFile = objFSO.OpenTextFile(ReaperFile, ForReading)
strTextFile = objFile.ReadAll
arrTextFile = Split(strTextFile, VbNewLine)
objFile.Close


blnValidSelection = FALSE
do
	strInput = Inputbox("Select which format you'd like to render to:" & VbNewLine & VbNewLine & RenderMP3 & ". MP3" & VbNewLine & RenderWAV & ". WAV", "Select render format" ,1)

	if strInput = "" Then
		'cancel, escape, or empty input
		wscript.quit
	End If

	if IsNumeric(strInput) Then
		'let's clean up the input
		strInput = CInt(Trim(strInput))
		If strInput = RenderMP3 Then
			strRenderExt = ".mp3"
			strRenderCfg = RenderCfgMP3
			blnValidSelection = TRUE
		ElseIf strInput = RenderWAV Then
			strRenderExt = ".wav"
			strRenderCfg = RenderCfgWAV
			blnValidSelection = TRUE
		Else
			'the user entered junk so we'll just assume it's an invalid input
			'invalid selection				
			MsgBox _
			"Invalid selection." & vbNewLine & vbNewLine &_
			"Please make another selection.", vbSystemModal + vbInformation + vbOKOnly, "Invalid selection"
		End If
	Else
		wscript.quit
	End If
loop while NOT blnValidSelection



'create an array with the same dimensions as the track names array to store the line locations of the MUTUSOLO parameter
IntSize =  UBound(arrStationTracks)
ReDim Preserve arrMuteSoloLoc(IntSize)

strScriptDir = objFSO.GetParentFolderName(wscript.ScriptFullName) & "\"

'pull the guest DJ name and show number from the path
strParentFolder = objFSO.GetParentFolderName(strBatchPath)
intBackSlashLoc = InStrRev(LCase(strParentFolder), "\")
strShowNameNum = Right(strParentFolder, Len(strParentFolder) - intBackSlashLoc)

'get show number
intShowNumLoc = InStr(strShowNameNum, "show ") + 5
intShowNumLen = InStr(intShowNumLoc, LCase(strShowNameNum), " ") - intShowNumLoc
strShowNumber = Trim(mid(strShowNameNum, intShowNumLoc, intShowNumLen))

'get guest dj name
intDashLoc = InStr(strShowNameNum, "-")
strDJName = ProperCase(Trim(Right(strShowNameNum, Len(strShowNameNum) - intDashLoc)))


'loop through all the tracks to be processed
intValidTrackCount = 0
For intStation = LBound(arrStationTracks) to UBound(arrStationTracks)
	'loop through the entire show.RPP file stored in memory and mute all the tracks to be processed
	blnLookingForMuteSolo = FALSE
	For intLineNum = LBound(arrTextFile) to UBound(arrTextFile)
		'track header found - see if it matches the current station track we're processing.  If not, move on
		If InStr(LCase(arrTextFile(intLineNum)), "<track {") and blnLookingForMuteSolo Then
			wscript.echo "MUTESOLO parameter missing because I'm at the next track marker without finding a MUTESOLO statement.  Quitting."
			wscript.quit
		End If

		If InStr(LCase(arrTextFile(intLineNum)), "<track {") Then
			If InStr(LCase(arrTextFile(intLineNum+1)), arrStationTracks(intStation)) Then
				'current block matches the current track that we're searching for so let's start looking for the MUTESOLO parameter
				blnLookingForMuteSolo = TRUE
				intValidTrackCount = intValidTrackCount + 1
			End If
		End If

		If InStr(LCase(arrTextFile(intLineNum)), "mutesolo") and blnLookingForMuteSolo Then
			'we've confirmed that we've found the MUTESOLO 
			arrTextFile(intLineNum) = Muted
			arrMuteSoloLoc(intStation)=intLineNum
			blnLookingForMuteSolo = FALSE
		End If
	Next
Next
objFile.Close

'check to see if the number of mute tracks to find matched the number of tracks specified in the batch file
If intValidTrackCount <> UBound(arrStationTracks)+1 Then
	MsgBox _
	"Not all tracks specified in batch file were found in the RPP file." & vbNewLine & vbNewLine &_
	"Please update the batch file to match the RPP file.", vbSystemModal + vbInformation + vbOKOnly, "Warning"
	wscript.quit
End If

'loop through all of the tracks and unmute each one and write out a temporary RPP file for rendering and render the show
For intStation = LBound(arrStationTracks) to UBound(arrStationTracks)
	Set objFile = objFSO.OpenTextFile("TEMP-" & UCase(arrStationTracks(intStation)) & "-" & ReaperFile, ForWriting, true)
	
	'loop through the text file in memory, update the render path and appropriate mute setting, and save to a temporary render file
	intRenderCfg = -1
	For intLineNum = LBound(arrTextFile) to UBound(arrTextFile)
		If InStr(LCase(arrTextFile(intLineNum)), "render_file") Then
			objFile.Write(RenderFilePrefix & """" & RenderPath & "show-" & strShowNumber & "-" & arrStationTracks(intStation) & strRenderExt & """" & VbNewLine)
		ElseIf InStr(LCase(arrTextFile(intLineNum)), "<render_cfg") Then
			'found the render_cfg tag, because the rest of the cfg is on the following line, store the next line number
			intRenderCfg = intLineNum + 1
			objFile.Write(arrTextFile(intLineNum) & VbNewLine)
		ElseIf intRenderCfg = intLineNum Then
			objFile.Write(strRenderCfg & VbNewLine)
		ElseIf intLineNum = arrMuteSoloLoc(intStation) Then
			objFile.Write(UnMuted & VbNewLine)
		Else
			objFile.Write(arrTextFile(intLineNum) & VbNewLine)
		End If
	Next
	objFile.Close
	
	'run reaper and render show
	Wscript.Echo "Rendering " & arrStationTracks(intStation) & "..."
	objShell.Run """" & PathToReaper & """ -renderproject """ & strBatchPath & "TEMP-" & UCase(arrStationTracks(intStation)) & "-" & ReaperFile & """", ShowWindow, WaitUntilFinished
	objFSO.DeleteFile strBatchPath & "TEMP-" & UCase(arrStationTracks(intStation)) & "-" & ReaperFile
	If InStr(strRenderExt, "mp3") Then
		'apply ID3 tag to newly created MP3
		objShell.Run """" & strScriptDir & "id3.exe"" -12 -t ""Soul-Titanium Radio Show " & strShowNumber & " - " & strDJName &_
			""" -a ""Mike Soultanian"" -g ""House"" """ & RenderPath & "show-" & strShowNumber & "-" & arrStationTracks(intStation) &_
			strRenderExt & """", DontShowWindow, WaitUntilFinished
	End If
	Wscript.Echo "Done."
Next



'=-=-=-=-=-=-=
'Functions
'=-=-=-=-=-=-=

Function ProperCase(sText)
'*** Converts text to proper case e.g.  ***'
'*** surname = Surname                  ***'
'*** o'connor = O'Connor                ***'
 
    Dim a, iLen, bSpace, tmpX, tmpFull
 
    iLen = Len(sText)
    For a = 1 To iLen
    If a <> 1 Then 'just to make sure 1st character is upper and the rest lower'
        If bSpace = True Then
            tmpX = UCase(mid(sText,a,1))
            bSpace = False
        Else
        tmpX=LCase(mid(sText,a,1))
            If tmpX = " " Or tmpX = "'" Then bSpace = True
        End if
    Else
        tmpX = UCase(mid(sText,a,1))
    End if
    tmpFull = tmpFull & tmpX
    Next
    ProperCase = tmpFull
End Function