#! /bin/bash
# ----------------------------------------------------------------------
# Récupération d'infos sur un fichier XML Nature 
# => sortie tabulée 4 colonnes
#  1-col0 - chemin donné en entrée
#  2-col1 - nombre de caractères dans le body <bdy>
#  3-col2 - nombre de balises refbibs <bib* dans la liste <bibl
#  4-col3 - nombre total balises (elts, s-elts...) de la liste <bibl
#
#  Usage
#  -----
#  find -name "*.xml" -exec bash xmlinfos.sh \{} \; >> resultats.tab
#-----------------------------------------------------------------------


# ici configurer manuellement les 3 noms de balises attendues
# (par ex pour Nature : valeurs resp. "bdy" "bibl" et "bib")
bodyElt="bdy"
bibListElt="bibl"
bibEntryElt="bib"

# entrée
fichier=$1
# infos
nbodychars=`grep -Pazo "(?s)<${bodyElt}[ >].*</${bodyElt}>" $fichier | wc -c`
match=`grep -Pazo "(?s)<${bibListElt}[ >].*</${bibListElt}>" $fichier`
nbibs=`echo $match | grep -o "<${bibEntryElt}" | wc -l`
nelts=`echo $match | grep -o "<" | wc -l`
# sortie
echo -e "$1\t$nbodychars\t$nbibs\t$nelts"
