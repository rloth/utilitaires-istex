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


Entrée:
PDF + <biblStruct>

Sortie:
<bibl> <author>Milgrom, P., &amp; Roberts, J.</author>   (<date>1991</date>).   <title level="a">Adaptive and sophisticated learning in normal form games</title>.   <title level="j">Games and Economic Behavior</title>,  <biblScope type="vol">3</biblScope>,   <biblScope type="pp">82-100</biblScope>. </bibl>

NB: les fonctions et toute la séquence main sauf la fin peuvent convenir
    pour tout travail de type reporter balises dans/sur du non-structuré
"""
__copyright__   = "(c) 2014-15 - INIST-CNRS (projet ISTEX)"
__author__      = "R. Loth"
__status__      = "Development"
__version__     = "1.0"

# TODO strip_tags pour tags trop fins groupés (authors et pp)

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
from itertools import permutations

# --------------------------------------------------------
# Global vars
biblStruct_to_bibl = {'monogr/title[@level="j"]': '<title level="j">',
					  'monogr/title[@level="m"]': '<title level="m">',
					  'analytic/title[@level="a"]': '<title level="a">',
					  'series/title[@level="s"]': '<title level="s">',
					  'analytic/title/hi': '<UN>',
					  'analytic/title/title/hi': '<UN>',
					  'monogr/meeting': '<title level="m">',
					  'monogr/imprint/meeting': '<title level="m">',
					  'monogr/imprint/date': '<date>',
					  'monogr/imprint/date/@when': '<date>',
					  'monogr/author/persName/surname': '<author>',
					  'monogr/author/persName/forename': '<author>',
					  'analytic/author/persName/surname': '<author>',
					  'analytic/author/persName/forename': '<author>',
					  'analytic/author/forename': '<author>',
					  'analytic/author/surname': '<author>',
					  'analytic/author': '<author>',
					  'monogr/author': '<author>',
					  'analytic/author/orgName': '<author>',
					  'monogr/author/orgName': '<author>',
					  'monogr/respStmt/name': '<author>',
					  'analytic/respStmt/name': '<author>',
					  #~ 'monogr/imprint/biblScope[@unit="pp"]': '<biblScope type="pp">',
					  # pour fusion 2 tags avec balise fermante unique
					  'monogr/imprint/biblScope[@unit="pp"]': '<biblScopp>',
					  'monogr/imprint/biblScope[@unit="vol"]': '<biblScope type="vol">',
					  'monogr/imprint/pubPlace': '<pubPlace>',
					  'monogr/meeting/placeName': '<pubPlace>',
					  'monogr/imprint/publisher': '<publisher>',
					  'monogr/imprint/biblScope[@unit="issue"]': '<biblScope type="issue">',
					  'monogr/editor/persName/surname': '<editor>',
					  'monogr/editor/persName/forename': '<editor>',
					  'monogr/editor': '<editor>',
					  'series/biblScope[@unit="vol"]': '<biblScope type="vol">',
					  'note': '<note>',
					  'monogr/idno': '<idno>',
					  'analytic/idno': '<editor>',
					  'note/ref': '<ptr type="web">',
					  'ref': '<ptr type="web">',
					  'monogr/imprint/biblScope[@unit="part"]': '<biblScope type="chapter">',
					  'monogr/imprint/biblScope[@unit="chap"]': '<biblScope type="chapter">'
					  # if bS has note which contains « thesis », publisher is a university
						# 'monogr/imprint/publisher': 'orgName',
					  }
# --------------------------------------------------------

class XTokinfo:
	"""Groups infos about a str token found in the source XML"""
	def __init__(self, s="", p="", t="", re=None):
		# token
		self.xmlstr = s
		# xpath of src element in <biblStruct>
		self.relpath = p
		# flat xml elt in <bibl>
		self.tagout = t
		# regexp
		self.re = re
	
	def make_pre_regexp(self):
		"""Just the raw regexp string without capture"""
		subtokens = re_tous.findall(self.xmlstr)
		esctokens = [t for t in map(re.escape,subtokens)]
		my_re_str = "[\W£]*".join(r'%s' % u for u in esctokens)
		# print ("re_str : /%s/" % my_re_str)
		return my_re_str
	
	def make_regexp(self, prepared_re_str = None):
		"""The precompiled regexp with capture around"""
		# A1) récup d'une chaîne échappée
		if prepared_re_str is None:
			re_str = self.make_pre_regexp()
		# A2) ou préalablement construite
		else:
			re_str = prepared_re_str
		
		# B) Décision du format des limites gauche et droite pour les \b
		# test si commence par une ponctuation échappée
		if re.match('\\\\*\W',re_str):
			prefix = "("
		else:
			prefix = "\\b("
		
		# idem mais plus facile à la fin
		if re.search('\W$', re_str):
			postfix = ")"
		else:
			postfix = ")\\b"
		
		# C) construction de l'expression régulière
		my_regexp = prefix + re_str + postfix
		return re.compile(my_regexp)
	
	
	
	
	def __str__(self):
		return "%s : '%s' : %s" % (self.relpath, self.xmlstr, self.tagout)
		# return "'%s' : %s" % (self.xmlstr, self.tagout)
	
	def __repr__(self):
		return "<%s>" % self.__str__()
# --------------------------------------------------------


def strip_inner_tags(match):
	"""
	Takes a re 'match object' and removes inner XML tags
	"""
	capture = match.group(0)
	top_mid_bot=re.match(r"^(<[^>]+>)(.*)(<[^>]+>)$",capture)
	if (top_mid_bot is None):
		print("CLEAN_TAG_ERR: capture doesn't start and end with xmltags", file=sys.stderr)
		return(capture)
	else:
		tmb3 = top_mid_bot.groups()
		ltag  = tmb3[0]
		inner = tmb3[1]
		rtag  = tmb3[2]
		
		# strip
		inner = re.sub(r"<[^>]*>","",inner)
		
		# ok
		return (ltag+inner+rtag)



def biblStruct_relpath_to_train_markup(relpath, context=None):
	"""Translate a biblStruct path to a flat bibl one"""
	return biblStruct_to_bibl[relpath]

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

def link_txt_bibs_with_xml(pdfbibzone, xmlbibnodes, debug=0):
	"""Trouver quelle biblStruct correspond le mieux à ch. ligne dans zone ?
	   (~ reference-segmenter)
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
					print("match essai frag pdf du i=%i: '%s'" %(i , re.escape(ptok)), file=sys.stderr)
				
				reptok = re.compile(r"\b%s\b" % re.escape(ptok))
				
				for xtext in xbib.itertext():
					if debug >= 4:
						print("\tsur frag xml du j=%i: %s" % (j, xtext), file=sys.stderr)
					
					# MATCH !
					if reptok.search(xtext):
						if debug >= 4:
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
				if debug >= 2:
					print( "l.%i %-90s: NONE tout à 0" % (i, pdfbibzone[i]), file=sys.stderr)
			
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
					print( "l.%i %-90s: WINs suite XML %s %s (max=%s) (repêchage parmi %s ex aequo)" % (
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
					print("l.%i %-90s: NONE exaequo bibs %s (maxs=%i)"  % (
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
					if debug >= 2:
						print("l.%i %-90s: WEAK (max=%i) (x vide? ou cette ligne p vide ?)" % (i, pdfbibzone[i], the_max_val), file=sys.stderr)
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
						print( "l.%i %-90s: WIN1 entrée XML %s %s (max=%i)" % (
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
					if debug >= 2:
						ma_bS = xbibs[argmax_j]
						infostr = glance_xbib(ma_bS, longer=True)
						print( "l.%i %-90s: WINs suite XML %s %s (max=%i vs d=%f) " % (
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
						print("l.%i %-90s: WEAK (max=%i vs d=%f)" % (
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
	   (signale les séquences en désordre pour diagnostics)
	"""
	# seq <- champions sans duplicats
	seq = []
	checkset = set()
	for w in array_of_xidx:
		# on enlève les doublons
		if w is None or w in checkset:
			continue
		else:
			seq.append(w)
			checkset.add(w)
	
	# diagnostic consécutivité
	consec = True
	lseq = len(seq)
	for a in range(0,lseq):
		if seq[a] != a:
			# force est de le constater
			consec = False
			break
	print("SEQ:intrus seq[%i]='%i'" % (a,seq[a]),file=sys.stderr)
	
	return consec

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
		if debug >= 2:
			print("-"*20+"\n"+"line n. "+str(i)+" : "+tline, file=sys.stderr)
			print("found %i known text fragments from XML content" %  tl_match_occs[i], file=sys.stderr)
			print("found %i typical bibl formats from helper toks" % pdc_match_occs[i] + "\n"+"-"*20, file=sys.stderr)
	
	# sum of 2 arrays
	all_occs = [(tl_match_occs[i] + pdc_match_occs[i]) for i in range(n_lines)]
	
	# log: show arrays
	if debug >= 3:
		print("tl_match_occs\n",tl_match_occs, file=sys.stderr)
		print("pdc_match_occs\n",pdc_match_occs, file=sys.stderr)
	if debug >= 2:
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
			
			if debug >= 2:
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
				
				# TODO £ : max normal = last max => simplifier 15 lignes:
				
				# judge last max 
				# (if window span is a little over the real 
				#  length of the bib zone in the pdf
				#  then *last* max should be right answer)
				if summs_by_chunk_from[i] == max_chunk:
					i_last_max_chunk = i
				if summs_by_chunk_from[i] > max_chunk:
					max_chunk = summs_by_chunk_from[i]
					i_last_max_chunk = i
				
				if debug >= 4:
					# affiche chaque step
					print("line", i,
					  "this sum", summs_by_chunk_from[i],
					  "last max sum", max_chunk,
					  "idx of last max", i_last_max_chunk, file=sys.stderr)
			
			if debug >= 3:
				print("windowed sums:", summs_by_chunk_from, file=sys.stderr)
			
			# Décision début
			# --------------
			
			# début: je suis sur que c'est lui !
			debut = i_last_max_chunk
		
		if debug >= 2:
			print("max_chunk:", max_chunk, "\nfrom i:", debut, file=sys.stderr)
		
	# LA FIN
	# ======
	
	# Décision avec petit lookahead
	# ------------------------------
	# on a encore besoin d'une fenêtre
	# mais plus courte (~ 10 lignes)
	# pour trouver la descente
	shorter_span = min(int(len(xmlbibnodes)/2), 10)
	
	if debug >= 2:
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
	
	if debug >= 2:
		print("found probable end of zone at %s", fin, file=sys.stderr)
	
	# log résultat
	print ("deb: ligne %s (\"%s\")\nfin: ligne %s (\"%s\")"
		   %(
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
	the_year  = None
	the_id    = None
	
	# id
	id_elt = bS.xpath("@xml:id")
	if len(id_elt):
		the_id = id_elt[0]
		
	# date
	date_elts = bS.xpath(".//tei:imprint/tei:date", namespaces=NSMAP)
	if len(date_elts) == 1:
		# 2 manières de noter la date: attribut when ou contenu balise
		# si attribut @when
		if "when" in date_elts[0].keys():
			the_year = date_elts[0].get("when")[0:4]
		# sinon contenu
		else:
			the_year = date_elts[0].text[0:4]
	# sinon la date reste à None
	elif len(date_elts) > 1:
		print ("plusieurs dates", file=sys.stderr)
	
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
	my_desc = "("+main_author[:min(5,len(main_author))]+"-"+str(the_year)+")" 
	
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
	       and ( # tout sauf les mots très courts sans majuscules (with, even..)
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

	parser.add_argument('-t','--txtin',
		metavar='path/to/txtfile',
		help='path to a txt flow of the same text (or segment thereof), for attempted citation regexp match',
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
	
	
	# variable bool (?globale) si la segmentation des références parmi
	# les lignes aura retrouvé une séquence croissante
	CONSECUTIF = False
	
	args = parser.parse_args(sys.argv[1:])
	
	# défault pdfin
	if args.pdfin == None and args.txtin == None :
		temp = re.sub(r'tei.xml', r'pdf', args.xmlin)
		args.pdfin = re.sub(r'xml', r'pdf', temp)
		print("PDFIN?: essai de %s" % args.pdfin, file=sys.stderr)
	
	
	#    INPUT XML
	# ================
	print("LECTURE XML", file=sys.stderr)
	
	# TODO ==> on signale au passage les colonnes vides (xbibs vides en amont)
	
	parser = etree.XMLParser(remove_blank_text=True)
	# parse parse
	try:
		dom = etree.parse(args.xmlin, parser)
	
	except OSError as e:
		print(re.sub("': failed to load external entity.*", "' (fichier absent ?)", str(e)), file=sys.stderr)
		sys.exit()
	
	
	NSMAP = {'tei': "http://www.tei-c.org/ns/1.0"}
	# query query
	xbibs = dom.findall(
				"tei:text/tei:back//tei:listBibl/tei:biblStruct",
				namespaces=NSMAP
				)
	xbibs_plus = dom.xpath(
				"tei:text/tei:back//tei:listBibl/*[local-name()='bibl' or local-name()='biblStruct']",
				 namespaces=NSMAP
				)
	
	# pour logs
	# ---------
	nxb = len(xbibs)
	nxbof = len(xbibs_plus) - nxb
	
	# si présence de <bibl>
	if (nxbof > 0):
		print("WARN: %i entrées dont  %i <bibl> (non traitées)" % (nxb+nxbof, nxbof), file=sys.stderr)
	
	# exception si aucune <biblStruct>
	if (nxb == 0):
		print("ERR: aucune xbib <biblStruct> dans ce xml natif !", file=sys.stderr)
		sys.exit()
	
	
	# préalable: passage en revue des XML ~> diagnostics (vars globales)
	# ----------
	
	# pour corresp. indice j <=> n° XML:ID (si trouvé, souvent == label)
	XMLIDMAP = [None for j in range(nxb)]
	
	# si les xml:id finissent par 1,2,3... 
	# (TODO: autres diagnostics : absents, non numériques, consécutifs avec début != 1 etc)
	FLAG_STD_MAP = False
	
	# tous les contenus texte des elts xml, en vrac
	XMLTEXTS = []
	
	# remplissage des deux: XMLTEXTS et XMLIDMAP
	for j, xbib in enumerate(xbibs):
		
		thisbib_texts=[]
		for eltstr in xbib.itertext():
			thisbib_texts.append(eltstr)
		
		# TODO : vérifier si intéressant de les préserver séparément (liste de listes)
		XMLTEXTS += thisbib_texts
		
		thisbib_id = None
		xbib_ids = xbib.xpath("@xml:id") ;
		if len(xbib_ids):
			thisbib_id = xbib.xpath("@xml:id").pop()
			# au passage diagnostic consécutivité
			# a-recup numérotation en fin d'ID 
			# ex: 1,2 ou 3 dans DDP278C1 DDP278C2 DDP278C3
			nums = re.findall(r"[0-9]+", thisbib_id)
			
			# b-verif
			if (len(nums)) and (int(nums[-1]) == j+1) and (j == 0 or FLAG_STD_MAP): 
				FLAG_STD_MAP = True
		
		# log si haut debug
		if args.debug >= 2:
			print(("-"*50)+ 
		           "\nlecture des contenus texte xmlbib %i (@xml:id='%s')" 
		              % (j, thisbib_id), file=sys.stderr)
			print(thisbib_texts, file=sys.stderr)
		
		# stockage
		XMLIDMAP[j] = thisbib_id
		
	if args.debug >= 1:
		print(XMLIDMAP, file=sys.stderr)
		if FLAG_STD_MAP:
			print("GOOD: numérotation ID <> LABEL traditionnelle", file=sys.stderr)
		else:
			# todo préciser le type de lacune observée (pas du tout de labels, ID avec plusieurs ints, ou gap dans la seq)
			print("WARN: la numérotation XML:ID ne contient pas un label unique incrémental", file=sys.stderr)
	
	
	if args.txtin:
		#  INPUT TXT à comparer
		# ======================
		print("---\nLECTURE FLUX TXT ISSU DE PDF", file=sys.stderr)
		
		try:
			pdflines = [line.rstrip('\n') for line in open(args.txtin)]
		except FileNotFoundError as e:
			print("Echec ouverture du flux textin '%s': %s\n" % (e.filename,e.strerror), file=sys.stderr)
			sys.exit(1)
	else:
		#  INPUT PDF à comparer
		# ======================
		print("---\nLECTURE PDF", file=sys.stderr)

		# appel pdftotext via OS
		try:
			pdftxt = check_output(['pdftotext', args.pdfin, '-']).decode("utf-8")
		
		except CalledProcessError as e:
			print("Echec pdftotxt: cmdcall: '%s'\n  ==> FAILED (file not found?)" % e.cmd, file=sys.stderr)
			# print(e.output, file=sys.stderr)
			sys.exit(1)
		# got our pdf text!
		pdflines = [line for line in pdftxt.split("\n")]
	
	print ("N lignes: %i" % len(pdflines), file=sys.stderr)
	
	
	# TODO éventuellement quand pdf entier ?
	# filtrer deux ou 3 lignes autour du FORM FEED ^L 
	# pour essayer de virer les hauts et bas de page
	
	
	#  Recherche zone biblio
	# ========================
	print("---\nFIND PDF BIBS", file=sys.stderr)
	
	# La zone biblio dans le texte  pdf est un segment marqué par 2 bornes
	#       (par ex: d=60 et f=61 on aura |2| lignes intéressantes)
	# ----------------------------------------------------------------------
	(debut_zone, fin_zone) = find_bib_zone(xbibs, pdflines, debug=args.debug)
	
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
	
	# get sequence over pdf content lines ids filled with best matching xml ids
	winners = link_txt_bibs_with_xml(pdflines[debut_zone:fin_zone+1], xbibs, debug=args.debug)
	
	# affiche résultat
	print("Les champions: %s" % winners, file=sys.stderr)
	# exemple liste winners
	# ----------------------------
	# winners =[None, 0 , 0 , 1 , 1 , 2, 2, 2, 3, 3, 3, 4, 4, None, None, None, None, 4, 5, 5, 6, 6, 7,   7                 ]
	#      i' =[  0 | 1 | 2 | 3 | 4 | ...     ...     ...     ...     ...     ...     ...     ...     | fin_zone-debut_zone ]
	
	# NB: "None" values are either:
	#             - failed matches
	#             - or gaps in the list,
	#             - or lines before 1st ref
	#             - or lines after last ref
	
	# vérification si on ne doit garder que les documents qui matchent bien
	# (par exemple quand on génère un corpus d'entraînement)
	if check_align_seq(winners):
		CONSECUTIF = True
	
	#---------------------------------------------------------------------------------
	# then we group content from pdf (each txtline i') by its associated xml id j_win
	# ---------------------------------------------------------------------------------
	# résultat à remplir
	xlinked_real_lines = [None for j in range(nxb)]
	
	for i_prime, j_win in enumerate(winners):
		if j_win is None:
			# we *ignore* None values 
			# => if we wanted them we need to fix them earlier
			pass
		# === normal case ===
		else:
			# nouveau morceau
			if xlinked_real_lines[j_win] is None:
				xlinked_real_lines[j_win] = pdflines[debut_zone+i_prime]
			# morceaux de suite
			else:
				# on recolle les lignes successives d'une même bib
				# SEPARATEUR SAUT DE LIGNE 
				#  => format sortie reference-segmenter: sera transformé en '<lb/>'
				#  => format sortie citations: ignoré car matche /\W+/
				xlinked_real_lines[j_win] += "£"+pdflines[debut_zone+i_prime]

	# log détaillé de cette étape
	if args.debug >= 3:
		# linked results
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
	
	# pour la tokenisation des lignes via re.findall
	re_tous = re.compile(r'\w+|[^\w\s]')
	re_contenus = re.compile(r'\w+')
	re_ponctuas = re.compile(r'[^\w\s]')
	
	# tempo £stockage infos par xbib
	xbibtoks = [None for j in range(nxb)]
	
	for j, group_of_real_lines in enumerate(xlinked_real_lines):
		# pour vérifs
		my_doubt = False
		
		if group_of_real_lines is None:
			if args.debug > 0:
				print("Didn't find the lines for XML bib %i" % j)
			continue
		
		# préserve la ponctuation
		# £non utilisé mais utile à afficher en debug
		veritable_tokens_from_pdf = re_tous.findall(group_of_real_lines)
		# tokenisation plus exhaustive qu'auparavant sur ce sous-ensemble "validé"
		# remarque : on n'utilise pas de split pour préserver la ponctuation
		
		# on prépare les infos XML qu'on s'attend à trouver
		# ------------------------
		this_xbib = xbibs[j]
		
		# log
		# if args.debug >= 1:
		print("\n"+"="*50, file=sys.stderr)
		# rappel entrée 1 PDF
		print("XML entry:", glance_xbib(xbibs[j]) + "\ncontenus texte xmlbib %i" % j, file=sys.stderr)
		print(etree.tostring(this_xbib, pretty_print=True).decode("ascii") + ("-"*50), file=sys.stderr)
		print("PDF lines: \"%s\"" % group_of_real_lines, file=sys.stderr)
		# rappel entrée 2 XML
		
		# on utilise iter() et pas itertext() pour avoir les chemins rel
		# + on le fait sous la forme iter(tag=elt) pour avoir les éléments
		#   et pas les commentaires
		subelts = [xelt_s for xelt_s in this_xbib.iter(tag=etree.Element)]
		
		# cette boucle part des éléments xml (contenus attendus) pour
		# créer une liste de tokens avec à réintégrer à l'autre flux:
		#   - les contenus => point d'ancrage qui dira *où* réintégrer
		#   - leur balise  => décrit *ce que* l'on va réintégrer comme infos
		
		# difficultés à voir:
		#  - il peut y avoir plus de tokens que d'éléments
		#    par ex: <biblScope unit="page" from="20" to="31" />
		#    => donne 2 tokens "20" et "31"
		#  - il faut conserver une info univoque sur la nature de l'élt
		#    => on prend un xpath simple en ajoutant les attributs clé
		#  - cette info univoque sera à réintégrer en markup sur l'autre
		#    flux (en gros une traduction tei:biblStruct => tei:bibl)
		
		
		# £ stats absences ?
		# empty_elts_that_should_be_there = 0
		
		toklist = []
		for xelt in subelts:
			
			base_path = simple_path(xelt, relative_to = localname_of_tag(this_xbib.tag))
			
			loc_name = localname_of_tag(xelt.tag)
			
			if args.debug >= 2:
				print("***", file=sys.stderr)
				print("base_path   :", base_path, file=sys.stderr)
				print("text content:", xelt.text, file=sys.stderr)
			
			
			# PLUSIEURS CAS PARTICULIERS spécifiques aux biblios
			# -------------------------------------------------
			# (autrement simplement : tok.xmlstr = xelt.text 
			#                      et tok.relpath = base_path)
			# -------------------------------------------------
			
			# cas particulier *date*
			if loc_name == 'date':
				# soit 1 token normal
				if xelt.text:
					tok = XTokinfo(s=xelt.text, p=base_path)
					toklist.append(tok)
				# soit token dans la valeur d'attribut
				else:
					tok = XTokinfo(s=xelt.get('when'), p="%s/@%s" % (base_path, 'when'))
					toklist.append(tok)

			# cas particuliers *pagination*: 
			elif loc_name == 'biblScope' and xelt.get('unit') in ['page','pp']:
				# soit un biblScope normal
				if xelt.text:
					tok = XTokinfo(s=xelt.text, p='%s[@unit="pp"]' % base_path)
					toklist.append(tok)
				# soit 2 tokens dans les attributs
				else:
					tok1 = XTokinfo(s=xelt.get('from'), p='%s[@unit="pp"]/@from' % base_path)
					tok2 = XTokinfo(s=xelt.get('to'),   p='%s[@unit="pp"]/@to' % base_path)
					toklist.append(tok1, tok2)

			# tous les autres biblScope pour préserver leur @unit
			elif loc_name == 'biblScope':
				this_unit = xelt.get('unit')
				tok = XTokinfo(s=xelt.text, p='%s[@unit="%s"]' % (base_path, this_unit))
				toklist.append(tok)

			# les title avec leur @level
			# NB : xelt.text is not None devrait aller de soi et pourtant... pub2tei
			elif loc_name == 'title' and xelt.text is not None:
				this_level = xelt.get('level')
				if this_level == None:
					this_level="___"
				tok = XTokinfo(s=xelt.text, p='%s[@level="%s"]' % (base_path, this_level))
				toklist.append(tok)

			# les noms/prénoms à prendre ensemble quand c'est possible...
			# Pour cela on les traite non pas dans les enfants feuilles
			# mais le plus haut possible en analytic|monogr/author
			elif loc_name in ['author','editor']:
				re_strs_to_combine = []
				# print("+" * 50)
				for subtext in xelt.itertext():
					# print(subtext)
					pretok = XTokinfo(s=subtext, p="tempo_names")
					re_strs_to_combine.append(pretok.make_pre_regexp())
				# print("+" * 50,"\n",len(re_strs_to_combine))
				for combi in permutations(re_strs_to_combine):
					combitok = XTokinfo(s="__GR(%s)__" % ",".join(combi), p=base_path)
					combitok.re = combitok.make_regexp(
					  prepared_re_str = "\W*".join(combi)
					)
					# print(combitok.re)
					toklist.append(combitok)

			# du coup on ne retraite pas tous les enfants du précédent
			elif re.search(r'author|editor', base_path):
				# print ("!!!skipping", base_path, xelt.text)
				continue

			# normalement on a déjà traité tous les cas 
			# avec texte vide, attribut intéressant
			# => ne reste que des texte vide inintéressants
			elif xelt.text is None:
				continue

			# === cas normal ===
			else:
				tok = XTokinfo(s=xelt.text, p=base_path)
				toklist.append(tok)
		
		# spécifique biblStruct:
		# correspondances tag d'entrée => le tag de sortie
		for l, tok in enumerate(toklist):
			
			# 1) on génère le markup de sortie sur correspondances relpath
			tok.tagout = biblStruct_relpath_to_train_markup(tok.relpath)
			tok.endout = re.sub(r'^<','</', re.sub(r' .*$','>', tok.tagout))
			
			# debug
			if args.debug >= 1:
				print("XTOK",l,tok, file=sys.stderr)
			
			# sanity check A : the xmlstr we just found
			if tok.xmlstr is None:
				print("ERR: no xmlstr for %s" % tok.relpath, file=sys.stderr)
				my_doubt = True
				continue
			
			# 2) on crée des expressions régulières
			#    (sauf pour les noms/prénoms déjà préparés)
			# "J Appl Phys" ==> r'J(\W+)Appl(\W+)Phys'
			# £ TODO : autoriser un tiret n'importe ou dans les mots des
			#          longs champs !!
			if tok.re is None:
				tok.re = tok.make_regexp()
			
			# 3) on matche
			#  £ TODO procéder par ordre inverse de longueur !!
			n_matchs = len(re.findall(tok.re,group_of_real_lines))
			
			# sanity check B : "there can be only one" !
			if n_matchs > 1:
				print("ERR: '%s' (%s) matches too many times" % (tok.xmlstr, tok.relpath), file=sys.stderr)
				my_doubt = True
				continue
			
			# quand tok.xmlstr == "__group__" au moins un des 2 ne matche pas
			elif n_matchs < 1:
				print("ERR: '%s' (%s) didn't match using regexp /%s/" % (tok.xmlstr, tok.relpath, tok.re), file=sys.stderr)
				my_doubt = True
				continue
			
			# 4) si on a un unique match => on le traite
			else:
				# match direct naïf (TODO jonction nom-prénom + fusions groupes)
				pseudo_out = tok.tagout + r"\1" + tok.endout
				group_of_real_lines = re.sub(tok.re,pseudo_out,group_of_real_lines)
				print("OK: '%s' (%s) matched using regexp /%s/" % (tok.xmlstr, tok.relpath, tok.re), file=sys.stderr)

		print(toklist)
		
		# SEPARATEUR SAUT DE LIGNE => format sortie reference-segmenter
		new_lines = re.sub("£","<lb/>",group_of_real_lines)
		
		if my_doubt:
			print("PASS: report incertain sur la refbib '%s'" % group_of_real_lines[0:10], file=sys.stderr)
			
			# continue ?
			new_lines = "__DOUBT__:"+new_lines
		
		print("new bibl lines:", file=sys.stderr)
		
		# dernier correctif: groupement de tags pour le modèle citations
		new_lines = re.sub(r'(<author>.*</author>)',strip_inner_tags, new_lines)
		new_lines = re.sub(r'</biblScopp>', r'</biblScope>',
				  re.sub(r'<biblScopp>', r'<biblScope type="pp">',
				 re.sub(r'(<biblScopp>.*</biblScopp>)',strip_inner_tags,
				new_lines)))
		
		# OUTPUT FINAL
		print("<bibl>"+new_lines+"</bibl>")
		
# EXEMPLES DE SORTIE
# <bibl> <author>Whittaker, J.</author>   (<date>1991</date>).   <title level="a">Graphical Models in Applied Multivariate Statistics</title>.   <publisher>Chichester: Wiley</publisher>. </bibl>

# <bibl> <author>Surajit Chaudhuri and Moshe Vardi</author>.  <title level="a">On the equivalence of recursive and nonrecursive data-log programs</title>.   In <title level="m">The Proceedings of the PODS-92</title>,   pages <biblScope type="pp">55-66</biblScope>,   <date>1992</date>. </bibl>



# £TODO distinguer 2 sorties pour les modèles:
#          - reference-segmenter
#          - citations

# ---------------------------------------------------------------------------------------------------------
# C | MODELE CRF          | TRAINING EXE                        | TRAINING EXT
# --+---------------------+-------------------------------------+------------------------------------------
# 1 | fulltext            | createTrainingFulltext              | .training.fulltext.tei.xml
# 2 | segmentation        | createTrainingSegmentation          | .training.segmentation.tei.xml
# 3 | reference-segmenter | createTrainingReferenceSegmentation | .referenceSegmenter.training.tei.xml
# 4 | citation            | createTrainingFulltext              | .training.references.tei.xml
# 5 | name/citation       | createTrainingFulltext              | .training.citations.authors.tei.xml
# ---------------------------------------------------------------------------------------------------------


# ---------------------------------------------------------------------------------------------------------
# C | MODELE CRF          | COMMANDE ragreage.py | FONCTION ragreage.py CORRESPONDANTE
# --+---------------------+----------------------+---------------------------------------------------------
# 1 | fulltext            |                      | 
# 2 | segmentation        |                      | find_bib_zone
# 3 | reference-segmenter |                      | link_txt_bibs_with_xml()
# 4 | citation            | (par défaut)         | TODO ignorer <lb> + 2 post-traitements : auteurs et pp
# 5 | name/citation       |                      | TODO ignorer tout sauf auteurs
# ---------------------------------------------------------------------------------------------------------
