#! /bin/bash
#                      -------------------
# RECUP INFOS XML : lot IOP - version NLM
#                      -------------------

# chemin du fichier d'entrée = argument 1
chemin=$1

# préparation
front=`strings "$chemin" | grep -Pzo "(?s)<front[ >].*?</front>"`

# récupérer infos
nbodychars=`strings "$chemin" | grep -Pzo "(?s)<body[ >].*?</body>" | wc -c`
title=`echo $front | grep -Pzo "(?s)<article-title[> ].*</article-title>" | tr "\r\n\t" " "`
keywords=`echo $front | grep -Pzo "(?s)<kwd-group[ >].*?</kwd-group>" | grep -Pzo "(?s)<kwd[ >].*?</kwd>" | tr "\r\n\t" " "`
langue='__NA__'
abstract=`echo $front | grep -Pzo "(?s)<abstract[ >].*?</abstract>" | tr "\r\n\t" " "`

# OUTPUT
echo -e "$chemin\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"
