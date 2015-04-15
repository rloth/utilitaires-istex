#! /bin/bash
#               ====== BIBOCR ======
#     --------------------------------------------
#       Usage:  bibocr.sh input.pdf > sortie.txt
#     --------------------------------------------
#      Convertit les 10 dernières pages d'un PDF
#         via l'OCR tesseract (en mode anglais)

# ----------------------------------------------------
# Dépendances:
#  - pdfinfo   (deb package: poppler-utils)
#  - convert   (deb package: imagemagick)
#  - tesseract (deb package: tesseract-ocr)
# ----------------------------------------------------
# (c) 2015 INIST-CNRS (ISTEX) romain.loth at inist.fr
# ----------------------------------------------------

export PDF_IN=$1

# GLOBAL VARS
export MAXPAGES=10
export RESOLUTION=800  # doit être > 300x300 dpi

# pour les logs sur STDERR
alias errcho='>&2 echo'

# info sur le nombre de pages total
ACTUALPAGES=`pdfinfo $PDF_IN | grep -a Pages | grep -Po "\d+$"`

# log du précédent
errcho "PDFIN: $ACTUALPAGES pp"

# le nombre de pages à partir de la fin qu'on va demander
export N_pp=$(($ACTUALPAGES>$MAXPAGES?$MAXPAGES:$ACTUALPAGES))

# log
errcho "CONVERSION: $N_pp last pages"

# obtention de la fin du pdf dans un nouveau fichier pdf temporaire: 
# ex: /run/shm/tmp.bibocr-frag-KPihH1.pdf
TMP_FRAG_PATH=`mktemp --tmpdir=/run/shm/ tmp.bibocr-A_frag-XXXXXX.pdf`
pdftk $PDF_IN cat r${N_pp}-r1 output $TMP_FRAG_PATH

# obtention d'images converties correspondantes
convert -density $RESOLUTION $TMP_FRAG_PATH ${TMP_FRAG_PATH}.converted-%02d.png

# OCR-ization
errcho "OCR-IZATION TO STDOUT..."
for IMG in ${TMP_FRAG_PATH}.converted-*.png
 do tesseract $IMG stdout
    echo -ne "\f"
 done

# nettoyage des tmp dans la RAM (/run/shm)
rm -fr $TMP_FRAG_PATH
rm -fr ${TMP_FRAG_PATH}.converted-*.png
