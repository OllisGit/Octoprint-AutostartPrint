/*
 * View model for OctoPrint-AutostartPrint
 *
 * Author: OllisGit
 * License: AGPLv3
 */
$(function() {

    var PLUGIN_ID = "AutostartPrint"; // from setup.py plugin_identifier

    var countdownDialog = null;
    var countdownCircle = null;
    var selectedFilename = null;


    function showDialog(dialogId, confirmFunction){

            if (countdownDialog != null && countdownDialog.is(":visible")){
                return;
            }

            $("#selectedFilenameForCountdown").text(selectedFilename)

            countdownDialog = $(dialogId);
            var cancelPrintButton = $("button.btn-confirm", countdownDialog);

            cancelPrintButton.unbind("click");
            cancelPrintButton.bind("click", function() {
                confirmFunction(countdownDialog);
            });

            countdownDialog.modal({
                //minHeight: function() { return Math.max($.fn.modal.defaults.maxHeight() - 80, 250); }
                keyboard: false,
                clickClose: false,
                showClose: false
            }).css({
                width: 'auto',
                'margin-left': function() { return -($(this).width() /2); }
            });
    }


    function updateCountdownCircle(maxCountdownSeconds, currentCountdownSeconds){
        var timeFactor = maxCountdownSeconds / 100;

        currentCountdown = currentCountdownSeconds;

        if (countdownCircle == null){
            // start countdowncircle
            countdownCircle = $('#countdownCircle');
            countdownCircle.circleProgress({
                size: 350,
                startAngle: -Math.PI / 4 * 2,
                //lineCap: 'round',
                value: 1.0
            });
            countdownCircle.on('circle-animation-progress', function(event, progress, stepValue) {
                $(this).find('strong').text(
                    "Print starts in '" + currentCountdown + "' seconds"
                );
            });
        } else {
            timeValue = currentCountdownSeconds / timeFactor / 100;
            countdownCircle.circleProgress('value', timeValue);
        }
    }

    // ViewModel - Constructor
    function AutostartPrintViewModel(parameters) {

        var self = this;

        // assign the injected parameters, e.g.:
        self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[1];

        self.pluginSettings = null;
        self.onBeforeBinding = function() {
            // assign current pluginSettings
            self.pluginSettings = self.settingsViewModel.settings.plugins[PLUGIN_ID];
        }

       // enable support of resetSettings
        new ResetSettingsUtil().assignResetSettingsFeature(PLUGIN_ID, function(data){
                                // assign default settings-values
                                self.pluginSettings.activated(data.activated);
                                self.pluginSettings.deactivateAfterSuccessful(data.deactivateAfterSuccessful);
                                self.pluginSettings.startPrintDelay(data.startPrintDelay);
                                self.pluginSettings.fileSelectionMode(data.fileSelectionMode);
        });

        self.countdownCircle = null;
        // receive data from server
        self.onDataUpdaterPluginMessage = function (plugin, data) {

            if (plugin != PLUGIN_ID) {
                return;
            }

            if (data.message_text){
                    new PNotify({
                        title: data.message_title,
                        text: data.message_text,
                        type: data.message_type,  // 'notice', 'info', 'success', or 'error'.
                        hide: false
                        });
            }

            if ("upateCountdown" == data.action){

                selectedFilename = data.selectedFilename;

                showDialog("#navbar_countdownDialog", function(dialog){
                    $.ajax({
                        url: API_BASEURL + "plugin/"+PLUGIN_ID+"?action=stopCountdown",
                        type: "GET"
                    }).done(function( data ){
                        new PNotify({
                            title: "Stopped autostart print!",
                            text: "The autostart print was canceled!",
                            type: "info",
                            hide: true
                        });
                        //shoud be done by the server to make sure the server is informed countdownDialog.modal('hide');
                        countdownDialog.modal('hide');
                        countdownCircle = null;
                    });
                });

                if (data.currentCountdownSeconds >= 0){
                    updateCountdownCircle(data.maxCountdownSeconds, data.currentCountdownSeconds);
                } else {
                    countdownDialog.modal('hide');
                    countdownCircle = null;
                }
                return;
            }

            if ("currentActivationState" == data.action){
                self.pluginSettings.activated(data.activated);
            }
        }
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: AutostartPrintViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [
                        "loginStateViewModel",
                        "settingsViewModel"
                      ],
        // Elements to bind to, e.g. #settings_plugin_AutostartPrint, #tab_plugin_AutostartPrint, ...
        elements: [
            document.getElementById("autostartPrint_plugin_navbar"),
            document.getElementById("autostartPrint_plugin_settings")
        ]
    });
});
