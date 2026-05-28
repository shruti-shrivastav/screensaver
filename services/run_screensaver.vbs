Set WshShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strBatPath = strScriptDir & "\run_screensaver.bat"

' Run the batch file in a hidden window (style 0) and do not wait for exit (False)
WshShell.Run """" & strBatPath & """", 0, False
