#! /bin/bash
#                      -----
# RECUP INFOS XML : lot OUP
#                      -----

# une fois : préalable pour les noms de fichiers contenant ' '
# IFSBAK=$IFS
# IFS=$(echo -en "\n\b")

# chemin du fichier d'entrée = argument 1
fichier=$1

# échappe ';(), ' dans le chemin (très important pour les paths OUP)
chemin=`echo $fichier | perl -pe 's/;/\;/g ; s/ /\ /g ; s/,/\,/g ; s/\(/\(/g ; s/\)/\)/g'`
# chemin=`echo $fichier | perl -pe 'chomp ; $_=quotemeta($_)'`
# echo "-->$chemin<--"

# préparation
front=`grep -Pazo "(?s)<front[ >].*?</front>" "$chemin"`

# ici récupération
nbodychars=`grep -Pazo "(?s)<body[ >].*?</body>" "$chemin" | wc -c`
title=`echo $front | grep -Pazo "<(?:article-)?title[ >].*?</(?:article-)?title>" | tr '\\\r\n\t' " "`
keywords=`echo $front | grep -Pazo "<kwd[ >].*?</kwd>" | tr '\\\r\n\t' " "`
langue='__NA__'
abstract=`echo $front | grep -Pazo "(?s)<abstract[ >].*?</abstract>" | tr '\\\r\n\t' " "`

# OUTPUT
echo -e "$fichier\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"

# une fois : remise en place du paramètre préalable
# IFS=$IFSBAK
