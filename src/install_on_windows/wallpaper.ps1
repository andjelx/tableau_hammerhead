 function UpdateWallpaper {
    param ([string]$Motd, [string]$outFile)
    # Tested only with PowerShell 2+
    Add-Type -AssemblyName System.Drawing

    # Origin: https://konstantingreger.net/lego-ify-tableau/
    $filenameTemplate = "C:\TableauSetup\Tableau-Lego.jpg"
    $bmp = [System.Drawing.Image]::FromFile($filenameTemplate)
    $font = new-object System.Drawing.Font Consolas,48
    $brushFg = [System.Drawing.Brushes]::Black
    $graphics = [System.Drawing.Graphics]::FromImage($bmp)
    $graphics.DrawString($Motd,$font,$brushFg,$bmp.Width/5,10)
    $graphics.Dispose()

    $bmp.Save($outFile)
}

function FixWallpaper {
    #  Update wallpaper
    #  Substitute config for EC2 Launch v1 to prevent wallpaper change
    #  Set wallpaper with EC2 Launch v2
    $filenameOutput = "C:\ProgramData\Amazon\EC2Launch\wallpaper\Ec2Wallpaper.jpg"

    UpdateWallpaper "Tableau server version: $TAS_Version" "$filenameOutput"

    Copy-Item -Force -Path c:\TableauSetup\LaunchConfig.json -Destination C:\ProgramData\Amazon\EC2-Windows\Launch\Config\LaunchConfig.json
    & "C:\Program Files\Amazon\EC2Launch\EC2launch.exe" wallpaper --path="$filenameOutput" --attributes=hostName,instanceId,privateIpAddress,publicIpAddress,instanceSize,availabilityZone,memory,network
} 
