#! /bin/bash
#                      -----
# RECUP INFOS XML : lot IOP
#                      -----

# chemin du fichier d'entrée = argument 1
chemin=$1

# préparation
header=`strings "$chemin" | grep -Pzo "(?s)<header[ >].*?</header>"`

# RÉCUPS
nbodychars=`strings "$chemin" | grep -Pzo "(?s)<body[ >].*?</body>" | wc -c`
title=`echo $header | grep -Pzo "(?s)<title[> ].*?</title>" | tr "\r\n\t" " "`
keywords=`strings "$chemin" | grep -Pzo "<keyword[ >].*?</keyword>" | tr "\r\n\t" " "`
langue='__NA__'
abstract=`echo $header | grep -Pzo "(?s)<abstract[ >].*?</abstract>" | tr "\r\n\t" " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
