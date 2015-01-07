#! /bin/bash
#                      -------------------
# RECUP INFOS XML : lot IOP - version NLM
#                      -------------------

# chemin du fichier d'entrée = argument 1
chemin=$1

# préparation
front=`grep -Pazo "(?s)<front[ >].*?</front>" $chemin`

# récupérer infos
nbodychars=`grep -Pazo "(?s)<body[ >].*?</body>" $chemin | wc -c`
title=`echo $front | grep -Pazo "(?s)<article-title[> ].*</article-title>" | tr '\\\r\n\t' " "`
keywords=`echo $front | grep -Pazo "(?s)<kwd-group[ >].*?</kwd-group>" | grep -Pazo "(?s)<kwd[ >].*?</kwd>" | tr '\\\r\n\t' " "`
langue='__NA__'
abstract=`echo $front | grep -Pazo "(?s)<abstract[ >].*?</abstract>" | tr '\\\r\n\t' " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
