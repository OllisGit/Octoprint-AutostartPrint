# OctoPrint-AutostartPrint

[![Version](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=version&url=https://api.github.com/repos/OllisGit/OctoPrint-AutostartPrint/releases&query=$[0].name)]()
[![Released](https://img.shields.io/badge/dynamic/json.svg?color=brightgreen&label=released&url=https://api.github.com/repos/OllisGit/OctoPrint-AutostartPrint/releases&query=$[0].published_at)]()
![GitHub Releases (by Release)](https://img.shields.io/github/downloads/OllisGit/OctoPrint-AutostartPrint/latest/total.svg)

Plugin starts a print job after the Printer is connected (e.g. after powering up). It selects the lasted uploaded file for print.

If you want to start a printjob after powering up your OctoPrintServer, make sure you do the folowing steps:

1. Make sure you check "Auto-connect on server startup" in NavigationBar
2. Select what kind of file do you want to print from "local-" or "sd-card-filesystem" in the Plugin-Settings
3. Define a delay in seconds
3. Activate the Plugin 

--> Next time the printer is connected a countdown is started and after that countdown the print starts automatically. 

## Screenshots
![plugin-settings](screenshots/plugin-settings.png "Plugin-Settings")
![countdown-dialog](screenshots/countdown-dialog.png "Countdown-Dialog")


## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/OllisGit/OctoPrint-AutostartPrint/releases/latest/download/master.zip


## Versions

see [Release-Overview](https://github.com/OllisGit/OctoPrint-AutostartPrint/releases/)

## Roadmap
* Preselection of a file, instead of latest file from SD/Local-Filesystem
