#! /bin/bash
#                      -----
# RECUP INFOS XML : lot IOP
#                      -----

# chemin du fichier d'entrée = argument 1
chemin=$1

# préparation
header=`grep -Pazo "(?s)<header[ >].*?</header>" $chemin`

# RÉCUPS
nbodychars=`grep -Pazo "(?s)<body[ >].*?</body>" $chemin | wc -c`
title=`echo $header | grep -Pazo "(?s)<title[> ].*?</title>" | tr '\\\r\n\t' " "`
keywords=`grep -Pazo "<keyword[ >].*?</keyword>" $chemin | tr '\\\r\n\t' " "`
langue='__NA__'
abstract=`echo $header | grep -Pazo "(?s)<abstract[ >].*?</abstract>" | tr '\\\r\n\t' " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
