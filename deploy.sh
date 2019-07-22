#!/bin/sh

[ -x "$(which gcloud)" ] || exit 1

# Timestamp
sed "s|LAST_UPDATE_DATE|`date`|" -i'.orig' index.html
# Deploy
gcloud app deploy --project crs-o-matic-hrd
# Restore
mv index.html.orig index.html
