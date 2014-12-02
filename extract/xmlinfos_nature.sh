#! /bin/bash
#                      --------
# RECUP INFOS XML : lot NATURE
#                      --------

# chemin du fichier d'entrée = argument 1
chemin=$1

# RECUP
nbodychars=`strings "$chemin" | grep -Pzo "(?s)<bdy[ >].*?</bdy>" | wc -c`
title=`strings "$chemin" | grep -Pzo "(?s)<fm[ >].*?</fm>" | grep -Pzo "(?s)<atl[ >].*?</atl>" | tr "\r\n\t" " "`
keywords='__NA__'
langue=`strings "$chemin" | grep -Po "<article[^>]+>" | grep -Po '(?<=language=")[^"]+(?=")' | tr "\r\n\t" " "`
abstract=`strings "$chemin" | grep -Pzo "(?s)<(abs|fp).*?</(abs|fp)>" | tr "\r\n\t" " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
