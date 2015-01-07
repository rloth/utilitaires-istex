#! /bin/bash
#                      -----
# RECUP INFOS XML : lot RSC
#                      -----

# chemin du fichier d'entrée = argument 1
chemin=$1

# récup
nbodychars=`grep -Pazo "(?s)<art-body[ >].*?</art-body>" $chemin | wc -c`
title=`grep -Pazo "(?s)<titlegrp[ >].*?</titlegrp>" $chemin | tr '\\\r\n\t' " " | grep -Pazo "<title[ >].*?</title>"`
keywords='__NA__'
langue='__NA__'
abstract=`grep -Pazo "(?s)<art-front[ >].*?</art-front>" $chemin | grep -Pazo "(?s)<abstract[ >].*?</abstract>" | tr '\\\r\n\t' " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
