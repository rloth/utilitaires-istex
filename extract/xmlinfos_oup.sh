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

# TODO vérifier au préalable article-type="other" ou article-type="research-article" ?

# préparation
front=`grep -Pazo "(?s)<front[ >].*?</front>" "$chemin"`

# ici récupération
nbodychars=`grep -Pazo "(?s)<body[ >].*?</body>" "$chemin" | wc -c`

# parfois nécessaire \\\r au lieu de \r
#     /!\ si plusieurs titres ils y seront tous
#     ex: /data/oup/Cardiovascular Research, 1967-2010 (v1-v88)/
#         cardiovascres87_suppl_1/cardiovascres87_suppl_1xml/cvq176.xml
title=`echo $front | grep -Pazo "<(?:article-)?title[ >].*?</(?:article-)?title>" | tr -s '\r\n\t' " "`
keywords=`echo $front | grep -Pazo "<kwd[ >].*?</kwd>" | tr -s '\r\n\t' " "`
langue='__NA__'

# /!\ si plusieurs abstracts ils y seront tous (cf. titre)
abstract=`echo $front | grep -Pazo "(?s)<abstract[ >].*?</abstract>" | tr -s '\r\n\t' " "`

# OUTPUT
echo -e "$fichier\t$nbodychars\t$langue\t$title\t$keywords\t$abstract"

# une fois : remise en place du paramètre préalable
# IFS=$IFSBAK
