function Install-Chrome
{
    $LocalTempDir = $env:TEMP;
    $ChromeInstaller = "chrome_installer.exe";
    $url='http://dl.google.com/chrome/install/latest/chrome_installer.exe';
    $output="$LocalTempDir\$ChromeInstaller"

    try {
        (new-object System.Net.WebClient).DownloadFile($url, $output);
        $p = Start-Process $output -ArgumentList "/silent","/install" -PassThru -Verb runas;

        while (!$p.HasExited) { Start-Sleep -Seconds 1 }

        Write-Output ([PSCustomObject]@{Success=$p.ExitCode -eq 0;Process=$p})
    } catch {
        Write-Output ([PSCustomObject]@{Success=$false;Process=$p;ErrorMessage=$_.Exception.Message;ErrorRecord=$_})
    } finally {
        Remove-Item "$LocalTempDir\$ChromeInstaller" -ErrorAction SilentlyContinue -Verbose
    }

}

Install-Chrome
