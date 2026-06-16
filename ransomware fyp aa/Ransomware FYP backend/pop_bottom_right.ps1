param (
    [string]$title,
    [string]$message
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = $title
$form.Size = New-Object System.Drawing.Size(300, 100)
$form.StartPosition = "Manual"
$form.FormBorderStyle = "FixedToolWindow"
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::DarkRed
$form.ForeColor = [System.Drawing.Color]::White

$label = New-Object System.Windows.Forms.Label
$label.Text = $message
$label.AutoSize = $true
$label.Location = New-Object System.Drawing.Point(10, 20)
$label.Font = New-Object System.Drawing.Font("Arial", 10, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($label)

# Position at bottom right
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$form.Location = New-Object System.Drawing.Point(($screen.Width - $form.Width - 10), ($screen.Height - $form.Height - 50))

# Timer to close after 5 seconds
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 5000
$timer.add_Tick({ $form.Close() })
$timer.Start()

$form.ShowDialog() | Out-Null
