#! /usr/bin/python3
"""
TODOS préalables : feuille RSC (et Nat à part)


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
      (1) find_bibzone()                => sortie segmentation 
      (2) link_txt_bibs_with_xml()    ===> sortie reference-segmenter
      (3) align xml fields on pdftxt
             ||
           report struct sur non-struct
             ||
            <bibl>
   annotation xml simplifiées* bibl =====> TODO 
    préservant toute l'info markup
     sur chaîne réelle -txtin ou


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

# procédures: find_bib_zone, link_txt_bibs_with_xml et helpers divers
import rag_procedures

# fonctions
import re
from itertools import permutations

# --------------------------------------------------------
# --------------------------------------------------------
# global vars

# pour la tokenisation des lignes via re.findall
re_TOUS = re.compile(r'\w+|[^\w\s]')
re_CONTENUS = re.compile(r'\w+')
re_PONCT = re.compile(r'[^\w\s]')


# each diagnostic whether the xml:ids end with 1,2,3... 
# (TODO: autres diagnostics :
#     -> absents, non numériques, consécutifs avec début != 1 etc)
FLAG_STD_MAP = False

# said endings 1,2,3 (if present) for label retrieval
# utilise l'attribut "n" quand il est présent
# (dans la feuille elsevier il reprenait value-of sb:label)
LABELS = None

# --------------------------------------------------------
# --------------------------------------------------------
# fonctions

def prepare_arg_parser():
	"""Preparation argument parser de l'input pour main"""
	parser = argparse.ArgumentParser(
		description="""Ajout des ponctuations réelles dans un xml de 
		               refbibs (NB lent: ~ 2 doc/s sur 1 thread)""",
		usage="""ragreage.py 
		          -x ech/tei.xml/oup_Human_Molecular_Genetics_ddp278.xml
		          -p ech/pdf/oup_Human_Molecular_Genetics_ddp278.pdf""",
		epilog="- © 2014-15 Inist-CNRS (ISTEX) romain.loth at inist.fr -"
		)
	
	
	parser.add_argument('-x','--xmlin',
		metavar='path/to/xmlfile',
		help="""
		path to a TEI.xml with citations in <biblStruct> xml format 
		(perhaps to be created from native XML by a call like 
		`saxonb-xslt -xsl:tools/Pub2TEI/Stylesheets/Publishers.xsl
		-s:exemples_RONI_1513/rsc_1992_C3_C39920001646.xml`)'""",
		type=str,
		required=True,
		action='store')
		
	
	
	parser.add_argument('-p','--pdfin',
		metavar='path/to/pdffile',
		help="""path to a pdf file of the same text, for attempted
		        pdftottext and citation regexp match""",
		type=str,
		default=None ,  # cf juste en dessous
		action='store')
	
	parser.add_argument('-t','--txtin',
		metavar='path/to/txtfile',
		help="""pdfin can be replaced by a path to a txt flow.
		This input text must be very close to the xml content
		(or segment thereof, in accordance with a chosen -m type)""",
		type=str,
		default=None ,  # cf juste en dessous
		action='store')
		
	
	
	parser.add_argument('-m','--model-type',
		metavar='name-of-model',
		help="""format output as a valid tei's 'listBibl' (default)
		        or tailored to a Grobid crf model pseudotei input among:
		        {'segmentation', 'reference-segmenter', 'citations'}""",
		type=str,
		default='listBibl' ,
		action='store')
	
	
	parser.add_argument('-d','--debug',
		metavar=1,
		type=int,
		help='logging level for debug info in [0-3]',
		default=0,
		action='store')
	
		
	parser.add_argument('-r', '--remainder',
		dest='mask',
		help='show mask after matches instead of normal output',
		action='store_true')
	
	return parser



# --------------------------------------------------------
# -B- fonctions xpath et nettoyage value-of

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
	"""
	Strip etree tag from namespace à la xsl:local-name()
	"""
	return re.sub(r"{[^}]+}","",etxmltag)

def strip_inner_tags(match):
	"""
	Takes a re 'match object' and removes inner XML tags à la xsl:value-of()
	
	Ex: "<au>Merry</au> and <au>Pippin</au>"
	    => <au>Merry and Pippin</au>
	"""
	capture = match.group(0)
	top_mid_bot=re.match(r"^(<[^>]+>)(.*)(<[^>]+>)$",capture)
	if (top_mid_bot is None):
		print("CLEAN_TAG_ERR: capture doesn't start and end with xmltags"
		      , file=sys.stderr)
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



def check_align_seq(array_of_xidx):
	"""
	Diagnostics sur les champions par ligne issus des scores_pl_xb ?
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
			print("SEQ:intrus seq[%i]='%i'" % (a,seq[a]),
			         file=sys.stderr)
			break
	# bool
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
# fonctions procédures citations (prepare field tokens => match in txt)

def biblStruct_elts_to_match_tokens(xml_elements, debug=0):
	""" Prepares tokens relevant to each field
	
	Convertit une branche XML sous la forme de tous ses sous-éléments
	   en une liste de tokens matchables (instances de XTokinfo)
	   (avec 2 tags src=xip,tgt=xop + 1 ou psieurs contenus=str + 1 re)
	   dont certains spécifiquement groupés pour le modèle crf citations
	
	Difficulté à voir: il peut y avoir plus de tokens que d'éléments
	   par ex: <biblScope unit="page" from="20" to="31" />
	   => donne 2 tokens "20" et "31"
	
	Les tags et la regexp du token sont stockés dans son instance 
	   tag src => xpath simple en y ajoutant les attributs clé
	   tag tgt => tag src traduit via table tei:biblStruct => tei:bibl
	   regexp => match défini dans classe XToken
	"""
	
	toklist = []
	for xelt in xml_elements:
		base_path = simple_path(xelt, relative_to = "biblStruct")
		
		loc_name = localname_of_tag(xelt.tag)
		
		if debug >= 2:
			print("***", file=sys.stderr)
			print("base_path   :", base_path, file=sys.stderr)
			print("text content:", xelt.text, file=sys.stderr)
		
		
		# PLUSIEURS CAS PARTICULIERS spécifiques aux biblios
		# -------------------------------------------------------
		# (autrement simplement :  tok.xtexts      = xelt.text 
		#                       et tok.xml_in_path = base_path)
		# -------------------------------------------------------
		
		# cas particulier *date*
		if loc_name == 'date':
			# soit 1 token normal
			if xelt.text:
				tok = XTokinfo(s=xelt.text, xip=base_path)
				toklist.append(tok)
			# soit token dans la valeur d'attribut
			else:
				tok = XTokinfo( s=xelt.get('when'),
				              xip="%s/@%s" % (base_path, 'when') )
				toklist.append(tok)

		# cas particuliers *pagination*: 
		elif loc_name == 'biblScope' and xelt.get('unit') in ['page','pp']:
			# soit un biblScope normal
			if xelt.text:
				tok = XTokinfo( s=xelt.text,
				              xip='%s[@unit="pp"]' % base_path )
				toklist.append(tok)
			# soit 2 tokens dans les attributs
			else:
				tok1 = XTokinfo( s=xelt.get('from'),
				               xip='%s[@unit="pp"]/@from' % base_path)
				tok2 = XTokinfo( s=xelt.get('to'),
				               xip='%s[@unit="pp"]/@to' % base_path )
				toklist.append(tok1, tok2)

		# tous les autres biblScope (vol, iss...) pour préserver leur @unit
		elif loc_name == 'biblScope':
			my_unit = xelt.get('unit')
			tok = XTokinfo( s=xelt.text,
			              xip='%s[@unit="%s"]' % (base_path, my_unit) )
			toklist.append(tok)

		# les title avec leur @level
		# NB : xelt.text is not None devrait aller de soi et pourtant... pub2tei
		elif loc_name == 'title' and xelt.text is not None:
			this_level = xelt.get('level')
			if this_level == None:
				this_level="___"
			tok = XTokinfo( s=xelt.text,
			              xip='%s[@level="%s"]' % (base_path, this_level))
			toklist.append(tok)

		# les noms/prénoms à prendre ensemble quand c'est possible...
		#    pour cela on les traite non pas dans les enfants feuilles
		#    mais le + haut possible ici à (analytic|monogr)/(author|editor)   
		elif loc_name in ['author','editor']:
			# du coup l'arg s du token est différent: str[] et pas str
			str_list = [s for s in xelt.itertext()]
			nametok = XTokinfo( s=str_list,   # <----- ici liste
			                  xip=base_path)
			toklist.append(nametok)
		
		# et du coup on ne re-traite pas tous les enfants du précédent
		elif re.search(r'(?:author|editor)/.', base_path):
			#~ print ("!!!skipping", base_path, xelt.text)
			continue

		# normalement on a déjà traité tous les cas 
		# avec texte vide, attribut intéressant
		# => ne reste que des texte vide inintéressants
		elif xelt.text is None:
			continue

		# === cas normal ===
		else:
			tok = XTokinfo(s=xelt.text, xip=base_path)
			toklist.append(tok)
	
	
	# XTokinfo array
	return toklist


def match_citation_fields(raw_lines, subtree=None, label="", debug=0):
	"""Matches field info in raw txt string
	   returns(output_xml_string, success_bool)
	   
	   Minimal: re-annotate only label
	   Normal : re-annotate label and all subelements in subtree this_xbib
	   
	En particulier, report des tags <bibl> sur une refbib"""
	
	
	# vérification des arguments
	if subtree is None and label == "":
		raise ValueError("match_citation_fields()"
		 +" il faut au moins un label ou une branche XML à reporter")
	elif subtree is None:
		just_label = True
	else:
		just_label = False
	
	
	# - log -
	if debug > 0:
		print("\n"+"="*50, file=sys.stderr)
		
		# rappel input XML
		
		
		if subtree is not None:
			xmlentry = rag_procedures.glance_xbib(subtree)
			print("XML entry:", xmlentry
		        + "\ncontenus texte xmlbib %i" % j, file=sys.stderr)
			print(etree.tostring(subtree, pretty_print=True).decode("ascii")
		        + ("-"*50), file=sys.stderr)
		else:
			xmlentry = "__no_xbib__"
			print("XML entry:", xmlentry, file=sys.stderr)
		    
		
		# rappel input raw (pdfin ou txtin)
		print("PDF lines: \"%s\"" % raw_lines, file=sys.stderr)
		print(re_TOUS.findall(raw_lines), file=sys.stderr)
		print("\n"+"-"*50, file=sys.stderr)
	
	
	# on prépare les infos XML qu'on s'attend à trouver
	# ------------------------
	
	# tokenisation
	# - - - - - - - - - - - - - -
	# ajouter label en 1er token
	#~ print ("je cherche %s" % label)
	toklist = [XTokinfo(s=str(label),xip="label")]
	
	# Tous les autres tokens:
	if not just_label:
		# parcours de l'arbre
		
		# on utilise iter() et pas itertext() pour avoir les chemins rel
		# + on le fait sous la forme iter(tag=elt) pour avoir les éléments
		#   et pas les commentaires
		subelts = [xelt_s for xelt_s in subtree.iter(tag=etree.Element)]
		
		# la boucle part des éléments xml (contenus attendus) pour
		# créer une liste de tokens avec à réintégrer à l'autre flux:
		#   - les contenus => point d'ancrage qui dira *où* réintégrer
		#                  => génère une expression régulière à trouver
		#   - leur balise  => décrit *ce que* l'on va réintégrer comme infos
		#                  => obtenue par table corresp selon relpath actuel
		# - - - - - - -
		# methode 1 : appel fonction cas par cas
		toklist += biblStruct_elts_to_match_tokens(subelts, debug=debug)
		
		# - - - - - - -
		# méthode 2 générique
		#~ toklist = [XTokinfo(
					  #~ s=xelt.text,
					  #~ xip=simple_path(
					  #~    xelt, 
					  #~    relative_to = localname_of_tag(subtree.tag)
					  #~    )
					  #~ ) for xelt in subelts if xelt.text not in [None, ""]]
	# - - - - - - - - - - - - - -
	 # print("TOKLIST", toklist)
	
	# on matche les infos XML sur le flux PDFTXT
	# ------------------------------------------
	
	# spécifique biblStruct:
	# correspondances tag d'entrée => le tag de sortie
	for l, tok in enumerate(toklist):
		
		# pour vérifs : todo stat dessus passée en //
		my_doubt = False
		
		# debug
		if debug >= 1:
			print("XTOK",l,tok, file=sys.stderr)
		
		# sanity check A : the xmlstr we just found
		if tok.xtexts is None:
			print("ERR: no xmlstr for %s" % tok.relpath, file=sys.stderr)
			my_doubt = True
			continue
		
	
		# 3) on matche -------------------------------------------
		#  £ TODO procéder par ordre inverse de longueur !!
		# print("RAW: {'%s'}" % raw_lines)
		n_matchs = len(re.findall(tok.re,raw_lines))
		# --------------------------------------------------------
		
		# sanity check B : "there can be only one" !
		if n_matchs > 1:
			if debug >= 2:
				print("ERR: '%s' (%s) matches too many times" %
				         (tok.xtexts, tok.relpath),
				         file=sys.stderr)
			my_doubt = True
			
			
			# ££££ TODO choose one of the matches if len > 2 ?
			continue
		
		# quand tok.xtexts == "__group__" au moins un des 2 ne matche pas
		elif n_matchs < 1:
			if debug >= 2:
				print("ERR: no raw match for XToken '%s' (%s) aka re /%s/" %
				         (tok.xtexts, tok.relpath, tok.re.pattern),
				         file=sys.stderr)
			my_doubt = True
			continue
		
		# 4) si on a un unique match => on le traite --------------
		else:
			# substitution
			if args.mask:
				#~ pseudo_out = "__%s__" % tok.tagout
				pseudo_out = "__"
			else:
				# remplacement normal : tag de sortie
				# TODO: vérifier s'il faut échapper les '<' '>' et '&'
				pseudo_out = tok.tagout + r"\1" + tok.endout
			raw_lines = re.sub(tok.re,pseudo_out,raw_lines)
		# --------------------------------------------------------
	
	# dernier correctif: groupements de tags
	# ------------------
	
	# -a- pages collées pour le modèle citation
	new_lines = re.sub(r'<pp>', r'<biblScope type="pp">',
			  re.sub(r'</pp>', r'</biblScope>',
			 re.sub(r'(<pp>.*</pp>)',strip_inner_tags,
			raw_lines)))
	
	# -b- auteurs groupés
	new_lines = re.sub(r'(<author>.*</author>)',strip_inner_tags, new_lines)
	
	new_lines = "<bibl>"+new_lines+"</bibl>"
	
	
	return(new_lines, not(my_doubt))


# --------------------------------------------------------

# --------------------------------------------------------


class XTokinfo:
	"""Groups infos about a str token found in the source XML"""
	
		
	# MAP (biblStruct => bibl) to choose the final citation's 'out tag'
	STRUCT_TO_BIBL = {
	  # --- label inséré à part ---
	  'label': '<label>',
	  
	  # --- équivalences standard ---
	  'analytic/title[@level="a"]' :            '<title level="a">',
	  'analytic/title/hi' :                 '__rmtag__',  # todo effacer le tag
	  'analytic/title/title/hi' :           '__rmtag__',
	  'analytic/author/persName/surname' :  '<author>',
	  'analytic/author/persName/forename': '<author>',
	  'analytic/author/forename' :          '<author>',
	  'analytic/author/surname' :           '<author>',
	  'analytic/author/orgName' :           '<author>',  # ? orgName en <bibl> ?
	  'analytic/author' :                   '<author>',
	  'analytic/respStmt/name' :            '<author>',
	  'monogr/author/persName/surname' :       '<author>',  # <!-- monogr -->
	  'monogr/author/persName/forename' :        '<author>',
	  'monogr/author/orgName' :                   '<author>',  # ? orgName en <bibl> ?
	  'monogr/author' :                           '<author>',
	  'monogr/respStmt/name' :                    '<author>',
	  'monogr/imprint/meeting' :                  '<title level="m">',
	  'monogr/meeting' :                          '<title level="m">',
	  'monogr/imprint/date' :                     '<date>',
	  'monogr/imprint/date/@when' :               '<date>',
	  'monogr/title[@level="j"]' :                '<title level="j">',
	  'monogr/title[@level="m"]' :                '<title level="m">',
	  
	  'monogr/imprint/biblScope[@unit="vol"]' :   '<biblScope type="vol">',
	  'monogr/imprint/biblScope[@unit="issue"]': '<biblScope type="issue">',
	  'monogr/imprint/biblScope[@unit="part"]' :  '<biblScope type="chapter">',
	  'monogr/imprint/biblScope[@unit="chap"]' :  '<biblScope type="chapter">',
	  'monogr/imprint/publisher' :                '<publisher>',
	  'monogr/imprint/pubPlace' :                 '<pubPlace>',
	  'monogr/meeting/placeName' :                '<pubPlace>',
	  'monogr/editor/persName/surname' :       '<editor>',
	  'monogr/editor/persName/forename' :      '<editor>',
	  'monogr/editor' :                        '<editor>',
	  'series/title[@level="s"]' :          '<title level="s">',
	  'series/biblScope[@unit="vol"]' :     '<biblScope type="vol">',
	  'note' :                              '<note>',
	  'monogr/idno' :                       '<idno>',
	  'analytic/idno' :                     '<editor>',
	  'note/ref' :                          '<ptr type="web">',
	  'ref' :                               '<ptr type="web">',
	  
	  # --- pages ---
	  # pour fusion ulterieure de 2 tags <pp> ensemble
	  'monogr/imprint/biblScope[@unit="pp"]': '<pp>',
	  # sinon normal:
	  # 'monogr/imprint/biblScope[@unit="pp"]': '<biblScope type="pp">',
	  
	  # --- cas particuliers ---
	  # if bS has note which contains « thesis », publisher is a university
	  # 'monogr/imprint/publisher': 'orgName',
	  
	  # -- à vérifier --
	  'monogr/imprint/edition' :                  '<note type="edition">',  
	  }


	# sert pour recombiner des tokens séparés: par ex " " ou ""
	BLANK = " "
	
	
	
	# =================================================
	# initialisation
	def __init__(self, s="", xip=""):
		# 1) Initialisation str <= contenu(s) et xip <= src_path
		# -------------------------------------------------------
		# CONTENUS SELF.XTEXTS
		if type(s) == str:
			# token = 1 str (<= usually text content of the xml elt)
			self.xtexts = s
			self.combimode = False
		
		# token = k strings together in any order
		# initialisation combinée avec une liste str appelé s_list
		# ex: nom + prénom 
		elif type(s) == list:
			self.xtexts = s
			self.combimode = True
			
		else:
			raise TypeError(type(s))
		
		# xpath of src element in <biblStruct>
		# XIP
		self.relpath = xip
		
		# 2) on crée des expressions régulières pour le contenu
		# -------------------------------------------------------
		# SELF.RE
		# "J Appl Phys" ==> r'J(\W+)Appl(\W+)Phys'
		# £ TODO : autoriser un tiret n'importe ou dans les mots des
		#          longs champs !!
		# => les chaînes seront matchables dans les 2 ordres possibles
		# ex: /nom\W*prénom/ et /prénom\W*nom/
		self.re = self.tok_full_regexp()
		
		# 3) on récupère ce qui deviendra le tag de sortie
		# -------------------------------------------------
		# SELF.TAGOUT
		# opening tag
		self.tagout = XTokinfo.xmlin_path_to_xmlout(self.relpath)
		# closing tag
		self.endout = re.sub(r'^<','</', re.sub(r' .*$','>', self.tagout))
		
	
	# =================================================
	# correspondance des annotations I/O
	def xmlin_path_to_xmlout(relpath, context=None):
		"""
		Translate an input structrured path into desired output markup
		"""
		# for this we use the global var : STRUCT_TO_BIBL
		# todo define ~ config.IN_TO_OUT with param table
		return XTokinfo.STRUCT_TO_BIBL[relpath]
	
	
	
	# =================================================
	# préparation d'une regexp pour un string donné
	def str_pre_regexp(self, anystring):
		"""Just the raw regexp string without capture"""
		# A) préparation du contenu
		# --------------------------
		subtokens = re_TOUS.findall(anystring)
		esctokens = [t for t in map(re.escape,subtokens)]
		# TODO ajouter ici possibilité tirets de césure
		my_re_str = "[\W¤]*".join(r'%s' % u for u in esctokens)
		
		# B) Décision du format des limites gauche et droite pour les \b
		# --------------------------------------------------
		# test si commence par une ponctuation échappée
		if re.match('\\\\*\W',my_re_str):
			prefix = ""
		else:
			prefix = "\\b"
		# idem mais plus facile à la fin
		if re.search('\W$', my_re_str):
			postfix = ""
		else:
			postfix = "\\b"
		
		# voilà
		return prefix + my_re_str + postfix
	
	# =================================================
	# construction de l'expression régulière à partir
	# de toutes sortes de strings seuls ou couplés
	def tok_full_regexp(self):
		"""The precompiled regexp with alternatives and parens around"""
		re_str=""
		
		# => cas normal : une seule chaîne dans self.xtexts
		if not self.combimode:
			# récup d'une seule chaîne échappée
			re_str = self.str_pre_regexp(self.xtexts)
		
		# => plusieurs chaînes matchables dans les 2 ordres possibles
		# ex: ['nom', 'prénom'] => /((?:nom\W*prénom)|(?:prénom\W*nom))/
		elif self.combimode:
			alternatives = []
			for substr_combi in permutations(self.xtexts):
				# jonction par un espace ou toute valeur de XTokinfo.BLANK
				str_combi = XTokinfo.BLANK.join(substr_combi)
				re_combi = self.str_pre_regexp(str_combi)
				
				# non capturing
				alternatives.append("(?:"+re_combi+")")
			
			# -or- using regex pipe
			re_str = "|".join(alternatives)
		
		# enfin ajout de balises de capture extérieures
		# et compilation
		my_regexp_object = re.compile("("+re_str+")")
		return my_regexp_object
	
	
	
	
	def __str__(self):
		return "%s : '%s' : %s" % (self.relpath, self.xtexts, self.tagout)
		# return "'%s' : %s" % (self.xtexts, self.tagout)
	
	def __repr__(self):
		return "<%s>" % self.__str__()

# --------------------------------------------------------

# --------------------------------------------------------




















###############################################################
########################### M A I N ###########################
###############################################################

# logstamp
# ========
# represents hope that all 3 steps go well
checklist = [True, True, True]

# options et arguments
# ====================
parser = prepare_arg_parser()
args = parser.parse_args(sys.argv[1:])

# défault pdfin
if args.pdfin == None and args.txtin == None :
	temp = re.sub(r'tei.xml', r'pdf', args.xmlin)
	args.pdfin = re.sub(r'xml', r'pdf', temp)
	print("PDFIN?: essai de %s" % args.pdfin, file=sys.stderr)

# vérification cohérence
if (args.model_type in ["reference-segmenter", "citations"] 
	and not args.txtin):
	print("""L'arg -m '%s' requiert un -t ad hoc (utiliser les cibles createTraining* de grobid-trainer)"""
		  % args.model_type,
		  file=sys.stderr)
	sys.exit(1)


#    INPUT XML
# ================
print("LECTURE XML", file=sys.stderr)

# TODO ==> on signale au passage les colonnes vides (xbibs vides en amont)

parser = etree.XMLParser(remove_blank_text=True)
# parse parse
try:
	dom = etree.parse(args.xmlin, parser)

except OSError as e:
	print(e)
	sys.exit(1)

except etree.XMLSyntaxError as e:
	print("lxml.etree:", e)
	sys.exit(1)


# query query
xbibs = dom.findall(
			"tei:text/tei:back//tei:listBibl/tei:biblStruct",
			namespaces=rag_procedures.NSMAP
			)
xbibs_plus = dom.xpath(
			"tei:text/tei:back//tei:listBibl/*[local-name()='bibl' or local-name()='biblStruct']",
			 namespaces=rag_procedures.NSMAP
			)

# pour logs
# ---------
nxb = len(xbibs)
nxbof = len(xbibs_plus) - nxb

# si présence de <bibl>
if (nxbof > 0):
	print("WARN: %i entrées dont  %i <bibl> (non traitées)" %
			 (nxb+nxbof, nxbof),
			 file=sys.stderr )
	
	# incomplétude du résultat à l'étape 0
	checklist[0] = False

# exception si aucune <biblStruct>
if (nxb == 0):
	print("ERR: aucune xbib <biblStruct> dans ce xml natif !",
			 file=sys.stderr)
	sys.exit(1)


# préalable: passage en revue des XML ~> diagnostics IDs
# ----------
# initialisation IDs et NOs
xml_ids_map = [None for j in range(nxb)]
xml_no_strs_map = [None for j in range(nxb)]
xml_no_ints_map = [None for j in range(nxb)]

# remplissage selon xpaths @id et @n
for j, xbib in enumerate(xbibs):
	
	# il devrait toujours y avoir un ID, mais en réalité parfois absent
	xbib_id_nodes = xbib.xpath("@xml:id") ;
	
	# si présent, l'attribut "@n" reprend le label (devrait toujours être numérique ?)
	xbib_no_nodes = xbib.xpath("@n") ;
	
	found_id = (len(xbib_id_nodes) == 1)
	found_no = (len(xbib_no_nodes) == 1 
				  and re.match(r'^[\[\]\.0-9 ]+$', str(xbib_no_nodes[0])))
	
	# récup id et numérotation
	if found_id and found_no:
		# lecture attributs XML
		thisbib_id = xbib_id_nodes.pop()
		thisbib_no_str = xbib_no_nodes.pop()
		thisbib_no_int = int(re.sub("[^0-9]+","", thisbib_no_str))
	
	# récup id et astuce numérotation attendue en fin d'ID 
	elif found_id and not found_no:
		thisbib_id = xbib_id_nodes.pop()
		
		# on cherche le dernier nombre pour mettre dans xml_nos_map
		# par ex: 1,2 ou 3 dans DDP278C1 DDP278C2 DDP278C3
		postfix_num_match = re.search(r"[0-9]+$", thisbib_id)
		
		if postfix_num_match:
			thisbib_no_str = postfix_num_match.group(0)
			thisbib_no_int = postfix_num_match.group(0)
		else:
			# rien trouvé pour le no: on mettra None dans xml_nos_map
			thisbib_no_str = None
			thisbib_no_int = None
	
	# les 2 cas restants: trouvé no sans id OU trouvé aucun
	else:
		thisbib_id = None
		thisbib_no_str = None
		thisbib_no_int = None
	
	# stockage de ce qu'on a trouvé
	# -----------------------------
	xml_ids_map[j] = thisbib_id
	xml_no_strs_map[j] = thisbib_no_str
	xml_no_ints_map[j] = thisbib_no_int
	

# verif incrément normal a posteriori 
# (ce diagnostic pourrait aussi être fait dès la boucle) 
FLAG_STD_MAP = True # temporaire
for j, no in enumerate(xml_no_ints_map):
	if (no is None) or (int(no) != j+1):
		FLAG_STD_MAP = False


# écriture dans variable globale pour matcher les labels réels en sortie
LABELS = []
for item in xml_no_strs_map:
	if item is None:
		LABELS.append(None)
	else:
		# remove padding 0s
		no = re.sub("^0+", "", item)
		LABELS.append(no)


if args.debug >= 1:
	print("IDs:", xml_ids_map, file=sys.stderr)
	print("NOs:", xml_no_ints_map, file=sys.stderr)
	print("NO_strs:", xml_no_strs_map, file=sys.stderr)
	if FLAG_STD_MAP:
		print("GOOD: numérotation ID <> LABEL traditionnelle",
				 file=sys.stderr)
	else:
		# todo préciser le type de lacune observée :
		# (pas du tout de labels, ID avec plusieurs ints, ou gap dans la seq)
		print("WARN: la numérotation XML:ID non incrémentale",
				 file=sys.stderr)

# // fin lecture xml bibs


if args.txtin:
	#  INPUT TXT à comparer
	# ======================
	print("---\nLECTURE FLUX TXT ISSU DE PDF", file=sys.stderr)
	
	try:
		rawlines = [line.rstrip('\n') for line in open(args.txtin)]
	except FileNotFoundError as e:
		print("I/O ERR: Echec ouverture du flux textin '%s': %s\n"
				  % (e.filename,e.strerror),
				  file=sys.stderr)
		sys.exit(1)

elif args.pdfin:
	#  INPUT PDF à comparer
	# ======================
	print("---\nLECTURE PDF", file=sys.stderr)

	# appel pdftotext via OS
	try:
		pdftxt = check_output(['pdftotext', args.pdfin, '-']).decode("utf-8")
	
	except CalledProcessError as e:
		print("LIB ERR: Echec pdftotxt: cmdcall: '%s'\n  ==> failed (file not found?)" % e.cmd, file=sys.stderr)
		# print(e.output, file=sys.stderr)
		sys.exit(1)
	# got our pdf text!
	rawlines = [line for line in pdftxt.split("\n")]

else:
	print("""ARG ERR: On attend ici --pdfin foo.pdf
			 (ou alors --txtin bar.txt)""",
			 file=sys.stderr)
	sys.exit(1)


# pour logs
# ---------
npl = len(rawlines)

print ("N lignes: %i" % npl, file=sys.stderr)


# La zone biblio dans le texte  pdf est un segment marqué par 2 bornes
#       (par ex: d=60 et f=61 on aura |2| lignes intéressantes)
# ----------------------------------------------------------------------
debut_zone = None
fin_zone = None


#    ============
# -a- Cas facile
# (si on a un txtin visant 'citations' ou 'reference-segmenter'
#  en entraînement, le flux ne contiendra *que* la zone des biblios
if (args.model_type in ["reference-segmenter", "citations"]):
	debut_zone = 0
	fin_zone = npl -1 

#            =======================
# -b- sinon : Recherche zone biblio
else:
	print("---\nFIND PDF BIBS", file=sys.stderr)
	
	(debut_zone, fin_zone) = rag_procedures.find_bib_zone(
									 xbibs,
									 rawlines,
									 debug=args.debug
							  )
	
	#  !! debut_zone et fin_zone sont des bornes inclusives !!
	#  !!         donc nos slices utiliseront fin+1         !!
	#                      ------             -----
	
	if ((debut_zone == None) or  (fin_zone == None)):
		print("ERR: trop difficile de trouver la zone biblio dans ce rawtexte '%s'" % args.pdfin, file=sys.stderr)
		sys.exit(1)



# (à présent: match inverse pour aligner)
# =======================================
#  Alignement lignes txt <=> entrées XML
# =======================================
print("---\nLINK PDF BIBS <=> XML BIBS", file=sys.stderr)

# get correspondance array
# (sequence over pdf content lines ids filled with matching xml ids)
winners = rag_procedures.link_txt_bibs_with_xml(
				   rawlines[debut_zone:fin_zone+1], 
				   xbibs, 
				   debug=args.debug
				   )

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


# TODO ici utilisation de xml_nos_map pour faire des tokens labels

# vérification si on ne doit garder que les documents qui matchent bien
# (par exemple quand on génère un corpus d'entraînement)

if not check_align_seq(winners):
	
	# désordre du résultat à l'étape 1
	checklist[1] = False

# pour la sortie : traduction de la checkliste en "101", "111", etc
out_check_trigram = ""
for test in checklist:
	if test:
		out_check_trigram += "1"
	else:
		out_check_trigram += "0"

# -------=============--------------------------------------------------
# boucle OUTPUT mode 1 (dans le cas *reference-segmenter*: alignements)
# -------=============--------------------------------------------------

if args.model_type=="reference-segmenter":
	
	# log de la checkliste (évaluation qualité de ce qui sort)
	CHECKS = open("checks.refseg.tab", "a")

	# header
	header="""<tei>
<teiHeader>
	<fileDesc xml:id="%s"/>
</teiHeader>
<text xml:lang="en">
	<listBibl>""" % args.xmlin
	print (header)
	
	# yalla !
	print ("~" * 80, file=sys.stderr)
	
	# buffer for lines of the same xml elt
	local_grouped_lines = []
	
	# txtin donc len(winners) = len(rawlines)
	if len(winners) != len(rawlines):
		raise ValueError("wtf??")
	
	for i, this_line in enumerate(rawlines):
		
		# récup de l'indice XML correspondant à la ligne
		j_win = winners[i]
		
		# lookahead de l'indice suivant
		if i+1 < npl:
			next_win = winners[i+1]
		else:
			next_win = None
		
		# cas aucune ligne matchée
		if j_win is None:
			# on ne peut rien reporter sur cette ligne
			# mais on la sort quand même (fidélité au flux txtin)
			print(this_line)
		else:
			# nouveau morceau
			if len(local_grouped_lines) is 0:
				# tentative de report du label
				xlabel = LABELS[j_win]
				if xlabel:
					# TODO faire une fonction à part et reserver match_citation_fields au cas citations ?
					# -------------------8<-------------------------
					# report du label sur chaîne de caractères réelle
					(my_bibl_line, success) = match_citation_fields(
												this_line,
												label = xlabel,
												debug = args.debug,
											   )
					# pas prévu pour
					my_bibl_line = re.sub("</bibl>$","",my_bibl_line)
					# -------------------8<-------------------------
				else:
					my_bibl_line = "<bibl>"+this_line
				
				# >> BUFFER, dans les 2 cas
				local_grouped_lines.append(my_bibl_line)

			# morceaux de suite
			elif next_win == j_win:
				# ligne sans balises
				local_grouped_lines.append(this_line)
			# morceau de fin >> SORTIE
			else:
				local_grouped_lines.append(this_line+'</bibl>')
				# separateur saut de ligne
				#  => sortie finale format ref-seg
				#     -------------
				print("<lb/>".join(local_grouped_lines))
				
				# empty buffer
				local_grouped_lines = []
	
	print ("~" * 80, file=sys.stderr)
	print (
		   args.xmlin
			 +"\t"+out_check_trigram[0]
			 +"\t"+out_check_trigram[1], 
		   file=CHECKS
		   )
	
	CHECKS.close()
	
	# tail
	tail="""
	</listBibl>
</text>
</tei>"""
	print (tail)
	
	sys.exit(0)

# -------------------------------------------------------------
#  mode 2: boucle plus simple pour les sorties + "standardes"
# -------------------------------------------------------------
#    in std mode we go further by grouping content from pdf
#     (each raw txtline i') by its associated xml id j_win
#   --------------------------------------------------------
else:
	# résultat à remplir
	rawlinegroups_by_xid = [None for j in range(nxb)]
	
	for i_prime, j_win in enumerate(winners):
		if j_win is None:
			# we *ignore* None values 
			# => if we wanted them we need to fix them earlier
			pass
		# === normal case ===
		else:
			# nouveau morceau
			if rawlinegroups_by_xid[j_win] is None:
				rawlinegroups_by_xid[j_win] = rawlines[debut_zone+i_prime]
			# morceaux de suite
			else:
				# on recolle les lignes successives d'une même bib
				# separateur saut de ligne: '¤' ASCII 207
				#  => format sortie citations: neutre dans les reports car matche /\W+/
				rawlinegroups_by_xid[j_win] += "¤"+rawlines[debut_zone+i_prime]
	
	# log détaillé de cette étape
	if args.debug >= 1:
		# linked results
		print("="*70, file=sys.stderr)
		for j in range(nxb):
			xml_info = rag_procedures.glance_xbib(xbibs[j], longer = True)
			if rawlinegroups_by_xid[j] is None:
				print(xml_info + "\n<==> NONE", file=sys.stderr)
			else:
				print(xml_info + "\n<==>\n" + rawlinegroups_by_xid[j], file=sys.stderr)
			print("="*70, file=sys.stderr)
	
	
	#       ------------------------------------          =============
	#  Enfin alignement des champs sur le texte et boucle OUTPUT mode 2
	#       ------------------------------------          =============
	print("---\nLINK PBIB TOKENS <=> XBIB FIELDS\n", file=sys.stderr)
	
	# report de chaque champ
	bibl_found_array = []
	
	for j, group_of_real_lines in enumerate(rawlinegroups_by_xid):
			
			this_xbib = xbibs[j]
			
			xlabel = LABELS[j]
			
			toks = []
			
			if group_of_real_lines is None:
				if args.debug > 1:
					print("===:no lines found for xbib %i (label %s)"
							 % (j,xlabel))
				
				# incomplétude constatée du résultat à l'étape link_lines
				checklist[1] = False
				continue
			
			else:
				# report des balises sur chaîne de caractères réelle
				(my_bibl_str, success) = match_citation_fields(
											group_of_real_lines,
											subtree = this_xbib,
											label   = xlabel,
											debug   = args.debug
										   )
				
				# update 3è slot checklist pour filtrage erreurs
				# (1 info par refbib et non plus sur l'ens.)
				checklist[2] = success
				
				# separateur saut de ligne dans le cas 'citations' 
				# (TODO check si c'est bien " " attendu et pas "" ?)
				my_bibl_str = re.sub("¤"," ",my_bibl_str)
				
				#  => sortie finale format 'citations'
				#     -------------
				print(out_check_trigram+":"+my_bibl_str)
	
	
	# EXEMPLES DE SORTIE
	# -------------------
	# <bibl> <author>Whittaker, J.</author>   (<date>1991</date>).   <title level="a">Graphical Models in Applied Multivariate Statistics</title>.   <publisher>Chichester: Wiley</publisher>. </bibl>

	# <bibl> <author>Surajit Chaudhuri and Moshe Vardi</author>.  <title level="a">On the equivalence of recursive and nonrecursive data-log programs</title>.   In <title level="m">The Proceedings of the PODS-92</title>,   pages <biblScope type="pp">55-66</biblScope>,   <date>1992</date>. </bibl>

	
	# TODO: pour 'citations' ajouter aussi les non alignées != groups_by_xid comme pour l'autre
	
	# voilà fin mode 2
	sys.exit(0)

