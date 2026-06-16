Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\Administrator\Desktop\ransomware fyp aa\Ransomware FYP backend\"

' Start API Server silently using venv python
WshShell.Run """c:\Users\Administrator\Desktop\ransomware fyp aa\Ransomware FYP backend\venv\Scripts\python.exe"" api.py", 0, False

' Start File Monitor silently using venv python
WshShell.Run """c:\Users\Administrator\Desktop\ransomware fyp aa\Ransomware FYP backend\venv\Scripts\python.exe"" monitor.py", 0, False
