utilitaires-istex : décodage/encodage/accents
=============================================

Scripts de gestion et conversion d'accents et encodages de caractères.

nativeXML_to_utf8XML.pl
-----------------------
Conversion d'un fichier XML depuis l'encodage déclaré en entête vers UTF-8 (avec remplacement déclaration)

nettoie_accents_cara.pl
-----------------------
Script polyvalent de conversion ou suppression d'accents et/ou caractères rares
Dans le cadre d'ISTEX cf. notamment les options -x et -a

Utilisation courante
---------------------

cf.  [procédure conversion UTF-8 échantillons enrich](https://wiki.inist.fr/_media/applis/istex/enrichissement/procedure_harmonisation_envois_partenaires_enrichissement.pdf?id=applis%3Aistex%3Aenrichissement)


    for doc in `ls originaux`
      do echo $doc
       nativeXML_to_utf8XML.pl originaux/$doc \
       | nettoie_accents_cara.pl -x \
       | xmllint --format - > convertis/$doc
      done

