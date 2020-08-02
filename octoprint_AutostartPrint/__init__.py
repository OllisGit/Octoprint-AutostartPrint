# coding=utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import octoprint.plugin
import octoprint.printer
from octoprint.events import eventManager, Events
import octoprint.filemanager
from octoprint.filemanager.destinations import FileDestinations
import flask


import time
from threading import Thread

## GLOBAL KEYS
from octoprint.util import comm

SETTINGS_KEY_ACTIVATED = "activated"
SETTINGS_KEY_DEACTIVATE_AFTER_SUCCESSFUL = "deactivateAfterSuccessful"
SETTINGS_KEY_START_PRINT_DELAY = "startPrintDelay"
SETTINGS_KEY_FILE_SELECTION_MODE = "fileSelectionMode"
SETTINGS_KEY_START_TRIGGER_MODE = "startTriggerMode"
SETTINGS_KEY_INCLUDE_SUB_FOLDERS = "includeSubFolders"


FILE_SELECTION_MODE_SDCARD = FileDestinations.SDCARD
FILE_SELECTION_MODE_FILESYSTEM = FileDestinations.LOCAL

START_TRIGGER_MODE_CONNECTION = "connection"
START_TRIGGER_MODE_OPERATIONAL = "operational"

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
													  activated=self._settings.get_boolean([SETTINGS_KEY_ACTIVATED]),
													  selectedFilename = self.selectedFilename,
													  maxCountdownSeconds = maxCountdownSeconds,
													  currentCountdownSeconds = currentCountdownSeconds))

	def _sendCurrentActivationStateToClient(self):
		self._plugin_manager.send_plugin_message(self._identifier,
												 dict(action="currentActivationState",
													  activated = self._settings.get_boolean([SETTINGS_KEY_ACTIVATED])
													  )
												 )



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
										   "File '" +self.selectedFilename+ "' selected and started")



	def _startAutoStart(self):
		## start printing
		self._logger.info("!!!CONNECTED-Event started")
		# get latest file
		# check if gcode file
		# start countdown
		# -- select
		# -- print
		selectedFilePath = None
		selectedFileName = None
		selectedFilePathDict = None
		latestFiles = self._file_manager.list_files(recursive=True)
		selectedStorageDestination = self._settings.get([SETTINGS_KEY_FILE_SELECTION_MODE])
		for currentDestination in latestFiles:
			if selectedStorageDestination == currentDestination:
				allFiles = latestFiles[currentDestination].items()

				selectedFilePathDict = self._findLatestUploadedFile(allFiles, None)

		if selectedFilePathDict != None:
			# okay start countdown
			selectedFilePath = selectedFilePathDict["filePath"]
			selectedFileName = selectedFilePathDict["fileName"]

			if selectedStorageDestination == FileDestinations.SDCARD:
				path = selectedFilePath
				sd = True
			else:
				path = self._file_manager.path_on_disk(selectedStorageDestination, selectedFilePath)
				sd = False

			# start_new_thread(self.autostartThreadFunction(path, sd,))
			t = Thread(target=self._autostartPrintThreadFunction, args=(selectedFileName, path, sd,))
			t.start()
		else:
			# no file matching file found
			self._sendPopupMessageToClient("error", "AutostartPrint: No file selected!",
										   "Could not found a file on '" + selectedStorageDestination + "'")
		self._logger.info("!!!CONNECTED-Event DONE")

	def _findLatestUploadedFile(self, allFiles, latestResult):
		result = None
		for currentFile in allFiles:
			# check if file is a "machinecode file" and not a folder or image
			currentFilePath = currentFile[1]["path"]

			if not octoprint.filemanager.valid_file_type(currentFilePath, type="machinecode"):
				includeSubFolders = self._settings.get_boolean([SETTINGS_KEY_INCLUDE_SUB_FOLDERS])
				if (currentFile[1]["type"] == "folder" and includeSubFolders == True):
					if ("children" in currentFile[1]):
						allSubFiles = currentFile[1]["children"].items()
						latestResult = self._findLatestUploadedFile(allSubFiles, latestResult)
						# skip folder, next file
						continue
				else:
					if not octoprint.filemanager.valid_file_type(currentFilePath, type="machinecode"):
						continue

			# gcode present
			latestUploadTime = 0
			if (latestResult != None):
				latestUploadTime = latestResult["uploadTime"]

			uploadTime = currentFile[1]["date"]

			if uploadTime > latestUploadTime:

				selectedFilePath = currentFilePath
				selectedFileName = currentFile[0]

				latestResult = dict(
					filePath = selectedFilePath,
					fileName = selectedFileName,
					uploadTime = uploadTime
				)

		return latestResult



	######################################################################################### Hooks and public functions

#	def on_startup(self, host, port):
#		self._logger.info("ONSTART!")

#	def on_after_startup(self):
#		self._logger.info("AFTERSTART")

	def on_event(self, event, payload):

		# if (Events.CONNECTED == event and self._settings.get_boolean([SETTINGS_KEY_ACTIVATED])):
		if (self._settings.get_boolean([SETTINGS_KEY_ACTIVATED])):

			startPrinting = False
			if (START_TRIGGER_MODE_CONNECTION == self._settings.get([SETTINGS_KEY_START_TRIGGER_MODE])):
				startPrinting = Events.CONNECTED == event

			if (START_TRIGGER_MODE_OPERATIONAL == self._settings.get([SETTINGS_KEY_START_TRIGGER_MODE])):
				if (Events.PRINTER_STATE_CHANGED == event):
					operationalStateString = "Operational"  # self._printer.get_state_string(comm.STATE_OPERATIONAL)
					currentStateString = payload["state_string"]
					startPrinting = operationalStateString == currentStateString
					if (self._printer.is_printing()):
						# Already printing
						startPrinting=False

			if (startPrinting):
				self._startAutoStart()

		if (Events.PRINT_DONE == event and self._settings.get_boolean([SETTINGS_KEY_DEACTIVATE_AFTER_SUCCESSFUL])):
			self._settings.set_boolean([SETTINGS_KEY_ACTIVATED], False)
			self._settings.save()
			# could also work eventManager().fire(Events.SETTINGS_UPDATED)
			self._sendCurrentActivationStateToClient()


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

			if "activateAutostartPrint" == action:
				isActivated = request.values["activated"] == "true"	# string compare because bool("false") doesn't work. bool("False") works
				self._settings.set_boolean([SETTINGS_KEY_ACTIVATED], isActivated)
				self._settings.save()
				return flask.jsonify(activated=isActivated)

	##~~ SettingsPlugin mixin
	def get_settings_defaults(self):
		return dict(
			# put your plugin's default settings here
			activated = False,
			deactivateAfterSuccessful = True,
			startPrintDelay = 120,
			fileSelectionMode = FILE_SELECTION_MODE_SDCARD,
			startTriggerMode = START_TRIGGER_MODE_CONNECTION,
			includeSubFolders = False
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
				"js/ResetSettingsUtilV2.js"],
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
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = AutostartPrintPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
