Set objArgs = WScript.Arguments
If objArgs.Count >= 2 Then
    strTitle = objArgs(0)
    strMsg = objArgs(1)
    MsgBox strMsg, vbCritical + vbOKOnly, strTitle
End If
