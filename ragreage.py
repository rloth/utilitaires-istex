#! /usr/bin/python3
"""
ragreage.py: Reconstruction de refbibs réelles
             (métadonnées + chaîne d'origine)
             pour créer un corpus d'entraînement
             du modèle CRF "citations" dans Grobid
             
             Si on imagine 2 pôles :
               A- XML data-driven (arbre de structuration de données)
               B- XML text-driven (markup ou annotations d'un texte)
             Alors cet utilitaire cherche à passer de A à B,
             car B est essentiel pour du corpus qui doit servir 
             d'entraînement
             
Principe:
---------
           ARTICLE
           /      \\
      -p PDF     -x XML
      (avec     (biblStruct)
      ponct.)       |
    <pdftotext>     |
        \\         /
         comparaisons
         ------------
      (1) find_bibzone()
      (2) link_txt_bibs_with_xml()
      (3) align xml fields on pdftxt
             | |
           ragréage
             | |
   annotation xml simplifiées* bibl
     sur chaîne verbatim du pdf
     
* simplifiées: moins d'arborescence, mais en préservant toute l'info markup
"""
__copyright__   = "(c) 2014 - INIST-CNRS (projet ISTEX)"
__author__      = "R. Loth"
__status__      = "Development"
__version__     = "1.0"

# IMPORTS
# =======
# I/O
import sys
import argparse
from subprocess import (check_output, CalledProcessError)
from lxml import etree

# fonctions
import re
from math import ceil

# debugger
import pdb

# --------------------------------------------------------

def simple_path(xelt, relative_to = ""):
	"""Construct a path of local-names from tag to root
	   or up to a local-name() provided in arg "rel_to"
	"""
	# starting point
	the_path = localname_of_tag(xelt.tag)
	if the_path == relative_to:
		return "."
	else:
		# ancestor loop
		for pp in xelt.iterancestors():
			pp_locname = localname_of_tag(pp.tag)
			if pp_locname != relative_to:
				# prepend elts on the way
				the_path = pp_locname + "/" + the_path
			else:
				# reached chosen top elt
				break
	# voilà
	return the_path

def localname_of_tag(etxmltag):
	"""Strip etree tag from namespace and return local-name()
	"""
	return re.sub(r"{[^}]+}","",etxmltag)

def link_txt_bibs_with_xml(pdfbibzone, xmlbibnodes, debug = 1):
	"""Trouver quelle biblStruct correspond le mieux à ch. ligne dans zone ?
	
	TODO 
	  - on n'utilise pas assez la double séquentialité
	"""
	
	m_xnodes = len(xmlbibnodes)
	n_pzone = len(pdfbibzone)
	
	# initialisation matrice de décomptes cooc.
	scores_pl_xb = [[0 for j in range(m_xnodes)] for i in range(n_pzone)]

	# remarques sur matrice cooccurrences
	# -----------------------------------
	# en ligne: une ligne digitalisée du pdftotext
	# en colonne: une des refbibs du xml
	#  
	# (~> "similarité" entre les lignes pdf et les entrées xml)
	#
	# la matrice devrait être +- diagonale 
	# car il y a co-séquentialité des deux
	# (transcriptions d'une même source)
	#
	# exemple matrice remplie sur 6 lignes pdf et 4 noeuds xml
	# -----------------------
	# [ 10,  1,  0,  2 ] : "1 M. Morra, E. Occhiello and F. Garbassi, J . Colloid Interface Sci.,"
	# [  3,  0,  0,  0 ] : "1992, 149, 290."
	# [  1,  6,  0,  2 ] : "2 E. N. Dalal, Langmuir, 1987, 3, 1009."
	# [  1,  1,  0,  1 ] : "3 J. Domingue, Am. Lab., October, 1990, p. 5 ."
	# [  2,  1,  0, 13 ] : "4 D. J. Gardner, N. C. Generalla. D. W. Gunnells and M. P."
	# [  0,  1,  0,  5 ] : "Wolcolt, Langmuir, 1991, 7 , 2498."
	
	# la pdfligne 1 (ligne du haut) est très semblable à la 1ère xbib (score de 10)
	# et on voit que la ligne suivante est une suite de cette même xbib (score de 3)
	# (en colonne 3 on voit aussi une des xbibs toute vide)
	# ( => conversion tei en amont probablement mal passée)
	# -----------------------------------
	
	# compte des cooccurrences => remplissage matrice
	# ========================
	for i, probable_bib_line in enumerate(pdfbibzone):
		# représentation de la ligne plus pratique
		# (prépare les bouts de match effectuables avant de les compter ensemble)
		
		pdf_w_tokens =  [o for o in re.split(r'\W+', probable_bib_line) if (len(o) and o not in ["&", "and", "in", "In"])]
		# remarque : split sur "\W+" et non pas "\s+"
		# -------------------------------------------
		# la ponctuation ajoutée ne nous intéresse pas encore 
		# et pourrait gêner l'apparillage des lignes
		
		# print(pdf_w_tokens, file=sys.stderr)
		
		for j, xbib in enumerate(xmlbibnodes):
			# count count
			# décompte de cooccurrences (pl.bow <=> xb.bow)
			for ptok in pdf_w_tokens:
				if debug >= 3:
					print("match essai frag pdf du i=%i: '%s'" %(i , re.escape(tok)), file=sys.stderr)
				
				reptok = re.compile(r"\b%s\b" % re.escape(ptok))
				
				for xtext in xbib.itertext():
					if debug >= 3:
						print("\tsur frag xml du j=%i: %s" % (j, xtext), file=sys.stderr)
					
					# MATCH !
					if reptok.search(xtext):
						if debug >= 3:
							print("\t\tMATCH (i=%i, j=%i)!" % (i,j), file=sys.stderr)
						scores_pl_xb[i][j] += 1 
						# + d'un match de même ptok sur le même xtxt n'est pas intéressant
						break
	
	# pour log
	# --------
	if debug >= 2:
		# reboucle: affichage détaillé pour log de la matrice des scores
		for i in range(len(pdfbibzone)):
			# ligne courante : [valeurs de similarité] verbatim de la ligne
			print("pdf>biblio>l.%i: %s (max:%i) txt:'%s'" % (
					  i,
					  scores_pl_xb[i], 
					  max(scores_pl_xb[i]), 
					  # correspond à pdflines[debut_zone+i]
					  pdfbibzone[i]
					 ),
				file=sys.stderr)
	
	
	# RECHERCHE champions   
	# ===================
	# [argmax_j de scores[i][j] for j in xbibs], for i in pdflines
	#
	# => à remplir ici
	champions = [None for x in range(n_pzone)]
	
	# mémoire du précédent pour favoriser ré-attributions *du même*
	mem_previous_argmax_j = None
	
	# TODO mémoire plus longue pour favoriser attributions consécutives *du suivant* [i+1] aussi
	
	for i in range(n_pzone):
		# a priori on ne sait pas
		argmax_j = None
		
		# on espère un score gagnant franc, mais peut être 0
		the_max_val = max(scores_pl_xb[i])
		
		# on n'utilise pas indexof(the_max_val) car si *ex aequo* on les veut tous
		candidats = [j for j in range(nxb) if scores_pl_xb[i][j] == the_max_val]
		
		# si plusieurs ex aequo
		# ----------------------
		if len(candidats) > 1:
			
			# cas à noter: la ligne est pratiquement vide
			if the_max_val == 0:
				champions[i] = None
				if debug >= 1:
					print( "l.%i %-75s: NONE tout à 0" % (i, pdfbibzone[i]), file=sys.stderr)
			
			# cas rare: attribution raisonnable au précédent
			# ... si mem_previous_argmax_j in candidats
			#     malgré ambiguïté des similarités
			elif (mem_previous_argmax_j in candidats
			     and the_max_val > 5
			     and len(candidats) <= nxb/10):
				# Explication
				# - - - - - -
				# ex: txt:'T., Furukawa, T., Yamada, K., Akiyama, S. and' 
				#     candidats exaequo bibs [7, 9, 28] à max 7
				#     et mem_previous_argmax_j = 9
				# cas ambigüs (eg auteurs aussi présents ailleurs,
				#              ou que des mots présents ailleurs)
				# mais consécutifs à une attribution claire
				#      - - - - - - - - - - - - - - - - - - -
				# => bravo REPECHAGE !
				argmax_j = mem_previous_argmax_j
				champions[i] = argmax_j
				
				# log
				if debug >= 1:
					ma_bS = xbibs[argmax_j]
					infostr = glance_xbib(ma_bS)
					print( "l.%i %-75s: WINs suite XML %s %s (max=%s) (repêchage parmi %s ex aequo)" % (
						  i,
						  pdfbibzone[i],
						  argmax_j,
						  infostr,
						  the_max_val, 
						  candidats
						 ),
						file=sys.stderr)
			# cas générique ex aequo: *match pas concluant*
			# - - - - - - - - - - - - - - - - - - - - - - -
			else:
				if debug >= 1:
					print("l.%i %-75s: NONE exaequo bibs %s (maxs=%i)"  % (
						  i,
						  pdfbibzone[i],
						  candidats, 
						  the_max_val, 
						 ),
						file=sys.stderr)
		
		# --------------------------------
		# là on a un match intéressant...
		# --------------------------------
		elif len(candidats) == 1:
			
			# on en a un !
			argmax_j = candidats.pop()
			
			# à quelles valeurs max s'attendre ?
			# -----------------------------------
			# Pour une **ligne normale** on aura en général the_max_val > 10 avec observés [6-17]
			# (citation entière ou début d'une citation sur ligne entière :
			# la valeur max est alors assez haut : bon nombre d'infos casées
			
			# Par contre pour une **ligne de continuation** il est tout 
			# à fait normal d'avoir une max_val basse, à 1 ou 2
			# (donc plus difficile à repérer)
			
			# ligne normale
			if argmax_j != mem_previous_argmax_j:
				
				# match pas folichon
				if the_max_val < 5 :
					if debug >= 1:
						print("l.%i %-75s: WEAK (max=%i) (x vide? ou cette ligne p vide ?)" % (i, pdfbibzone[i], the_max_val), file=sys.stderr)
					# oublier résultat incertain
					argmax_j = None
				
				# xml correspondant trouvé !
				else:
					# bravo !
					champions[i] = argmax_j
					
					# log
					if debug >= 1:
						ma_bS = xbibs[argmax_j]
						infostr = glance_xbib(ma_bS, longer=True)
						print( "l.%i %-75s: WIN1 entrée XML %s %s (max=%i)" % (
							  i,
							  pdfbibzone[i],
							  argmax_j,
							  infostr,
							  the_max_val
							 ),
							file=sys.stderr)
			
			# ligne de continuation potentielle (même xbib préférée que le précédent)
			else:
				# moyenne des autres
				the_drift = sum([x for j,x in enumerate(scores_pl_xb[i]) if j != argmax_j]) / nxb
				
				# tout le reste est bas, on est plus haut 
				# et on trouve le même que mémorisé
				# => on va dire que c'est concluant !
				if (the_max_val > 2 * the_drift):
					# bravo !
					champions[i] = argmax_j
					
					# log
					if debug >= 1:
						ma_bS = xbibs[argmax_j]
						infostr = glance_xbib(ma_bS, longer=True)
						print( "l.%i %-75s: WINs suite XML %s %s (max=%i vs d=%f) " % (
							  i,
							  pdfbibzone[i],
							  argmax_j,
							  infostr,
							  the_max_val, 
							  the_drift
							 ),
							file=sys.stderr)
				else:
					# TODO mettre une info "__WEAK__" dans champions[i] pour diagnostics
					if debug >= 1:
						print("l.%i %-75s: WEAK (max=%i vs d=%f)" % (
							  i,
							  pdfbibzone[i],
							  the_max_val,
							  the_drift
							 ),
							file=sys.stderr)
		# wtf?
		else:
			raise ValueError("len(candidats)")
		
		# mémorisation de durée 1
		mem_previous_argmax_j = argmax_j
	
	# liste pour chaque ligne i la valeur de bib j trouvée, ou None
	return champions
	
	# exemple interprétation liste
	# ----------------------------
	# [None, 0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, None, None, None, None, 4, 5, 5, 6, 6, 7, 7]
	#                    ^^^^^^^^                ^^^^^^^^^^^^^^^^^^^^^^ 
	#                ici lignes i=[6,7,8]       probablement saut de page
	#                 matchent xbib j=2

# --------------------------------------------------------

def check_align_seq(array_of_xidx):
	"""Diagnostics sur les champions par ligne issus des matrices scores_pl_xb ?
	# fonction TODO
	"""
	pass
	# fonction TODO: signalerait les séquences en désordre pour diagnostics

	# exemple 1: rsc_1992_P2_P29920001815
	# Les champions: [12, 12, 13, None, 14, 14, 14, 15, 15, 15, 15, 16, 16, 16, 17, 18, 18, 18, 18, 19, None, None, 18, 10, 28, 14, 21, 21, 21, 21, 22, 22, 23, 24, 24, None, 25, None, None, None, 26, None, 26, None, 27, 27, 28, 28, None, 28, 10, None, 29, None, None, 15, 30, 30, None, 31, None, 31, None, 5, 32, 32, None, 33, 0, 34]
	
	# explication : le pdf a un layout mal ficelé
	# (deux colonnes du PDF mais pas dans le rendu)
	
	#     aaaa           citation 12
	#     blab           citation 12 (suite)
	#     bla            citation 13
	#  REFS:               (....)
	#   citation 1       citation 25
	#    (....)            (....)
	#   citation 7       citation 32
	#   citation 8
	#    (....)
	#   citation 11
	
	# dans le rendu les cit 1..7 se mélangent avec le 25..32
	#            et les cit 8..11 sont carrément hors zone
	
	## exemple 2 le pdf est ok mais notre algo fait deux matchs hors ordre
	## (noms de famille identiques et 'and' => ce dernier ne matche plus)
	# Les champions: [0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 3, 3, 4, 5, 5, 6, None, None, None, None, None, None, 7, 7, 7, 8, 8, 9, 28, 9, 9, 10, 10, 10, 10, 11, 11, 11, 12, 12, 12, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 15, 16, 16, 16, 17, 17, 18, 18, 18, 18, None, None, None, 5, None, 19, 19, 20, 20, 20, 20, 21, 21, 21, 21, 22, 22, 22, None, 23, 23, 23, 24, 24, 24, 25, 25, 25, 25, 26, 26, 26, 27, 27, 27, 28, 28, 28, 28, 28, 29, 29]
	
	# exemple 3: rsc_1997_CS_CS9972600425
	#   le pdf est ok, par contre 
	#       - il a des interlignes (bas de page) qui intercalent des groupes de 5 à 7 None entre les bibs 4 et 5, 16 et 17
	#       - le debut de zone est trop tôt (window span trop grand en amont?) => il y a des None avant la bib 0
	#       - les bibs 14,15,16 et 17 ont ~ les mêmes auteurs => matchs plus WEAK ex aequo (et pas de décision pour la 17)
	# Les champions: [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, 0, 1, 1, 2, 2, 3, 4, None, None, None, None, None, 5, 6, 7, 7, 8, 8, 8, 9, 9, 10, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 14, 15, 15, 16, 16, 16, None, None, None, None, None, None, None, 18, 18, 19, 19, None, None, 21, 21, None, 22, 23, 23, 24, 25, 25, 26, 26, 27, 28, 29, 30, 30, None, None, None]


# --------------------------------------------------------

def find_bib_zone (xmlbibnodes, rawtxtlines, debug=0):
	"""Trouve la zone de bibs dans du texte brut
	       - en utilisant les infos de la bibl structurée XML 
	         supposée dispo (ça aide beaucoup)
	       - en regardant l'aspect intrinsèque de la ligne (aide la précision du précédent)
	       - ou tout simplement si on trouve l'intitulé "References"
	"""
	# integers to be found (indices)
	debut = None
	fin = None
	
	# var remplie ssi vu l'expression /References:?/
	# => simplifie la recherche du début !
	ref_header_i0 = None
	re_linereferences_header = re.compile(r"^R ?[Ee] ?[Ff] ?[Ee] ?[Rr] ?[Ee] ?[Nn] ?[Cc] ?[Ee] ?[Ss]?s*:?\s*$")
	
	# decompte de 'clues'
	# ===================
	# on mesure les occurrences dans pdflines de:
	#   - search_toks : tout fragment connu xbib
	#   - re_... : helper tokens = certaines propriétés biblio-like
	#                              (commence par majusc, label, etc)

	# n = nombre de lignes
	n_lines = len(rawtxtlines)
	
	# --------------
	# xmlelts tokens
	# --------------
	# count array for each match re.search(r'xmlelts', textline)
	tl_match_occs = []
	
	# pour décompte un pré-préalable : 
	# regex compile each token found in the xml
	search_toks = set()
	for st in XMLTEXTS:
		for tok in re.split(r"\W+", st):
			if is_searchable(tok):
				etok = re.escape(tok)
				search_toks.add(re.compile(r"\b%s\b" % etok))
	
	# TODO : est-ce que les noms communs du XML content devraient être enlevés ?
	# cf. ech/tei.xml/oup_Geophysical_Journal_International_-2010_v1-v183_gji121_3_gji121_3xml_121-3-789.xml
	
	if debug >= 2:
		print (search_toks, "<== Those are the searched tokens", file=sys.stderr)
	
	
	# -------------
	# helper tokens (puncts, digits, capitalized letters)
	# -------------
	# pdc toks count array
	pdc_match_occs = []
	
	# date + ponctuation (très caractéristique des lignes refbib) : exemples "(2005)", "2005a," 
	re_datepunct = re.compile(r"[:;,.\(\[]?\s?(?:18|19|20)[0-9]{2}[abcde]?\s?[:;,.\)\]]")
	# exemples : "68(3):858-862" ou "68: 858-862" ou "68: 858"
	re_vol_infoA = re.compile(r"[0-9]+(?:\([0-9]+\))?\s?:\s?[0-9]+\s?(?:[-‒–—―−﹣]\s?[0-9]+)?")
	# exemples : "vol. 5, no. 8, pp. 1371"   "Vol. 5, No. 8, pp 1371-1372
	re_vol_infoB = re.compile(r"\b[Vv]ol\.?\s?[0-9]+\s?[,\.;]\s?[Nn]o\.?\s?[0-9]+\s?[,\.;]\s?pp?\.?\s?\d+\s?[-–]?\s?\d*")
	# exemples : "68(3), 858-862" ou "68, 858-862"
	re_vol_infoC = re.compile(r"[0-9]+(?:\([0-9]+\))?\s?,\s?[0-9]+\s?[-‒–—―−﹣]\s?[0-9]+")
	
	# reconnaissance de fragments très générique : marche uniquement car vol n'est pas un mot (l'équivalent pour "No" serait irréaliste)
	re_vol = re.compile(r"\b[Vv]ol\.?(?=[\s\d])")
	re_ppA = re.compile(r"\bpp\.?(?=[\s\d])")
	re_ppB = re.compile(r"\b[0-9]+\s?[-‒–—―−﹣]\s?[0-9]+\b")
	# plus rares mais surs (à cause de la présence du ':')
	re_in = re.compile(r"\b[Ii]n ?:")
	re_doi = re.compile(r"\bdoi: ?10\.[\S]+")
	
	# re_init <=> intéressants seulement en début de ligne -> re.match
	re_initlabel = re.compile(r"\[.{1,4}\]")
	re_initcapncap = re.compile(r"(?:\[.{1,4}\])\s*[A-Z].*?\b[A-Z]")
	
	# -------------------
	# boucle de décompte 
	# -------------------
	for i, tline in enumerate(rawtxtlines):
		# new initial counts for this line
		tl_match_occs.append(0)
		pdc_match_occs.append(0)
		
	# filter out very short text lines
		if len(tline) <= 2:
			next
		
		# - - - - - - - - - - - - - - - - - - - -
		# décompte principal sur chaque xfragment
		# - - - - - - - - - - - - - - - - - - - -
		for tok_xfrag_re in search_toks:
			# 2 points if we matched an XML content
			if re.search(tok_xfrag_re, tline):
				tl_match_occs[i] += 2
		
		# décompte indices complémentaires
		# indices forts => 2 points
		pdc_match_occs[i] += 2 * len(re.findall(re_datepunct, tline))
		pdc_match_occs[i] += 2 * len(re.findall(re_vol_infoA, tline))
		pdc_match_occs[i] += 2 * len(re.findall(re_vol_infoB, tline))
		pdc_match_occs[i] += 2 * len(re.findall(re_vol_infoC, tline))
		pdc_match_occs[i] += 2 * len(re.findall(re_in, tline))
		pdc_match_occs[i] += 3 * len(re.findall(re_doi, tline))
		
		# indices plus heuristiques => 1 points
		pdc_match_occs[i] += 1 * len(re.findall(re_vol, tline))
		pdc_match_occs[i] += 1 * len(re.findall(re_ppA, tline))
		pdc_match_occs[i] += 1 * len(re.findall(re_ppB, tline))
		
		# indices ancrés sur ^ 
		# initlabel
		if re.match(re_initlabel, tline):
			pdc_match_occs[i] += 2
		
		# initcap
		if re.match(re_initcapncap, tline):
			pdc_match_occs[i] += 2
		
		# -------------------8<-----------------------
		# au passage si on trouve le début directement
		# (ne fait pas partie des décomptes mais même boucle)
		if re.match(re_linereferences_header, tline):
			# on reporte ça servira plus tard
			ref_header_i0 = i
		# -------------------8<-----------------------
		
		# listing d'observation détaillée
		if debug >= 1:
			print("-"*20+"\n"+"line n. "+str(i)+" : "+tline, file=sys.stderr)
			print("found %i known text fragments from XML content" %  tl_match_occs[i], file=sys.stderr)
			print("found %i typical bibl formats from helper toks" % pdc_match_occs[i] + "\n"+"-"*20, file=sys.stderr)
	
	# sum of 2 arrays
	all_occs = [(tl_match_occs[i] + pdc_match_occs[i]) for i in range(n_lines)]
	
	# log: show arrays
	if debug >= 2:
		print("tl_match_occs\n",tl_match_occs, file=sys.stderr)
		print("pdc_match_occs\n",pdc_match_occs, file=sys.stderr)
	if debug >= 1:
		print("all_match_occs\n",all_occs, file=sys.stderr)
	
		# type de résultat obtenu dans tl_match_occs (seq de totaux par ligne):
		# [0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0,
		#  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
		#  0, 0, 0, 0, 0, 0, 5, 8, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0,
		#  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
		#  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0,
		#  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
		#  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
		#  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0,
		#  7, 3, 6, 1, 3, 10, 0, 0, 11, 8, 2, 0, 0]
		
		# !! potentiellement jusqu'à 20 fois + gros
	
	
	# -----------------------
	# Répérage proprement dit
	
	# LE DEBUT
	# ========
	
	# cas si on a déjà le début 
	# --------------------------
	if ref_header_i0 is not None:
		# la ligne après l'entête
		debut = ref_header_i0 + 1
	
	else:
		# identification début si on n'a qu'une bib
		# -----------------------------------
		if (len(xmlbibnodes) == 1):
			# cas un peu spécial : 
			# ==> on ne peut pas compter sur vérifs des lignes d'avant/après
			# ==> on prend la ligne max puis éventuellement suivante(s)
			
			argmax_i = all_occs.index(max(all_occs))
			debut = argmax_i
		
		# identification si on a plusieurs bibs
		# -----------------------------------------------
		# Décision d'après all_occs avec grand lookahead
		# -----------------------------------------------
		else:
			# all_occs => Là-dedans on cherche une zone 
			#            avec des décomptes :
			#              - assez hauts
			#              - plutôt consécutifs,
			#              - formant une séquence de taille 
			#                de 1 à ~7 fois la longueur de nxbibs
			
			# !! sans se faire piéger par les appels de citation,
			# !! qui provoquent des pics du décompte de matches, mais plus épars 
			
			# Dans l'exemple d'all_occs plus haut, la liste biblio 
			# est sur les lignes [160:170] et commence par [7,3,6,..]
			# Mais le pic à 5 puis 8 est un piège... 
			
			# On peut éviter les pics locaux si on regarde les sommes
			# sur une fenêtre ou chunk de l lignes un peu plus gros
			
			# -----------------------------------------------------
			# large sliding lookahead window over sums in all_occs
			desired_chunk_span = ceil(3.2 * len(xmlbibnodes))
			# param 3.2 fixé après quelques essais 
			# dans doc/tables/test_pdf_bib_zone-pour_ragreage.ods
			
			if debug >= 1:
				print("looking for debut_zone in Σ(occs_i...occs_i+k) over all i, with large window span k", desired_chunk_span, file=sys.stderr)
			
			# score le + haut ==> sera celui de la zone dont les contenus  
			#                     correspondent le plus à ceux des xbibs
			max_chunk = -1
			
			# i correspondant au (dernier) score le plus haut
			i_last_max_chunk = -1
			
			# sums by chunk starting at a given i
			summs_by_chunk_from = []
			
			for i,ici in enumerate(all_occs):
				
				# init sum
				summs_by_chunk_from.append(0)
				
				for k in range(desired_chunk_span):
					# stop count at array end
					if (i + k) >= n_lines:
						break
					# normal case : add freq count
					else:
						summs_by_chunk_from[i] += all_occs[i+k] 
				
				# judge last max 
				# (if window span is a little over the real 
				#  length of the bib zone in the pdf
				#  then *last* max should be right answer)
				if summs_by_chunk_from[i] == max_chunk:
					i_last_max_chunk = i
				if summs_by_chunk_from[i] > max_chunk:
					max_chunk = summs_by_chunk_from[i]
					i_last_max_chunk = i
				
				if debug >= 3:
					# affiche chaque step
					print("line", i,
					  "this sum", summs_by_chunk_from[i],
					  "last max sum", max_chunk,
					  "idx of last max", i_last_max_chunk, file=sys.stderr)
			
			if debug >= 2:
				print("windowed sums:", summs_by_chunk_from, file=sys.stderr)
			
			# Décision début
			# --------------
			
			# début: je suis sur que c'est lui !
			debut = i_last_max_chunk
		
		if debug >= 1:
			print("max_chunk:", max_chunk, "\nfrom i:", debut, file=sys.stderr)
		
	# LA FIN
	# ======
	
	# Décision avec petit lookahead
	# ------------------------------
	# on a encore besoin d'une fenêtre
	# mais plus courte (~ 10 lignes)
	# pour trouver la descente
	shorter_span = min(int(len(xmlbibnodes)/2), 10)
	
	if debug >= 1:
		print("looking for fin_zone in Σ(occs_i...occs_i+l) over all i > debut, with with small window span l", shorter_span, file=sys.stderr)
	
	summs_shorter_lookahead = []
	for i in range(n_lines):
		summs_shorter_lookahead.append(0)
		# inutile de se retaper tout le début du doc avant début zone
		if i < debut:
			next
		for l in range(shorter_span):
			if (i + l) >= n_lines:
				break
			else:
				summs_shorter_lookahead[i] += all_occs[i+l]
	
	# curseur temporaire à l'endroit le plus court possible (si une ligne par xbib)
	fin = debut + len(xmlbibnodes)
	
	# prolongement portée jq vraie fin : 
	while summs_shorter_lookahead[fin+1] > 0:
		# tant que freq_suivants > 0:
		# on suppose des continuations consécutive de la liste des biblios
		# ==> on décale la fin
		fin += 1
	
	# log résultat
	print ("N lignes: %i\ndeb: ligne %s (\"%s\")\nfin: ligne %s (\"%s\")"
		   %(
		     n_lines, 
		     debut, "_NA_" if debut is None else rawtxtlines[debut] ,
		     fin, "_NA_" if fin is None else rawtxtlines[fin]
		     ),
		  file=sys.stderr)
	
	# filtre si début beaucoup trop tot
	# comparaison len(bibs) len(pdflines)
	if (nxb * 8 <  (fin - debut)):
		print ("WARN ça fait trop grand, je remets deb <- None", file=sys.stderr)
		debut = None
	
	return (debut, fin)

# --------------------------------------------------------

def glance_xbib(bS, longer = False):
	"""Donne un infostr ou aperçu du contenu d'une biblio structurée XML
	
	Arguments:
		bS -- l'entrée biblio
		longer -- un booléen pour format étendu 
	"""
	# variables du glance
	# article title if present, or monog title, or nothing 
	main_title  = None
	main_author = None
	the_date  = None
	the_id    = None
	
	# id
	id_elt = bS.xpath("@xml:id")
	if len(id_elt):
		the_id = id_elt[0]
		
	# date
	date_elts = bS.xpath(".//tei:imprint/tei:date", namespaces=NSMAP)
	if len(date_elts):
		the_date = date_elts[0].text[0:4]
	
	# check bool entrée analytique ??
	has_analytic  = (len(bS.xpath("tei:analytic", namespaces=NSMAP)) > 0)
	
	
	if has_analytic:
		ana_tit_elts = bS.xpath("tei:analytic/tei:title", namespaces=NSMAP)
		if len(ana_tit_elts):
			main_title = ana_tit_elts[0].text 
		
		ana_au_elts = bS.xpath("tei:analytic/tei:author//tei:surname", namespaces=NSMAP)
		if len(ana_au_elts):
			main_author = ana_au_elts[0].text
	
	# on va chercher auteur et titre dans monogr si ils manquaient dans analytic
	if (main_title is None):
		monogr_tit_elts = bS.xpath("tei:monogr/tei:title", namespaces=NSMAP)
		if len(monogr_tit_elts):
			main_title = monogr_tit_elts[0].text
		else:
			main_title = "_NA_"
	
	if (main_author == None):
		monogr_au_elts = bS.xpath("tei:monogr/tei:author//tei:surname", namespaces=NSMAP)
		if len(monogr_au_elts):
			main_author = monogr_au_elts[0].text
		else:
			main_author = "_NA_" # on ne laisse pas à None car on doit renvoyer str
	
	# NB : il peuvent éventuellement toujours être none si éléments à texte vide ?
	
	# build "short" string
	my_desc = "("+main_author[:min(5,len(main_author))]+"-"+str(the_date)+")" 
	
	# optional longer string
	#~ if longer:
		#~ maxlen = min(16,len(main_title))
		#~ my_desc = the_id+":"+my_desc+":'"+main_title[:maxlen]+"'"
	
	return my_desc

# --------------------------------------------------------

def is_searchable(a_string):
	"""Filtre des chaînes texte
		------------------------
		Retourne:
		  - False: chaînes de caractères ne pouvant servir 
		           comme requêtes de recherche
		  - True : toute autre chaîne
	""" 
	return ((a_string is not None) 
	       and (len(a_string) > 1)
	       and (not re.match("^\s+$",a_string))
	       and ( # éviter les mots sans majuscules et très courts (with, even..)
	               len(a_string) > 4 
	            or re.match("^[A-Z0-9]", a_string)
	           )
	       )











###############################################################
########################### M A I N ###########################
###############################################################
if __name__ == "__main__":
	
	# options et arguments
	# ====================
	parser = argparse.ArgumentParser(
		description="Ajout des ponctuations réelles dans un xml de refbibs (NB lent: ~ 2 doc/s sur 1 thread)",
		usage="ragreage.py -x ech/tei.xml/oup_Human_Molecular_Genetics_1992-2010_v1-v19_hmg18_18_hmg18_18xml_ddp278.xml -p ech/pdf/oup_Human_Molecular_Genetics_1992-2010_v1-v19_hmg18_18_hmg18_18pdf_ddp278.pdf",
		epilog="-----(© 2014 Inist-CNRS (ISTEX) romain.loth at inist dot fr )-----")
	
	parser.add_argument('-x','--xmlin',
		metavar='path/to/xmlfile',
		help='path to a TEI.xml with citations in <biblStruct> xml format (perhaps to be created from native XML by a call like `saxonb-xslt -xsl:tools/Pub2TEI/Stylesheets/Publishers.xsl -s:exemples_RONI_1513/rsc_1992_C3_C39920001646.xml`)',
		type=str,
		required=True,
		action='store')
		
	parser.add_argument('-p','--pdfin',
		metavar='path/to/pdffile',
		help='path to a pdf file of the same text, for attempted pdftottext and citation regexp match',
		type=str,
		default=None ,  # cf juste en dessous
		required=False,
		action='store')
		
	parser.add_argument('-d','--debug',
		metavar=1,
		type=int,
		help='logging level for debug info in [0-3]',
		default=0,
		required=False,
		action='store')
	
	
	args = parser.parse_args(sys.argv[1:])
	
	# défault pdfin
	if args.pdfin == None :
		temp = re.sub(r'tei.xml', r'pdf', args.xmlin)
		args.pdfin = re.sub(r'xml', r'pdf', temp)
		print("PDFIN?: essai de %s" % args.pdfin, file=sys.stderr)
	
	
	#    INPUT XML
	# ================
	print("LECTURE XML", file=sys.stderr)
	
	# TODO ==> on signale au passage les colonnes vides (xbibs vides en amont)
	
	# parse parse
	parser = etree.XMLParser(remove_blank_text=True)
	
	try:
		dom = etree.parse(args.xmlin, parser)
	
	except OSError as e:
		print(re.sub("': failed to load external entity.*", "' (fichier absent ?)", str(e)), file=sys.stderr)
		sys.exit()
	
	NSMAP = {'tei': "http://www.tei-c.org/ns/1.0"}
	
	# query query
	xbibs = dom.findall(
				"tei:text/tei:back/tei:div/tei:listBibl/tei:biblStruct",
				namespaces=NSMAP
				)
	xbibs_plus = dom.xpath(
				"tei:text/tei:back/tei:div/tei:listBibl/*[local-name()='bibl' or local-name()='biblStruct']",
				 namespaces=NSMAP
				)
	
	# pour logs
	# ---------
	nxb = len(xbibs)
	nxbof = len(xbibs_plus) - nxb
	
	# si présence de <bibl>
	if (nxbof - nxb > 0):
		print("WARN: %i entrées dont  %i <bibl> (non traitées)" % (nxb+nxbof, nxbof), file=sys.stderr)
	
	# exception si aucune <biblStruct>
	if (nxb == 0):
		print("ERR: aucune xbib <biblStruct> dans ce xml natif !", file=sys.stderr)
		sys.exit()
	
	
	# préalable: passage en revue des XML ~> diagnostics (vars globales)
	# ----------
	
	# pour corresp. indice j <=> n° XML:ID (si trouvé, souvent == label)
	XMLIDMAP = [None for j in range(nxb)]
	FLAG_STD_MAP = True # sera confirmé ou deviendra False
	
	# tous les contenus texte des elts xml, en vrac
	XMLTEXTS = []
	
	# remplissage des deux: XMLIDMAP et XMLTEXTS
	for j, xbib in enumerate(xbibs):
		xbib_id = xbib.xpath("@xml:id").pop()
		
		# numérotation en fin d'ID eg 1,2 ou 3 dans DDP278C1 DDP278C2 DDP278C3
		nums = re.findall(r"[0-9]+^", xbib_id)
		XMLIDMAP[j] = xbib_id
		# print('nums', nums, 'pour j =',j, file=sys.stderr)
		
		# au passage diagnostic labels
		if (len(nums)) and (int(nums[0]) != j+1) and FLAG_STD_MAP: 
			FLAG_STD_MAP = False
		
		bibtexts=[]
		
		for eltstr in xbib.itertext():
			bibtexts.append(eltstr)
		
		# TODO : vérifier si intéressant de les préserver séparément (liste de listes)
		XMLTEXTS += bibtexts

		# log si debug
		if args.debug >= 1:
			print(("-"*50)+ 
		           "\nlecture des contenus texte xmlbib %i (@xml:id='%s')" 
		              % (j, xbib_id), file=sys.stderr)
			print(bibtexts, file=sys.stderr)
	
	
	if FLAG_STD_MAP:
		print("GOOD: numérotation ID <> LABEL traditionnelle", file=sys.stderr)
	else:
		# todo préciser le type de lacune observée (pas du tout de labels, ID avec plusieurs ints, ou gap dans la seq)
		print("WARN: la numérotation XML:ID ne contient pas un label unique incrémental", file=sys.stderr)
	
	print(XMLIDMAP, file=sys.stderr)
	
	
	#  INPUT PDF à comparer
	# ======================
	print("---\nLECTURE PDF", file=sys.stderr)

	# appel pdftotext via OS
	try:
		pdftxt = check_output(['pdftotext', args.pdfin, '-']).decode("utf-8")
	
	except CalledProcessError as e:
		print("Echec pdftotxt: cmdcall: '%s'\n  ==> FAILED (file not found?)" % e.cmd, file=sys.stderr)
		# print(e.output, file=sys.stderr)
		sys.exit()
	
	# got our pdf text!
	pdflines = [line for line in pdftxt.split("\n")]
	
	# TODO éventuellement
	# filtrer deux ou 3 lignes autour du FORM FEED ^L 
	# pour essayer de virer les hauts et bas de page
	
	
	#  Recherche zone biblio
	# ========================
	print("---\nFIND PDF BIBS", file=sys.stderr)
	
	# La zone biblio dans le texte  pdf est un segment marqué par 2 bornes
	#       (par ex: d=60 et f=61 on aura |2| lignes intéressantes)
	# ----------------------------------------------------------------------
	(debut_zone, fin_zone) = find_bib_zone(xbibs, pdflines)
	
	#  !! debut_zone et fin_zone sont des bornes inclusives !!
	#  !!         donc nos slices utiliseront fin+1         !!
	#                      ------             -----
	
	if ((debut_zone == None) or  (fin_zone == None)):
		print("ERR: trop difficile de trouver la zone biblio dans ce texte '%s'" % args.pdfin, file=sys.stderr)
		sys.exit()
	
	#  Alignement lignes txt <=> entrées XML
	# =======================================
	print("---\nLINK PDF BIBS <=> XML BIBS", file=sys.stderr)
	# (à présent: match inverse)
	
	winners = link_txt_bibs_with_xml(pdflines[debut_zone:fin_zone+1], xbibs)
	
	# affiche résultat
	print("Les champions: %s" % winners, file=sys.stderr)
	
	# we want all content from pdf numbered using its associated xml idx
	# ------------------------------------------------------------------
	# résultat à remplir
	xlinked_real_lines = [None for j in range(nxb)]
	
	for i_prime, j0 in enumerate(winners):
		if j0 is not None:
			# nouveau morceau
			if xlinked_real_lines[j0] is None:
				xlinked_real_lines[j0] = pdflines[debut_zone+i_prime]
			# morceaux de suite
			else:
				# on recolle (avec un marqueur : <lb>)
				xlinked_real_lines[j0] += '\n'+pdflines[debut_zone+i_prime]
		else:
			# we *ignore* None values 
			# => if we wanted them we need to fix them earlier
			# (could be failed matches, gaps in the list
			#  lines before 1st ref or lines after last ref)
			pass
	
	# log linked results
	if args.debug >= 1:
		print("="*70, file=sys.stderr)
		for j in range(nxb):
			if xlinked_real_lines[j] is None:
				print(glance_xbib(xbibs[j], longer = True) + "\n<==> NONE", file=sys.stderr)
			else:
				print(glance_xbib(xbibs[j], longer = True) + "\n<==>\n"
				+ xlinked_real_lines[j], file=sys.stderr)
			print("="*70, file=sys.stderr)
	
	
	#  Enfin alignement des champs sur le texte et récup ponct
	# =========================================================
	print("---\nLINK PBIB TOKENS <=> XBIB FIELDS\n", file=sys.stderr)
	# reconstitution séquence réelle des champs pdf, mais avec balises
	
	# £log de l'étape précédente
	if args.debug >= 1:
		print(xlinked_real_lines, file=sys.stderr)
	
	# pour la tokenisation des lignes via re.findall
	re_tous = re.compile(r'\w+|[^\w\s]')
	re_contenus = re.compile(r'\w+')
	re_ponctuas = re.compile(r'[^\w\s]')
	
	
	# tempo £stockage infos par xbib
	xbibinfos = [None for j in range(nxb)]
	
	for j, group_of_real_lines in enumerate(xlinked_real_lines):
		
		# à remplir 
		pile = []
		
		# préserve la ponctuation
		veritable_tokens_from_pdf = re_tous.findall(group_of_real_lines)
		# tokenisation plus exhaustive qu'auparavant sur ce sous-ensemble "validé"
		# remarque : on n'utilise pas de split pour préserver la ponctuation
		
		# log
		if args.debug >= 2:
			print("-"*50, file=sys.stderr)
			print("pdf lines:", veritable_tokens_from_pdf)
			print("xml entry:", glance_xbib(xbibs[j]), file=sys.stderr)
		
		
		# on prépare les infos XML qu'on s'attend à trouver
		# ------------------------
		this_xbib = xbibs[j]
		
		# on utilise iter() et pas itertext() pour avoir les chemins rel
		subelts = [xelt_t for xelt_t in this_xbib.iter()]
		
		xbibinfos[j] = [None for t in range(len(subelts))]
		
		# £ préparer directement les prénoms ici?
		for t, xelt in enumerate(subelts):
			xrelpath = simple_path(xelt, relative_to = localname_of_tag(this_xbib.tag))
			
			xbibinfos[j][t] = xrelpath
			
			print(xrelpath, xbibinfos[j][t])
			
			if args.debug >= 2:
				print("***", file=sys.stderr)
				print("xrelpath:", xrelpath, file=sys.stderr)
		
		
		#pdb.set_trace()
		
		# ------------------------------------>8--------------------
		
	print(xbibinfos)
		
		# ------------------------------------>8--------------------
		
		#~ # ON SE CALE SUR L'ORDRE DU TEXTE D'ORIGINE
		#~ # ------------------------------------------
		#~ # mais par contre on va suivre la progression avec un curseur
		#~ # de la métadonnée de la petite boucle => registre par méta des curseurs
		#~ for vtok in veritable_tokens_from_pdf:
				#~ revtok = re.compile(r"\b%s\b" % re.escape(vtok))
				#~ 
				#~ # on utilise iter() et pas itertext() parce qu'on
				#~ # devra expliciter tous les chemins avec getparent()
				
				# £ ou bien remplacer par xbibinfos[j]
				
				#~ for xelt in this_xbib.iter():
					#~ xrelpath = simple_path(xelt, relative_to = container_locname)
					#~ 
					#~ if args.debug >= 2:
						#~ print("***", file=sys.stderr)
						#~ print("xrelpath:", xrelpath, file=sys.stderr)
					#~ 
					#~ # on reporte les correspondances
					#~ 
					#~ # cas particulier:  les noms+prénoms à garder ensemble
					#~ # pour biblStruct/analytic/author|biblStruct/analytic/editor
					#~ if (re.search(r"/persName/(?:(?:sur|fore)name|genName)$", xrelpath)):
						#~ print("noms", xrelpath, " -- texte:", xelt.text, file=sys.stderr)
						#~ # TODO couplage AB puis match directement toutes possibilités
						#~ # eg r"A(\W)+B" et r"B(\W)+A"
					#~ 
					#~ # cas normal
					#~ else:
						#~ if (xelt.text is not None) and (revtok.search(xelt.text)):
							#~ print("\t\tMATCH! '%s' <=> %s:'%s' " % (vtok, xrelpath, xelt.text))
						#~ # on empile les ponctuations
						#~ else:
							#~ pass
							#~ #pile_trouvés.append((vtok, "ponct"))
						#~ 
						#~ # on recense aussi les éléments tail qu'on ne sait pas traiter
						#~ if (xelt.tail is not None and not re.match("^\s+$", xelt.tail)):
							#~ print("VU un tail de '%s' pour %s" % (xelt.tail, xrelpath),
								  #~ file=sys.stderr)


		# registre des curseurs par xelt
		# progressent au fur et à mesure des tokens
		# (ça permettra en gros de savoir où on en était après le xrelpath suivant)
		# last_offsets = {}


#~ {
#~ # "biblStruct": "",
#~ # "biblStruct/analytic": "",
#~ "biblStruct/analytic/title": "title[@level='a']",
#~ "biblStruct/analytic/title/hi": "",
#~ "biblStruct/analytic/title/hi/hi": "",
#~ "biblStruct/analytic/title/subtitle": "",
#~ "biblStruct/analytic/title/title": "",
#~ "biblStruct/analytic/title/title/hi": "",
#~ "biblStruct/analytic/translated-title": "",
#~ "biblStruct/analytic/translated-title/title": "",
#~ "biblStruct/idno": "idno",
#~ 
#~ 
#~ # "biblStruct/monogr": "",
#~ "biblStruct/monogr/imprint": "",
#~ "biblStruct/monogr/imprint/biblScope": "",
#~ "biblStruct/monogr/imprint/date": "",
#~ "biblStruct/monogr/imprint/publisher": "",
#~ "biblStruct/monogr/imprint/pubPlace": "",
#~ "biblStruct/monogr/meeting": "",
#~ "biblStruct/monogr/title": "",
#~ "biblStruct/monogr/title/hi": "",
#~ "biblStruct/note": "",
#~ "biblStruct/note/p": "",
#~ "biblStruct/note/p/hi": "",
#~ 
#~ "biblStruct/analytic/author": "",
#~ "biblStruct/analytic/author/forename": "",
#~ "biblStruct/analytic/author/persName": "",
#~ "biblStruct/analytic/author/persName/forename": "",
#~ "biblStruct/analytic/author/persName/genName": "",
#~ "biblStruct/analytic/author/persName/surname": "",
#~ "biblStruct/analytic/author/suffix": "",
#~ "biblStruct/analytic/author/surname": "",
#~ "biblStruct/analytic/editor": "",
#~ "biblStruct/analytic/editor/persName": "",
#~ "biblStruct/analytic/editor/persName/forename": "",
#~ "biblStruct/analytic/editor/persName/genName": "",
#~ "biblStruct/analytic/editor/persName/surname": "",
#~ 
#~ "biblStruct/monogr/author": "",
#~ "biblStruct/monogr/author/persName": "",
#~ "biblStruct/monogr/author/persName/forename": "",
#~ "biblStruct/monogr/author/persName/genName": "",
#~ "biblStruct/monogr/author/persName/surname": "",
#~ "biblStruct/monogr/editor": "",
#~ "biblStruct/monogr/editor/persName": "",
#~ "biblStruct/monogr/editor/persName/forename": "",
#~ "biblStruct/monogr/editor/persName/surname: ""
#~ }
