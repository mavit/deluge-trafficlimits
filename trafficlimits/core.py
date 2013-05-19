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
import time

init_time = time.time()
DEFAULT_PREFS = {
    "maximum_upload": -1,
    "maximum_download": -1,
    "maximum_total": -1,
    "previous_upload": 0,
    "previous_download": 0,
    "previous_total": 0,
    "reset_time_upload": init_time,
    "reset_time_download": init_time,
    "reset_time_total": init_time,
    "label": ""
}

class Core(CorePluginBase):
    def enable(self):
        log.debug("TrafficLimits: Enabling...")
        self.config = deluge.configmanager.ConfigManager("trafficlimits.conf",
                                                         DEFAULT_PREFS)
        self.paused = False	# Paused by us, not some other plugin.
        self.label = self.config["label"]
        self.limits_mtime = 0
        self.set_initial()
        self.load_limits()

        self.update_timer = LoopingCall(self.update_traffic)
        self.update_timer.start(10)
        log.debug("TrafficLimits: Enabled.")


    def disable(self):
        log.debug("TrafficLimits: Disabling...")
        self.update_timer.stop()

        self.config["previous_upload"] \
            += self.session_upload - self.initial_upload
        self.config["previous_download"] \
            += self.session_download - self.initial_download
        self.config["previous_total"] \
            += self.session_total - self.initial_total
        self.config.save()
        if self.paused:
            component.get("Core").session.resume()
        log.debug("TrafficLimits: Disabled.")


    def update_traffic(self):
        log.debug("TrafficLimits: Updating...")

        try:
            if os.stat(deluge.configmanager.get_config_dir("trafficlimits")) \
                    .st_mtime != self.limits_mtime:
                self.load_limits();
        except OSError as error:
            log.debug("TrafficLimits: "
                      + deluge.configmanager.get_config_dir("trafficlimits")
                      + ": " + str(error))

        status = component.get("Core").get_session_status(["total_upload",
                                                           "total_download"])
        self.session_upload = status["total_upload"]
        self.session_download = status["total_download"]
        self.session_total = status["total_upload"] + status["total_download"]

        self.upload = ( self.config["previous_upload"]
                        + self.session_upload - self.initial_upload )
        self.download = ( self.config["previous_download"]
                          + self.session_download - self.initial_download )
        self.total = ( self.config["previous_total"]
                       + self.session_total - self.initial_total )

        if ( self.config["maximum_upload"] >= 0
             and self.upload > self.config["maximum_upload"] ):
            log.info("TrafficLimits: Session paused due to excessive upload.")
            self.paused = True
            component.get("Core").session.pause()
            self.initial_upload = self.session_upload
            self.config["previous_upload"] = 0
            self.config["reset_time_upload"] = time.time()

        if ( self.config["maximum_download"] >= 0
             and self.download > self.config["maximum_download"] ):
            log.info("TrafficLimits: Session paused due to excessive download.")
            self.paused = True
            component.get("Core").session.pause()
            self.initial_download = self.session_download
            self.config["previous_download"] = 0
            self.config["reset_time_download"] = time.time()

        if ( self.config["maximum_total"] >= 0
             and self.total > self.config["maximum_total"] ):
            log.info("TrafficLimits: Session paused due to excessive throughput.")
            self.paused = True
            component.get("Core").session.pause()
            self.initial_total = self.session_total
            self.config["previous_total"] = 0
            self.config["reset_time_total"] = time.time()

        component.get("EventManager").emit(
            TrafficLimitUpdate(
                self.label, self.upload, self.download, self.total,
                self.config["maximum_upload"],
                self.config["maximum_download"],
                self.config["maximum_total"],
                self.config["reset_time_upload"],
                self.config["reset_time_download"],
                self.config["reset_time_total"]
            )
        )

        log.debug("TrafficLimits: Updated.")


    def load_limits(self):
        log.debug("TrafficLimits: Loading limits...")

        try:
            limits = open(deluge.configmanager.get_config_dir("trafficlimits"))
            limits_mtime = os.fstat(limits.fileno()).st_mtime
            label = limits.readline().rstrip(os.linesep)
            maximum_upload = int(limits.readline().rstrip(os.linesep))
            maximum_download = int(limits.readline().rstrip(os.linesep))

            line = limits.readline().rstrip(os.linesep)
            maximum_total = -1 if line == '' else int(line)

        except (IOError, OSError, ValueError) as error:
            log.error("TrafficLimits: "
                      + deluge.configmanager.get_config_dir("trafficlimits")
                      + ": " + str(error))
            return

        self.limits_mtime = limits_mtime
        self.label = label
        self.config["maximum_upload"] = maximum_upload
        self.config["maximum_download"] = maximum_download
        self.config["maximum_total"] = maximum_total

        if self.label != self.config["label"]:
            self.config["label"] = self.label
            self.reset_initial()
            if self.paused:
                self.paused = False
                component.get("Core").session.resume()

        log.debug("TrafficLimits: Loaded limits.")

    @export
    def reset_initial(self):
        self.config["previous_upload"] = 0
        self.config["previous_download"] = 0
        self.config["previous_total"] = 0
        self.config["reset_time_upload"] = time.time()
        self.config["reset_time_download"] = self.config["reset_time_upload"]
        self.config["reset_time_total"] = self.config["reset_time_upload"]
        self.set_initial()


    def set_initial(self):
        status = component.get("Core").get_session_status(
            ["total_download", "total_upload"]
        )
        self.initial_upload = status["total_upload"]
        self.initial_download = status["total_download"]
        self.initial_total = status["total_upload"] + status["total_download"]


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
        state = [
            self.label, self.upload, self.download, self.total,
            self.config["maximum_upload"],
            self.config["maximum_download"],
            self.config["maximum_total"],
            self.config["reset_time_upload"],
            self.config["reset_time_download"],
            self.config["reset_time_total"]
        ]
        return state


class TrafficLimitUpdate (DelugeEvent):
    """
    Emitted when the ammount of transferred data changes.
    """
    def __init__(self, label, upload, download, total, maximum_upload,
                 maximum_download, maximum_total, reset_time_upload,
                 reset_time_download, reset_time_total):
        """
        :param label: str, a description of the current period
        :param upload: int, bytes uploaded during the current period
        :param download: int, bytes downloaded during the current period
        :param total: int, bytes up/downloaded during the current period
        :param maximum_upload: int, upper bound for bytes transmitted
        :param maximum_download: int, upper bound for bytes received
        :param maximum_total: int, upper bound for bytes transferred
        :param reset_time_upload: float, secs since epoch that upload was reset
        :param reset_time_download: float, secs since epoch download was reset
        :param reset_time_total: float, secs since epoch total was reset
        """
        self._args = [label, upload, download, total, maximum_upload,
                      maximum_download, maximum_total, reset_time_upload,
                      reset_time_download, reset_time_total]
