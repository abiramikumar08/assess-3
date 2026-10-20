Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile('C:\Temp\test_tts.wav')
$synth.Speak('Hello this is a test of Windows text to speech')
$synth.Dispose()
Write-Output "done"
