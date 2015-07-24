#! /bin/bash
#                      ----------
# RECUP INFOS XML : lot ELSEVIER
#                      ----------

# chemin du fichier d'entrée = argument 1
chemin=$1

# ICI RÉCUP
nbodychars=`grep -Pazo "(?s)<body[ >].*?</body>" $chemin | wc -c`
title=`grep -Pazo "(?s)<ce:title[ >].*?</ce:title>" $chemin | tr '\\\r\n\t' " "`

# arrive régulièrement
# pseudotitle=`grep -Pazo "(?s)<ce:dochead[ >].*?</ce:dochead>" $chemin | tr '\\\r\n\t' " "`

keywords=`grep -Pazo "<ce:keyword[ >].*?</ce:keyword>" $chemin | tr '\\\r\n\t' " "`
langue=`grep -Pao "<(?:converted-|simple-)?article[^>]+>" $chemin | grep -Pao '(?<=xml:lang=")[^"]+(?=")' | tr '\\\r\n\t' " "`
abstract=`grep -Pazo "(?s)<ce:abstract[ >].*?</ce:abstract>" $chemin | tr '\\\r\n\t' " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
