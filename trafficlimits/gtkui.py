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
import time

class GtkUI(GtkPluginBase):
    def enable(self):
        self.builder = gtk.Builder();
        self.builder.add_from_file(get_resource("config.ui"))
        self.builder.connect_signals({
                "on_button_clear_clicked": self.on_button_clear_clicked,
                });

        component.get("Preferences").add_page("TrafficLimits", self.builder.get_object("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

        self.status_item = component.get("StatusBar").add_item(
            image=get_resource("monitor.png"),
            text="",
            callback=self.on_status_item_clicked,
            tooltip="TrafficLimits plugin"
        )

        def on_get_state(state):
            self.set_status(*state)

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
            "label": self.builder.get_object("txt_label").get_text(),
            "maximum_upload":
                int(self.builder.get_object("spinbutton_upload").get_value()),
            "maximum_download":
                int(self.builder.get_object("spinbutton_download").get_value()),
            "maximum_total":
                int(self.builder.get_object("spinbutton_total").get_value()),
        }
        client.trafficlimits.set_config(config)

    def on_show_prefs(self):
        client.trafficlimits.get_config().addCallback(self.cb_get_config)
        client.trafficlimits.get_state().addCallback(self.cb_get_state)

    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.builder.get_object("txt_label").set_text(config["label"])
        self.builder.get_object("spinbutton_upload").set_value(
            config["maximum_upload"])
        self.builder.get_object("spinbutton_download").set_value(
            config["maximum_download"])
        self.builder.get_object("spinbutton_total").set_value(
            config["maximum_total"])

    def cb_get_state(self, state):
        "callback for on show_prefs"
        self.builder.get_object("label_uploaded").set_text(
            str(state[1]) + " bytes since "
            + time.strftime("%c", time.localtime(state[7])))
        self.builder.get_object("label_downloaded").set_text(
            str(state[2]) + " bytes since "
            + time.strftime("%c", time.localtime(state[8])))
        self.builder.get_object("label_transferred").set_text(
            str(state[3]) + " bytes since "
            + time.strftime("%c", time.localtime(state[9])))

    def on_status_item_clicked(self, widget, event):
        component.get("Preferences").show("TrafficLimits")

    def on_button_clear_clicked(self, widget):
        client.trafficlimits.reset_initial()
        self.builder.get_object("label_uploaded").set_text("0 bytes")
        self.builder.get_object("label_downloaded").set_text("0 bytes")
        self.builder.get_object("label_transferred").set_text("0 bytes")

    def set_status(self, label, upload, download, total,
                   maximum_upload, maximum_download, maximum_total,
                   reset_time_upload, reset_time_download, reset_time_total):
        status = ""
        pairs = [
             [download, maximum_download],
             [upload, maximum_upload],
             [total, maximum_total],
         ]
        used = "/".join(
            ["%s" % deluge.common.fsize(p[0]) for p in pairs if p[1] >= 0]
        )
        if used == "":
            status = label
        else:
            if label != "":
                status = label + ": "
            status += used + " (" + "/".join(
                ["%d%%" % (100 * p[0] / p[1]) for p in pairs if p[1] >= 0]
            ) + ")"

        self.status_item.set_text(status)

        tooltip = "/".join(
            ["%s" % p[0] for p in [
                ["download", maximum_download],
                ["upload", maximum_upload],
                ["total", maximum_total],
            ] if p[1] >= 0]
        ).capitalize()
        if tooltip == "":
            tooltip = "TrafficLimits plugin"
        else:
            tooltip += " during this period"
        self.status_item.set_tooltip(tooltip)
        
    def on_trafficlimit_update(self, label, upload, download, total,
                               maximum_upload, maximum_download, maximum_total,
                               reset_time_upload, reset_time_download,
                               reset_time_total):
        def on_state_deferred(s):
            self.set_status(label, upload, download, total,
                            maximum_upload, maximum_download, maximum_total,
                            reset_time_upload, reset_time_download,
                            reset_time_total)
            self.cb_get_state([label, upload, download, total,
                               maximum_upload, maximum_download, maximum_total,
                               reset_time_upload, reset_time_download,
                               reset_time_total])

        self.state_deferred.addCallback(on_state_deferred)
