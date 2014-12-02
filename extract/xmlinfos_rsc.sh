#! /bin/bash
#                      -----
# RECUP INFOS XML : lot RSC
#                      -----

# chemin du fichier d'entrée = argument 1
chemin=$1

# récup
nbodychars=`strings "$chemin" | grep -Pzo "(?s)<art-body[ >].*?</art-body>" | wc -c`
title=`strings "$chemin" | grep -Pzo "(?s)<titlegrp[ >].*?</titlegrp>" | tr "\r\n\t" " " | grep -Pzo "<title[ >].*?</title>"`
keywords='__NA__'
langue='__NA__'
abstract=`strings "$chemin" | grep -Pzo "(?s)<art-front[ >].*?</art-front>" | grep -Pzo "(?s)<abstract[ >].*?</abstract>" | tr "\r\n\t" " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
