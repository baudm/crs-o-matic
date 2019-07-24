#!/bin/sh

[ -x "$(which gcloud)" ] || exit 1

VER_ABBREV="$(git log -1 --format=%h)"
VER_FULL="$(git log -1 --format=%H)"
DATE="$(git log -1 --format=%cd)"

# Version info
sed "s|LAST_UPDATE_DATE|$DATE|; s|VER_ABBREV|$VER_ABBREV|; s|VER_FULL|$VER_FULL|" -i'.orig' templates/index.html
sed "s|VER_ABBREV|$VER_ABBREV|" -i'.orig' crs.py
# Deploy
gcloud app deploy --project crs-o-matic-hrd $*
# Restore
mv templates/index.html.orig templates/index.html
mv crs.py.orig crs.py
