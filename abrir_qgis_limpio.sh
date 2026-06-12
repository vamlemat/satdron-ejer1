#!/usr/bin/env bash

unset PYTHONPATH
unset PYTHONHOME
unset VIRTUAL_ENV

export PATH="/usr/local/sbin:/usr/sbin:/sbin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games"
export PYTHONNOUSERSITE=1
export PYTHONPATH="/usr/lib/python3/dist-packages:/usr/share/qgis/python:/usr/share/qgis/python/plugins"

exec /usr/bin/qgis "$@"
