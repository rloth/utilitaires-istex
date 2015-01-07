#! /bin/bash
#                      --------
# RECUP INFOS XML : lot NATURE
#                      --------

# chemin du fichier d'entrée = argument 1
chemin=$1

# RECUP
nbodychars=`grep -Pazo "(?s)<bdy[ >].*?</bdy>" $chemin | wc -c`
title=`grep -Pazo "(?s)<fm[ >].*?</fm>" $chemin | grep -Pazo "(?s)<atl[ >].*?</atl>" | tr '\\\r\n\t' " "`
keywords='__NA__'
langue=`grep -Po "<article[^>]+>" $chemin | grep -Po '(?<=language=")[^"]+(?=")' | tr '\\\r\n\t' " "`
abstract=`grep -Pazo "(?s)<(abs|fp).*?</(abs|fp)>" $chemin | tr '\\\r\n\t' " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"

