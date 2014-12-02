#! /bin/bash
#                      ----------
# RECUP INFOS XML : lot ELSEVIER
#                      ----------

# chemin du fichier d'entrée = argument 1
chemin=$1

# ICI RÉCUP
nbodychars=`strings "$chemin" | grep -Pzo "(?s)<body[ >].*?</body>" | wc -c`
title=`strings "$chemin" | grep -Pzo "(?s)<ce:title[ >].*?</ce:title>" | tr "\r\n\t" " "`
keywords=`strings "$chemin" | grep -Pzo "<ce:keyword[ >].*?</ce:keyword>" | tr "\r\n\t" " "`
langue=`strings "$chemin" | grep -Po "<(?:converted-|simple-)?article[^>]+>" | grep -Po '(?<=xml:lang=")[^"]+(?=")' | tr "\r\n\t" " "`
abstract=`strings "$chemin" | grep -Pzo "(?s)<ce:abstract[ >].*?</ce:abstract>" | tr "\r\n\t" " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
