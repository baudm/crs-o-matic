#!/bin/sh

[ $# -eq 1 ] || exit 1
APPCFG="$1"
[ -x "$APPCFG" ] || exit 1

# Timestamp
sed "s|LAST_UPDATE_DATE|`date`|" -i'.orig' index.html
# Deploy
$APPCFG update .
# Restore
mv index.html.orig index.html
