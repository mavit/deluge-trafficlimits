Deluge Traffic Limits
=====================

_TrafficLimits_ is a plugin for the [Deluge bittorrent client](http://deluge-torrent.org/).  It will pause all torrents if more than a set amount of data is uploaded or downloaded.

TrafficLimits can be found at
[http://github.com/mavit/deluge-trafficlimits](http://github.com/mavit/deluge-trafficlimits).

Downloads can be found at
[http://www.triv.org.uk/~mavit/deluge-trafficlimits/](http://www.triv.org.uk/~mavit/deluge-trafficlimits/).

Questions may be asked on the
[Deluge forum](http://forum.deluge-torrent.org/viewtopic.php?f=9&t=34343).

## Configuration:

As well as setting the limits through the preferences (GTK UI only, for now), you can also create a file called `~/.config/deluge/trafficlimits` containing a label, the upload limit, the download limit, and the combined limit (in bytes), each on a line by themselves.  For example:

    January
    -1
    21474836480
    -1

This is intended to be used by a cron job for automatic scheduling, e.g.,

    * 00-15,21-23 * * * /bin/echo -e "Unlimited\n-1\n-1\n-1"             > ${XDG_CONFIG_HOME:-~/.config}/deluge/trafficlimits.tmp && mv ${XDG_CONFIG_HOME:-~/.config}/deluge/trafficlimits.tmp ${XDG_CONFIG_HOME:-~/.config}/deluge/trafficlimits
    * 16-20       * * * /bin/echo -e "Evening\n400000000\n750000000\n-1" > ${XDG_CONFIG_HOME:-~/.config}/deluge/trafficlimits.tmp && mv ${XDG_CONFIG_HOME:-~/.config}/deluge/trafficlimits.tmp ${XDG_CONFIG_HOME:-~/.config}/deluge/trafficlimits


## See also:

Please see also the [_Toggle_ plugin](http://dev.deluge-torrent.org/wiki/Plugins/Toggle).  You will need this to resume transfers once they have been paused, unless you use the automatic scheduling..
