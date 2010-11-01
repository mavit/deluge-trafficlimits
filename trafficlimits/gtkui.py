#
# gtkui.py
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

import gtk

from deluge.log import LOG as log
from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common

from common import get_resource

class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))

        component.get("Preferences").add_page("TrafficLimits", self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

        self.status_item = component.get("StatusBar").add_item(
            image=get_resource("monitor.png"),
            text="",
            callback=self.on_status_item_clicked,
            tooltip="Download/upload during this period")

        def on_get_state(state):
            label = state[0]
            upload = int(state[1])
            download = int(state[2])
            maximum_upload = int(state[3])
            maximum_download = int(state[4])
            self.set_status(label, upload, download,
                            maximum_upload, maximum_download)

        self.state_deferred = client.trafficlimits.get_state().addCallback(on_get_state)
        client.register_event_handler("TrafficLimitUpdate", self.on_trafficlimit_update)

    def disable(self):
        component.get("StatusBar").remove_item(self.status_item)
        del self.status_item
        component.get("Preferences").remove_page("TrafficLimits")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def on_apply_prefs(self):
        log.debug("applying prefs for TrafficLimits")
        config = {
            "test":self.glade.get_widget("txt_test").get_text()
        }
        client.trafficlimits.set_config(config)

    def on_show_prefs(self):
        client.trafficlimits.get_config().addCallback(self.cb_get_config)

    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.glade.get_widget("txt_test").set_text(config["test"])

    def on_status_item_clicked(self, widget, event):
        component.get("Preferences").show("TrafficLimits")

    def set_status(self, label, upload, download,
                   maximum_upload, maximum_download):
        self.status_item.set_text(
            "%s: %s/%s (%d%%/%d%%)"
            % (label,
               deluge.common.fsize(download),
               deluge.common.fsize(upload),
               100 * download / maximum_download
                   if maximum_download >= 0 else 0,
               100 * upload / maximum_upload
                   if maximum_upload >= 0 else 0,
               ))

    def on_trafficlimit_update(self, label, upload, download,
                               maximum_upload, maximum_download):
        def on_state_deferred(s):
            self.set_status(label, upload, download,
                            maximum_upload, maximum_download)

        self.state_deferred.addCallback(on_state_deferred)
