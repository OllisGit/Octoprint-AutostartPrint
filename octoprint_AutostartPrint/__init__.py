# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.printer
from octoprint.events import Events
import octoprint.filemanager
from octoprint.filemanager.destinations import FileDestinations
import flask


import time
from threading import Thread

## GLOBAL KEYS

SETTINGS_KEY_ACTIVATED = "activated"
SETTINGS_KEY_START_PRINT_DELAY = "startPrintDelay"
SETTINGS_KEY_FILE_SELECTION_MODE = "fileSelectionMode"

FILE_SELECTION_MODE_SDCARD = FileDestinations.SDCARD
FILE_SELECTION_MODE_FILESYSTEM = FileDestinations.LOCAL

class AutostartPrintPlugin(octoprint.plugin.SettingsPlugin,
						   octoprint.plugin.AssetPlugin,
						   octoprint.plugin.TemplatePlugin,
						   octoprint.plugin.StartupPlugin,
						   octoprint.plugin.EventHandlerPlugin,
						   octoprint.plugin.SimpleApiPlugin):

	def initialize(self):
		self._selectedDestination = None
		self.countdownRunning = False
		self.selectedFilename = None

	################################################################################################## private functions

	def _to_storage_and_name(self, payload):
		return payload["target"], payload["path"]

	# type: 'notice', 'info', 'success', or 'error'
	def _sendPopupMessageToClient(self, type, title, popUpMessage):
		self._plugin_manager.send_plugin_message(self._identifier,
												 dict(message_type=type,
													  message_title=title,
													  message_text=popUpMessage))

	def _sendCountdownTimeToClient(self, maxCountdownSeconds, currentCountdownSeconds):
		self._plugin_manager.send_plugin_message(self._identifier,
												 dict(action="upateCountdown",
													  selectedFilename = self.selectedFilename,
													  maxCountdownSeconds = maxCountdownSeconds,
													  currentCountdownSeconds = currentCountdownSeconds))


	def _autostartPrintThreadFunction(self, fileName, filePath, isSDDestination):
		# lets try to start sofort
		self._logger.info("!!!_autostartPrintThreadFunction started")

		self.selectedFilename = fileName
		self.countdownRunning = True

		startPrint = True
		maxCountdownSeconds = self._settings.get_int([SETTINGS_KEY_START_PRINT_DELAY])
		currentCountdownSeconds = maxCountdownSeconds
		while True:
			if (self.countdownRunning == False):
				startPrint = False
				break
			if currentCountdownSeconds < -1:
				break
			self._sendCountdownTimeToClient(maxCountdownSeconds, currentCountdownSeconds)
			time.sleep(1)
			currentCountdownSeconds = currentCountdownSeconds -1

		# should I really start the print
		if startPrint:
			self._printer.select_file(filePath, isSDDestination, True)
			self._sendPopupMessageToClient("success", "AutostartPrint: Print started!",
										   "File " +self.selectedFilename+ " selected and started")

	######################################################################################### Hooks and public functions

#	def on_startup(self, host, port):
#		self._logger.info("ONSTART!")

#	def on_after_startup(self):
#		self._logger.info("AFTERSTART")

	def on_event(self, event, payload):

		if (Events.CONNECTED == event and self._settings.get_boolean([SETTINGS_KEY_ACTIVATED])):
			## start printing
			self._logger.info("!!!CONNECTED-Event started")

			# get latest file
			# check if gcode file
			# start countdown
			# -- select
			# -- print

			selectedFilePath = None
			selectedFileName = None
			lastUploadTime = 0
			latestFiles = self._file_manager.list_files()
			selectedStorageDestination = self._settings.get([SETTINGS_KEY_FILE_SELECTION_MODE])
			for currentDestination in latestFiles:
				if selectedStorageDestination == currentDestination:
					allFiles = latestFiles[currentDestination].items()
					for currentFile in allFiles:
						uploadTime = currentFile[1]["date"]
						# check if file is a "machinecode file"
						currentFilePath = currentFile[1]["path"]
						if not octoprint.filemanager.valid_file_type(currentFilePath, type="machinecode"):
							self._logger.debug("File '" + currentFilePath + "' is not a machinecode file, not autoprinting")
							continue

						if uploadTime > lastUploadTime:
							lastUploadTime = uploadTime
							selectedFilePath = currentFilePath
							selectedFileName = currentFile[0]

			if selectedFilePath != None:
				# okay start countdown

				if selectedStorageDestination == FileDestinations.SDCARD:
					path = selectedFilePath
					sd = True
				else:
					path = self._file_manager.path_on_disk(selectedStorageDestination, selectedFilePath)
					sd = False

				#start_new_thread(self.autostartThreadFunction(path, sd,))
				t = Thread(target=self._autostartPrintThreadFunction, args=(selectedFileName, path, sd,))
				t.start()
			else:
				# no file matching file found
				self._sendPopupMessageToClient("error","AutostartPrint: No file selected!", "Could not found a file on '"+selectedStorageDestination+"'")

			self._logger.info("!!!CONNECTED-Event DONE")


	def on_settings_save(self, data):
		# default save function
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

	# to allow the frontend to trigger an update
	def on_api_get(self, request):
		if len(request.values) != 0:
			action = request.values["action"]

			# deceide if you want the reset function in you settings dialog
			if "isResetSettingsEnabled" == action:
				return flask.jsonify(enabled="true")

			if "resetSettings" == action:
				self._settings.set([], self.get_settings_defaults())
				self._settings.save()
				return flask.jsonify(self.get_settings_defaults())

			if "stopCountdown" == action:
				self.countdownRunning = False
				return flask.jsonify(stopped=True)

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
			activated = False,
			startPrintDelay = 120,
			fileSelectionMode = FILE_SELECTION_MODE_SDCARD
		)

	##~~ TemplatePlugin mixin
	def get_template_configs(self):
		return [
			dict(type="settings", custom_bindings=True)
		]

	##~~ AssetPlugin mixin
	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/circle-progress.min.js",
				"js/AutostartPrint.js",
				"js/ResetSettingsUtil.js"],
			css=["css/AutostartPrint.css"],
			less=["less/AutostartPrint.less"]
		)

	##~~ Softwareupdate hook
	def get_update_information(self):
		# Define the configuration for your plugin to use with the Software Update
		# Plugin here. See https://github.com/foosel/OctoPrint/wiki/Plugin:-Software-Update
		# for details.
		return dict(
			AutostartPrint=dict(
				displayName="AutostartPrint Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="OllisGit",
				repo="OctoPrint-AutostartPrint",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/OllisGit/OctoPrint-AutostartPrint/releases/latest/download/master.zip"
			)
		)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "AutostartPrint Plugin"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = AutostartPrintPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
