#! /usr/bin/python3
# -*- coding: UTF-8 -*-

"""Repérage approximatif des lignes refbib dans un article txt 
   et sortie de décomptes sur les bigrammes punct, majuscules, dates
   
   => aka "matrice de diagnostic typobib"
   
   mode d'operation:
   ==================
   punct_dig_cap_matrix.py --dir ../PMC_mime_et_id/txt/ > matrice_docXpunct_1927docs.tab
 
   Ensuite on clusterise dans R:
   ------------------------------
   dp = read.table("matrice_docXpunct_20docs.tab", header=TRUE)
   dpnor = dp / rowSums(dp)
   dpnor.dist = dist(dpnor)
   library(cluster)
   k12 = sort(pam(dpnor.dist, k = 12, cluster.only=TRUE))
   write.table(k12, "echantillon.typobib_clu12.ls2", sep="\t", quote=F, col.names=F, row.names=T)
   """

import re
import os
import sys
import argparse
import glob           # pour lire la liste des fichiers
import unicodedata    # pour avoir les noms de charactères unicode

def charmatch2token(re_match):
	"""remplace un match d'expression régulière (match object)
	par un {_TOKEN_} avec le nom unicode (sans espace ni tiret)
	du premier caractère du match"""
	char = re_match.group(0)
	if len(char) != 1:
		char = char[0]
		print ("trop de caractères dans le match, je ne prends que le 1er", file=sys.stderr)
	name = unicodedata.name(char[0])
	name = re.sub("[- ]+","",name)
	
	return "{_"+name+"_}"


def ngrams(array,n):
	""" Construit une liste de n-grammes 
	à partir d'une liste de tokens"""
	ngrams = []
	array= ['START']+array+['STOP']
	length = len(array)
	for i in range(length-n+1):
		# le n-gramme est la slice [i:i+n]
		ng = array[i:i+n]
		ngrams.append("__".join(ng))
	return ngrams


def nettoyage_non_pertinents(string):
	"""substitutions de caractères rares mais non fonctionnels en refbib
	(par ex: les espaces alternatifs, ligatures, caras de contrôle...)
	(mais pas: les ponctuations rares => toutes conservées)"""
	
	# ligatures --> décomposition
	string = re.sub(r"Ꜳ","AA",string)
	string = re.sub(r"ꜳ","aa",string)
	string = re.sub(r"Æ","AE",string)
	string = re.sub(r"æ","ae",string)
	string = re.sub(r"Ǳ","DZ",string)
	string = re.sub(r"ǲ","Dz",string)
	string = re.sub(r"ǳ","dz",string)
	string = re.sub(r"ﬃ","ffi",string)
	string = re.sub(r"ﬀ","ff",string)
	string = re.sub(r"ﬁ","fi",string)
	string = re.sub(r"ﬄ","ffl",string)
	string = re.sub(r"ﬂ","fl",string)
	string = re.sub(r"ﬅ","ft",string)
	string = re.sub(r"Ĳ","IJ",string)
	string = re.sub(r"ĳ","ij",string)
	string = re.sub(r"Ǉ","LJ",string)
	string = re.sub(r"ǉ","lj",string)
	string = re.sub(r"Ǌ","NJ",string)
	string = re.sub(r"ǌ","nj",string)
	string = re.sub(r"Œ","OE",string)
	string = re.sub(r"œ","oe",string)
	string = re.sub(r"ﬆ","st",string)
	string = re.sub(r"Ꜩ","Tz",string)
	string = re.sub(r"ꜩ","tz",string)
	
	# caractères de contrôle --> espace 
	# (excepté \t:0009, \n:000A et \r:000D)
	string = re.sub(u"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]"," ",string)
	
	# tous les espaces alternatifs --> espace
	string = re.sub(u"[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]"," ",string)
	
	# divers
	string = re.sub(r"…","...",string)
	string = re.sub(r"€","EUR",string)
	
	return string

########################################################################

if __name__ == "__main__":
	# Parsing des options
	# --------------------
	parser = argparse.ArgumentParser(
		description="Repérage approximatif des lignes refbib dans un article txt et sortie de décomptes sur les bigrammes punct, majuscules, dates",
		epilog="-----(© 2014 Inist-CNRS (ISTEX) romain.loth at inist dot fr )-----")
	
	parser.add_argument('-d','--dir',
		metavar='path/to/inputdir',
		help='path to a directory containing documents in txt format',
		default="/home/loth/refbib/TESTS/txt_tests_typobib/minicorpus",
		required=True,
		action='store')
	
	parser.add_argument('-d2','--dir2',
		metavar='path/to/inputdir2',
		help='idem pour des documents à traiter ensemble avec ceux du premier dossier (ex traceurs supplémentaires)',
		default="/home/loth/refbib/corpus/exemples_styles/resultat_typobib_traceurs",
		required=False,
		action='store')
	
	#TODO non implémenté
	parser.add_argument('-t','--tfidf',
		help='apply tfidf transformation to table contents',
		default=False,
		required=False,
		action='store_true')
	
	parser.add_argument('-p','--profondeur',
		help='depth of glob on dir -d',
		metavar='2',
		default=1,
		required=False,
		action='store')
	args = parser.parse_args(sys.argv[1:])
	
	
	# Lecture dossier
	# ----------------
	depth_path = '/*' * int(args.profondeur)
	doc_paths =  sorted(glob.glob(args.dir+depth_path+".txt"))
	N_docs = len(doc_paths)
	
	print("DOSSIER: %i fichiers .txt dans '%s'" % (N_docs,args.dir), file=sys.stderr) ;
	
	
	if args.dir2:
		doc_paths2 = sorted(glob.glob(args.dir2+"/*.txt"))
		N_docs2 = len(doc_paths2)
		print("DOSSIER: %i fichiers .txt dans '%s'" % (N_docs2,args.dir2), file=sys.stderr) ;
		#~ 
		#~ # les fichiers supplémentaires seront traités ensemble
		doc_paths += doc_paths2
		N_docs += N_docs2
		
		print("EN TOUT: %i fichiers .txt traités ensembles" % N_docs, file=sys.stderr) ;
	
	# max pour debug
	#doc_paths = doc_paths[0:300]
	
	
	
	
	
	
	# Conteneurs pour stats en sortie
	# --------------------------------
	matrix = {}    # décompte par doc par n-gramme
	cols = {}      # décompte global par n-gramme
	
	keptlines = {}  # nombre de lignes par doc
	
	# regexps (re) et character classes (cc)
	# ---------------------------------------
	cc_bibpunct = r"-:;,.\(\)\[\]«»'‘’‚‛\"“”„‟‹›‒–—―−﹣"
	cc_poorbibpunct = r"-:;,.\(\)\[\]'\""
	cc_AZ = r"A-ZÀÁÂÃÄÅĄĀĂÇĆĈĊČĎĐÈÉÊËĘĒĔĖĚĜĞĠĢĤĦÌÍÎÏĨĪĬĮİĴĶŁĹĻĽĿÑŃŅŇÒÓÔÕÖØŌŎŐŔŖŘŚŜŞŠŢŤŦÙÚÛÜŨŪŬŮŰŲŴŸÝŶŹŻŽ"
	
	# TODO utiliser les catégories unicode "isLetter" "isLowercase" ?
	cc_az = r"αβγδεζηθικλμνξοπρστυφχψωa-zàáâãäåąāăçćĉċčďđèéêëęēĕėěĝğġģĥħìíîïĩīĭįıĵķłĺļľŀñńņňòóôõöøōŏőŕŗřśŝşšţťŧùúûüũūŭůűųŵÿýŷźżž"
	
	# 2005a
	re_datelike = r"(?:18|19|20)[0-9]{2}[abcde]?"
	
	# date + ponctuation (très caractéristique des lignes refbib) : exemples "(2005)", "2005a," 
	re_datepunct = r"[:;,.\(\[]?\s?(?:18|19|20)[0-9]{2}[abcde]?\s?[:;,.\)\]]"

	# exemples : "68(3):858-862" ou "68(3), 858-862" ou "68: 858-862" etc.
	re_vol_infoA = r"[0-9]+(?:\([0-9]+\))?\s?[:,]\s?[0-9]+\s?[-‒–—―−﹣Á]\s?[0-9]+"
	
	# exemples : "vol. 5, no. 8, pp. 1371"   "Vol. 5, No. 8, pp 1371-1372
	re_vol_infoB = r"\b[Vv]ol\.?\s?[0-9]+\s?[,\.;]\s?[Nn]o\.?\s?[0-9]+\s?[,\.;]\s?pp?\.?\s?\d+\s?[-–Á]?\s?\d*"
	
	# reconnaissance de fragments très générique : marche uniquement car vol n'est pas un mot (l'équivalent pour "No" serait irréaliste)
	re_vol = r"\b[Vv]ol\.?(?=[\s\d])"
	re_pp = r"\bpp\.?(?=[\s\d])"
	
	# plus rares mais surs (à cause de la présence du ':')
	re_in = r"\b[Ii]n ?:"
	re_doi = r"doi:10\.[\S]+"
	
	
	# Boucle sur docs
	# ---------------
	for (k,fpath) in enumerate(doc_paths):
		# fid = os.path.splitext(os.path.basename(fpath))[0]
		
		# multidossiers
		fid = fpath
		
		# ----cas particulier-----8<--------------
		# pour les fid=Acta_Vet_Scand_2011_May_31_53(1)_34--__--1751-0147-53-34.pdf.txt
		# on ne garde que Acta_Vet_Scand_2011
		if re.search(r"--__--", fid):
			fid = re.sub(r"(?<=(?:18|19|20)[0-9]{2}).*","",fid)
		# ------------------------8<--------------
		
		# initialisation du sous-dict pour ce doc
		matrix[fid] = {}
		
		# info debg
		keptlines[fid] = 0
		
		# open
		try:
			lines = [line.rstrip() for line in open(fpath)]
		except IOError:
			print("Echec ouverture fichier '%s'"%fpath)
			sys.exit()
		except UnicodeDecodeError as e:
			print("Echec unicode à l'open fichier '%s'\n\t└──>%s"%(fpath, format(e)))
			sys.exit()
		
		previous_line = ""
		
		# TODO 2 boucles :
		# - premier passage pour trouver les refbibs
		# - deuxième pour extraire leurs pontctuation et autres tokens 
		
		for line_counter, line in enumerate(lines):
			# nettoyage de la ligne
			# ----------------------
			# on remplace les ligatures ﬀ -> ff etc.
			cleanline = nettoyage_non_pertinents(line)
			
			# tests préalables : on cherche des lignes de refbib
			# --------------------------------------------------
			# éviter les lignes vides et doublons dans les données
			if ((re.match("^\s*$",cleanline))
				or (cleanline == previous_line)):
				continue
			
			# compter les expressions qu'on aimerait avoir le plus possible
			n_punct = len(re.findall(r"[%s]"%cc_bibpunct, line))
			n_sing_maj = len(re.findall(r"\b([%s])\b"%cc_AZ, line))
			n_date = len(re.findall(re_datelike, line))
			
			n_datepunct = len(re.findall(re_datepunct, line))
			
			n_vol_info = len(re.findall(re_vol_infoA, line)) + len(re.findall(re_vol_infoB, line))
			n_in = len(re.findall(re_in,line))
			n_doi = len(re.findall(re_doi,line))
			n_vol = len(re.findall(re_vol,line))
			n_pp = len(re.findall(re_pp,line))
			
			#n_all = n_punct + n_sing_maj + n_date + n_vol_info + n_in
			
			# NB: on ne compte pas ici "and" peu distinctif
			# et "et al" plus fréquent dans les renvois de citations que les références elles-mêmes
			
			# expressions qui ressemblent trop à des tableaux de chiffres
			n_table_number_like = len(re.findall('[0-9]{1,3}[.,][0-9]', line))
			
			previous_line = line
			
			# test proprement dit : 
			# on ne garde plus que les lignes ayant un ou plusieurs marqueurs symptomatiques des refbibs
			if (
				(
				  (n_datepunct > 0)
				  or (n_doi > 0)
				  or (n_vol_info > 0)
				  or (n_in > 0)
				  or (n_vol > 0)
				  or (n_pp > 0)
				  or ( (n_date + n_punct > 5) and (n_sing_maj > 3) )
				)
				and (n_table_number_like < 3)
			   ):
				
				keptlines[fid] += 1
				#print("p%i m%i d%i v%i | t%s: %s" %(n_punct,n_sing_maj,n_date,n_vol_info,n_table_number_like,line), file=sys.stderr)
				#continue
				
				# capture des éléments ressemblant à des fragments de biblio
				# -----------------------------------------------------------
				# séquence (2 x A-tokenisation, B-bigramisation, C-décomptes)
				# On fait la tokenisation deux fois :
				#  - jeu de tokens "riches" et spécifiques à certaines biblio
				#  - jeu de tokens "pauvres" mais plus universels ex: s/[«»“”„‟]/"/g
				#  => on obtient ainsi pour le clustering 2 représentations des 
				#     données à 2 niveaux de généralité)
				
				# NB : 
				#   - les tokens sont de forme {_[A-Z+]+_} avec majuscules et '+'
				#   - ils seront obtenus par substitutions successives sur la ligne
				#   - cette méthodo rend l'ordre des substitutions très important
				
				# au cas où: prévenir conflits avec formes {_BLA_} éventuelles
				if re.search(r"\b{_[A-Z]+_}\b",cleanline):
					print("%s contient un match qui ressemble à nos tokens : '%s'"%(fpath,line),file=sys.stderr)
					cleanline = re.sub(r"\b{_[A-Z]+_}\b","{_UNKNOWN_}",cleanline)
				
				
				# A1) Tokenisation 'pauvre'
				# -------------------------
				# on garde le moins possible d'éléments : 
				#  - les plus fonctionnels seulement
				#  - si possible en groupant un maximum de variantes
				poor_line = cleanline
				
				# simplification préalable de ponctuation
				# (! crucial pour la version 'pauvre' !)
				poor_line = re.sub(r"[‒–—―−﹣]",'-',poor_line)
				poor_line = re.sub(r"[«»“”„‟]",'"',poor_line)
				poor_line = re.sub(r"[‹›‘’‚‛]","'",poor_line)
				poor_line = re.sub(r"''",'"',poor_line)
				
				# tentative de suppression de la plupart des simple quotes apostrophes
				poor_line = re.sub(r"'s\b"," s",poor_line)           # Adler's => Adler s
				poor_line = re.sub(r"\bO'(?=[A-Z])","O",poor_line)   # O'Neill => ONeill
				# ce dernier sans espace pour éviter la multiplication des initiales
				
				# tokenisation proprement dite des ponctuations intéressantes
				# (,;- mais pas ?! etc) => vers fonction unicodedata.name
				poor_line = re.sub(r"[%s]"%cc_poorbibpunct,charmatch2token,poor_line)
				
				# ressemblant à une date
				poor_line = re.sub(re_datelike,"{_DATE_}",poor_line)
				
				# autres nombres
				poor_line = re.sub("\d+","{_NOMBRE_}",poor_line)
				
				# on incorpore le point éventuel dans l'initiale (une ou deux MAJ de suite)
				poor_line = re.sub(r"\b[%s]{1,2}\.?(?=[^%s%s])"%(cc_AZ,cc_AZ,cc_az),"{_INITIALE_}",poor_line)
				
				
				# RECUPERATION [LISTE] des contenus de tokens
				poor_toks = re.findall(r"{_([A-Z]+)_}", poor_line)
				
				#print(poor_toks)
				
				
				
				# A2) Tokenisation 'riche'
				# -------------------------
				rich_line = cleanline
				
				# volume etc (à mettre avant les autres punct et nombre)
				rich_line = re.sub(re_vol_infoA,"{_VOLINFO_}",rich_line)
				rich_line = re.sub(re_vol_infoB,"{_VOLINFO_}",rich_line)
				
				# tokenisation des marqueurs in:, etal. , and
				rich_line = re.sub(re_in,"{_IN_}",rich_line)
				rich_line = re.sub(r"\bet ?al[.\b]","{_ETAL_}",rich_line)
				rich_line = re.sub(r"(?:\band\b)|&","{_AND_}",rich_line)
				
				## ressemblant à une date
				rich_line = re.sub(re_datelike,"{_DATE_}",rich_line)
				
				## autres nombres
				rich_line = re.sub("\d+","{_NOMBRE_}",rich_line)
				
				## ponctuation intéressante 
				# (version riche: sans remplacements préalables, qui certes pourraient être utiles 
				#  pour la reconnaissance et le classement, mais empêchent de *diagnostiquer* les
				#  différences dans la phase d'évaluations :  ce n'est pas parce qu'on pourrait
				#  tokeniser ensemble « et " qu'ils ne constituent pas une différence pour l'outil évalué)
				rich_line = re.sub(r"[%s]"%cc_bibpunct,charmatch2token,rich_line)
				
				## on incorpore le point éventuel dans l'initiale (une ou deux MAJ de suite)
				rich_line = re.sub(r"\b[%s]{1,2}\.?(?=[^%s%s])"%(cc_AZ,cc_AZ,cc_az),"{_INITIALE_}",rich_line)
				
				# en deux temps : préalables WORD/CAPWORD puis groupes WORD+/CAPWORD+
				# prealable: mots commençant par une majuscule
				rich_line = re.sub(r"\b[%s]\w+\b"%cc_AZ,"{_CAPWORD_}",rich_line)
				# prealable: tous les autres mots (sauf nos tokens!!)
				rich_line = re.sub(r"\b[%s]+\b"%cc_az,"{_WORD_}",rich_line)
				# groupe
				rich_line = re.sub(r"(?:{_CAPWORD_} *)+(?:{_WORD_} *)*","{_CAPWORD&_}", rich_line)
				# groupe
				rich_line = re.sub(r"(?:{_WORD_} *)+","{_WORD&_}", rich_line)
				
				##reste:  tout devrait être tokénisé sauf certaines ponctuations (%/?!) et des caractères rares
				##reste = re.sub(r" ?(?:{_[A-Z&]+_} ?)+","",rich_line)
				
				## RECUPERATION [LISTE] des contenus de tokens riches
				rich_toks = re.findall(r"{_([A-Z&]+)_}", rich_line)
				
				# B) Ngrammisation
				# ----------------
				
				line_ngrams = ngrams(poor_toks, 3)    # trigrammes
				line_ngrams += ngrams(rich_toks, 2)   # bigrammes
				
				# C) Décomptes
				# ------------
				for ng in line_ngrams:
					# incrément global
					if ng in cols:
						cols[ng] += 1
					else:
						cols[ng] = 1
					# incrément par document
					if ng in matrix[fid]:
						matrix[fid][ng] += 1
					else:
						matrix[fid][ng] = 1
		
		# affichage d'un compteur de docs pendant le traitement
		print(str(k)+"--> "+fid+"                    \r", file=sys.stderr, end="")
	# ---------------------------------
	# ok on a vu tous les documents !
	print("",file=sys.stderr)
	# ---------------------------------
	
	# pour chaque ngramme on relève le nombre de docs où il apparait
	df = {}
	for ng in cols:
		for fid in matrix:
			# ng apparait dans le doc docid
			if ng in matrix[fid]:
				if ng in df:
					df[ng] += 1
				else:
					df[ng] = 1
	
	# détail du tableau df :
	#for elt in sorted(df, key=(lambda k: df[k])):
		#print("df:%s = %i"%(elt,df[elt]))
	
	
	# à présent on choisit les colonnes qui
	# en valent la peine et un ordre canonique
	canonic_cols = []
		
	## pour debug
	last_n_occ = 0
	last_df = 0
	
	if len(df.values()):
		max_df = max(df.values())
	else:
		max_df = -1
	
	# minimum d'occurrences totales permises pour un ngramme
	min_occ = max(N_docs/20, 15)
	
	# on classe les ngrammes par décompte décroissant
	for key in sorted(cols, key=(lambda k: cols[k]), reverse=True):
		# condition 1 : la somme totale des occurrences doit être >= 15 et >= N_docs/10
		if ((cols[key] >= min_occ)
		 #condition 2 : la colonne doit apparaître dans 3 docs au moins
		 and (df.get(key,-1) >= 3)
		 #condition 3 : la colonne doit apparaître dans moins de 95% des docs
		 and (df[key] < N_docs*95/100)
		 ):
			
			canonic_cols.append(key)
			
			## pour debug
			last_n_occ = cols[key]
			last_df = df[key]
	
	## pour debug
	print("total",len(cols), file=sys.stderr)
	print("len",len(canonic_cols), file=sys.stderr)
	print("last value",last_n_occ, file=sys.stderr)
	print("last docfreq",last_df, file=sys.stderr)
	print("max docfreq",max_df, file=sys.stderr)
	# infos debug +
	for docid in keptlines:
		print("%s\t%i"%(docid, keptlines[docid]), file=sys.stderr)
	
	# Sortie CSV
	# ------------
	
	# noms de colonnes
	print("\t"+"\t".join(canonic_cols))
	
	# TABLEAU
	for docid in sorted(matrix):
		line_vals = []
		# booléen d'erreur (TODO prendre en compte avant la selection des colonnes)
		empty_doc_flag = True
		
		# remplissage
		for column in canonic_cols:
			if column in matrix[docid]:
				val = matrix[docid][column]
			else:
				val = 0
			line_vals.append(val)
			if val != 0:
				empty_doc_flag = False
		
		# vérification
		if empty_doc_flag:
			print("SKIP: Le doc %s n'a aucun bigramme dans les colonnes canon" % docid, file=sys.stderr)
		# cas normal : impression CSV
		else:
			csvline = docid+"\t"+"\t".join([str(val) for val in line_vals])
			print(csvline)
	
	
