#
# core.py
#
# Copyright (C) 2010 Peter Oliver <TrafficLimits@mavit.org.uk>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

from deluge.log import LOG as log
from deluge.plugins.pluginbase import CorePluginBase
import deluge.component as component
import deluge.configmanager
from deluge.core.rpcserver import export
import os
from deluge.event import DelugeEvent
from twisted.internet.task import LoopingCall

DEFAULT_PREFS = {
    "previous_upload": 0,
    "previous_download": 0,
    "label": ""
}

class Core(CorePluginBase):
    def enable(self):
        log.debug("TrafficLimits: Enabling...")
        self.config = deluge.configmanager.ConfigManager("trafficlimits.conf",
                                                         DEFAULT_PREFS)
        self.reset_initial()
        self.load_limits()

        self.update_timer = LoopingCall(self.update_traffic)
        self.update_timer.start(10)

    def disable(self):
        log.debug("TrafficLimits: Disabling...")
        self.update_timer.stop()

        self.config["previous_upload"] \
            += self.session_upload - self.initial_upload
        self.config["previous_download"] \
            += self.session_download - self.initial_download
        self.config.save()
        component.get("Core").session.resume()

    def update_traffic(self):
        log.debug("TrafficLimits: Updating...")
        if os.stat(deluge.configmanager.get_config_dir("trafficlimits")) \
                .st_mtime != self.limits_mtime:
            self.load_limits();

        status = component.get("Core").get_session_status(["total_upload",
                                                           "total_download"])
        self.session_upload = status["total_upload"]
        self.session_download = status["total_download"]

        log.debug("TrafficLimits: maximum_upload: %d" % self.maximum_upload)
        log.debug("TrafficLimits: maximum_download: %d" % self.maximum_download)
        log.debug("TrafficLimits: initial_upload: %d" % self.initial_upload)
        log.debug("TrafficLimits: initial_download: %d" % self.initial_download)
        log.debug("TrafficLimits: session_upload: %d" % self.session_upload)
        log.debug("TrafficLimits: session_download: %d" % self.session_download)
        log.debug("TrafficLimits: previous_upload: %d" % self.config["previous_upload"])
        log.debug("TrafficLimits: previous_download: %d" % self.config["previous_download"])

        self.upload = ( self.config["previous_upload"] + self.session_upload
                   - self.initial_upload )
        self.download = ( self.config["previous_upload"] + self.session_download
                     - self.initial_download )

        if self.maximum_upload >= 0 and self.upload > self.maximum_upload:
            log.info("TrafficLimits: Session paused due to excessive upload.")
            component.get("Core").session.pause()
            self.initial_upload = self.session_upload
            self.config["previous_upload"] = 0
        if self.maximum_download >= 0 and self.download > self.maximum_download:
            log.info("TrafficLimits: Session paused due to excessive download.")
            component.get("Core").session.pause()
            self.initial_download = self.session_download
            self.config["previous_download"] = 0

        component.get("EventManager").emit(TrafficLimitUpdate(
                self.label, self.upload, self.download,
                self.maximum_upload, self.maximum_download))

    def load_limits(self):
        log.debug("TrafficLimits: Loading limits...")

        limits = open('/home/azureus/.config/deluge/trafficlimits')
        self.limits_mtime = os.fstat(limits.fileno()).st_mtime
        self.label = limits.readline().rstrip(os.linesep)
        self.maximum_upload = int(limits.readline().rstrip(os.linesep))
        self.maximum_download = int(limits.readline().rstrip(os.linesep))

        log.debug("TrafficLimits: label:" + self.label)

        if self.label != self.config["label"]:
            self.config["label"] = self.label
            self.config["previous_upload"] = 0
            self.config["previous_download"] = 0
            self.reset_initial()
            component.get("Core").session.resume()

    def reset_initial(self):
        status = component.get("Core").get_session_status(["total_download", "total_upload"])
        self.initial_upload = status["total_upload"]
        self.initial_download = status["total_download"]

    @export
    def set_config(self, config):
        """Sets the config dictionary"""
        for key in config.keys():
            self.config[key] = config[key]
        self.config.save()

    @export
    def get_config(self):
        """Returns the config dictionary"""
        return self.config.config

    @export
    def get_state(self):
        state = [ self.label, self.upload, self.download,
                  self.maximum_upload, self.maximum_download ]
        return state

class TrafficLimitUpdate (DelugeEvent):
    """
    Emitted when the ammount of transferred data changes.
    """
    def __init__(self, label, upload, download,
                 maximum_upload, maximum_download):
        """
        :param FIXME label: str, a description of the current period
        :param upload: str, bytes uploaded during the current period
        :param download: str, bytes downloaded during the current period
        :param maximum_upload: str, upper bound for bytes transmitted
        :param maximum_download: str, upper bound for bytes received
        """
        self._args = [label, upload, download, maximum_upload, maximum_download]