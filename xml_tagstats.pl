#! /usr/bin/perl

# xml_tag-stats.pl : statistiques récursives sur les éléments 
#                    dans un fichier XML
# --------------------------------------------------------------------------------
#  message /help/ en fin de ce fichier       version: 1 (12/06/2014)
#  copyright 2014 INIST-CNRS        contact: romain dot loth at inist dot fr
# --------------------------------------------------------------------------------

# EXEMPLE DE SORTIE
# root
#  └── citation 15
#      ├── person-group 14
#      │   └── name 72
#      │       ├── given-names 72
#      │       └── surname 72
#      ├── year 14
#      ├── source 12
#      ├── volume 12
#      ├── fpage 12
#      └── lpage 11
#
# Le nombre est l'effectif de chaque <élément> ou <sous-élément> xml

use warnings ;
use strict ;
use utf8 ;
use Encode ;
binmode(STDERR, ":utf8");
binmode(STDOUT, ":utf8");

use Getopt::Long ;

# pour lire le XML
use XML::LibXML ;

use Data::Dumper ;

################ SWITCHES + ARGS ##################

# INPUT = dossier xmldir + (extension des fichiers OU glob ex: "iop*.xml")
my $xmldir = "." ;
my $file_ext = "xml" ;
my $file_glob = "" ;


# ou INPUT = fichier seul
my $FILE_IN = "" ;
sub set_file_in {
	my $path = shift ;
	if (-e $path) { $FILE_IN = $path ; }
	     else     { die "Fichier introuvable: '$path'\n" ; }
}

# chemin XPATH du point de départ des décomptes
my $start_elt = "/" ;
# my $start_elt = "/TEI/text/back//biblStruct" ;
# my $start_elt = "/article/back/ref-list/ref" ;

# option bool pour sortie alternative
# (sort un décompte simple au lieu de l'arbre)
my $liste = 0 ;

# option bool pour tri alphabétique (sinon par défaut tri numérique décroissant)
my $ALPHA = 0 ;

# s'il y a un namespace par défaut, ne pas l'ignorer et respecter strictement les specifs xpath
# (par exemple un xpath comme "//tag" ne matchera pas <tag xmlns="bidule"> où bidule est un ns déclaré sans prefixe)
my $strictns = 0 ;

# additional ns declaration eg "tei:http://www.tei-c.org/ns/1.0"
my $ns_add = "" ;

# option bool pour complètement ignorer les entités (substituées avant parse)
my $ignore_ents = 0 ;

my $DO_RECODAGE_TAGS = "" ;

my $SHOW_MISC_ATTRS = 0 ;

# # # # # # # # # # # # # # # # # # # # # # # # # # 
 GetOptions ("<>"    => \&set_file_in,  # non-option (input file path)
			 "dir:s" => \$xmldir,       # opt str    (input dir)
			 "ext:s" => \$file_ext,     # opt str    (input file extensions)
			 "glob:s" => \$file_glob,   # opt str    (input file glob)
			 
			 "xpath:s" => \$start_elt,  # opt str    (xpath to root of counting)
			 "nsadd:s" => \$ns_add,     # opt str    ns declaration eg "tei:http://www.tei-c.org/ns/1.0"
			 
			 "killent" => \$ignore_ents,  # opt bool   (ignore all XML entities)
			 "moreattrs" => \$SHOW_MISC_ATTRS,  # opt bool   (ignore all XML entities)
			 "liste" => \$liste,        # opt bool   (alternative output)
			 "alpha" => \$ALPHA,        # opt bool   (alphabetic sort in tree output)
			 
			 "help"  => \&HELP_MESSAGE, # opt str
			 ) ;

if ($file_ext eq "nxml" || $file_ext eq "tei.xml") {
	warn "recodage de certains tags spécifiques au format $file_ext" ;
	$DO_RECODAGE_TAGS = $file_ext ;
}

# Fichier(s) xml à lire
my @xml_paths = () ;

# Si un seul fichier
if ($FILE_IN) {
	@xml_paths = ($FILE_IN) ;
}
# Sinon lecture dossier
else {
	# on part du principe qu'on a un dossier mixte
	# donc on filtre sur glob ou sur extension $FILE_EXT
	if ($file_glob) {
		@xml_paths = map {decode('UTF-8', $_)} glob("$xmldir/$file_glob") ;
	}
	else {
		@xml_paths = map {decode('UTF-8', $_)} glob("$xmldir/*.$file_ext") ;
	}
} 

my $N = scalar(@xml_paths) ;
print "($N fichier".($N==1?"":"s")." .$file_ext)\n" ;

############# lecture et traitement ###############

### POUR STATS
# compteur
my $doc_i = 0 ;
my $total_matches = 0 ;
my $rec_freq_hash = {} ;

# table de lookup doc_i <=> doc_name
my %lookup = () ;

# parseur XML
my $parser = XML::LibXML->new(load_ext_dtd => 0) ;


# flag décidé sur le premier document
#   vaut soit 0 (inactif)
#        soit une URI (si il y a un default namespace)
my $has_default_namespace_uri = 0 ;

#### BOUCLE SUR DOCS ####
for my $path (@xml_paths) {
	## Pointeur sur document
	$doc_i ++ ;
	# pour log
	my $doc_i_str = sprintf("%04d", $doc_i) ;
	
	my $content = "" ;
	
	open (DOC, "< $path") 
	 || die "Problem opening document '$path'\n" ;
	while (<DOC>) {
		if ($ignore_ents) {
			s/&[^;]+;/__ENT__/g ;
		}
		$content .= $_ ;
	}
	close DOC ;
	#~ die $content ;
	
	######## APPEL DU PARSEUR ######################
	my $doc ;
	eval { $doc = $parser->parse_string($content) ; } ;
	
	# eval { $doc = $parser->parse_file($path) ; } ;
	
	#~ warn Dumper $doc ;
	
	# on saute le doc si déclenche une erreur de parsing xml
	if ($@) {
		warn "XMLERR: doc $doc_i_str ($path)\n" ;
		warn (errlog($@,$path)) ;
		next ;
	}
	
	
	# préparation XPATH
	my $xpath_ng  = XML::LibXML::XPathContext->new($doc->documentElement());
	
	# ----------------------------------------------------------------------- -------
	# correction des namespaces (SI il y en a un par défaut à la racine du 1er doc ET si $strictns est faux)
	unless ($strictns) {
		
		# on enregistre toujours la tei
		$xpath_ng->registerNs("tei", "http://www.tei-c.org/ns/1.0") ;
		
		# sur le premier document : test du defaut namespace
		if ($doc_i == 1) {
			print "(xmlns='http://www.tei-c.org/ns/1.0' will map to xmlns:tei)\n" ;
			my $root = $doc->documentElement();
			# prise en compte des namespaces sans :pfx (et déclarés sur la racine)
			$has_default_namespace_uri = $root->namespaceURI ;
			if ($has_default_namespace_uri) {
				warn "(xmlns='$has_default_namespace_uri' will map to xmlns:ns0)\n" ;
			}
		}
		# pour tous documents : rendre possible l'appel du namespace par défaut éventuel
		if ($has_default_namespace_uri) {
			$xpath_ng->registerNs('ns0', $has_default_namespace_uri) ;
		}
		# Explication :
		#  les expressions simples du type /section/item ne pouvaient pas matcher à 
		#  cause de la connerie des specifs xpath ne permettant pas d'ignorer un ns 
		#  Elles deviennent faisables sous la forme /ns0:section/ns0:item 
		#  parcequ'on enregistre le ns par défaut commme ns0)
		# cf. https://metacpan.org/pod/XML::LibXML::Node#findnodes
		# cf. aussi recherche sur "xpath default namespace"
		
		# idem pour tout namespace additionnel défini en paramètre de l'appel cl
		if ($ns_add) {
			my ($prefix, $uri) = split (/:/, $ns_add) ;
			$xpath_ng->registerNs($prefix, $uri) ;
		}
	}
	# ----------------------------------------------------------------------- -------
	
	# recherche XPATH renvoie chaque sous-élément intéressant
	my @refs = $xpath_ng->findnodes($start_elt) ;
	
	$total_matches += scalar(@refs) ;
	
	# compteur de refs interne au doc
	my $ref_j = 0 ;
	
	#### BOUCLE SUR LES REFS ####
	for my $ref (@refs) {
		$ref_j ++ ;
		my $ref_j_str = sprintf("%03d", $ref_j) ;
		
		# compteur défilant avec \r
		print STDERR "parsing doc $doc_i_str, match $ref_j_str\r" ;
		
		# STATS SUR LES ELEMENTS ###############
		
		if ($liste) {
			$rec_freq_hash = rec_xml_freq_flat({
				"xml_elt"=>$ref,
				"add_idx"=>$rec_freq_hash
				}) ;
		}
		else {
			$rec_freq_hash = rec_xml_freq_tree({
				"xml_elt"   => $ref,
				"add_idx"   => $rec_freq_hash,
				"ancestors" => []
				}) ;
		}
	}
}

warn "\n" ;  # pour finir la ligne du compteur

if ($total_matches == 0) {
	warn "XPATH : no match for '$start_elt'\n" ;
	if ($has_default_namespace_uri) {
		warn "        Perhaps it's because of default namespace?\n" ;
		warn "        Then try replacing /tag by /ns0:tag\n" ;
	}
}

### SORTIE ### ----------------------------------
if ($liste) { print_freq_flat($rec_freq_hash) ; }
else        { print_freq_tree($rec_freq_hash) ; }


################################################
#                    SUBS                      #
################################################

# décompte récursif d'éléments
# -----------------------------
# renvoie un idx plat de forme ; {"xml_elt_tag" -> count}
# use XML::Twig
sub rec_xml_freq_flat {
	my $params = shift ;
	my $xml_elt = $params->{'xml_elt'} ;   # XML::LibXML::Node
	my $cur_idx = $params->{'add_idx'} ;   # hashref {tag -> int}
	
	my $tag = $xml_elt->nodeName() ;
	
	
	# incrément local
	if (defined($cur_idx->{$tag})) {
		$cur_idx->{$tag} ++ ;
	}
	else {
		$cur_idx->{$tag} = 1
	}
	
	# lancement récursif
	if ($xml_elt->hasChildNodes()) {
		for my $kid ($xml_elt->childNodes()) {
			$cur_idx = rec_xml_freq_flat ({"xml_elt"=>$kid, "add_idx"=>$cur_idx}) ;
		}
	}
	return $cur_idx ;
}

# idem mais en sortant un idx hiérarchique
# ----------------------------------------
# idx { "xml_elt_tag" -> {"_freq" => count , "xml_subelt_tag" => recursion } }
sub rec_xml_freq_tree {
	my $params = shift ;
	my $node = $params->{'xml_elt'} ;     # XML::LibXML::Node
	my $cur_idx = $params->{'add_idx'} ;     # hashref récursif
	my $ancestors = $params->{'ancestors'} ; # arrayref [root,...,gd-pere,pere]
	
	# cf. description des types (valeur numérique) en fin de fichier
	my $test_type = $node->getType() ;
	
	# si ce n'est pas un noeud "element" ni document
	if ($test_type != 1 and $test_type != 9) {
		# on ne fait rien
		return($cur_idx) ;
	}
	# document entier ou elt normal => parcour récursif + décompte ds idx
	else {
		my $xml_elt = $node ;
		
		my $tag = $xml_elt->nodeName() ;
		
		#~ if ($tag =~ "#comment") {
			#~ die "\ntag = $tag\n" ;
		#~ }
		
		my $grouptag = $tag ;
		
		if ($DO_RECODAGE_TAGS) {
			my $file_format = $DO_RECODAGE_TAGS ;
			# recodages ad hoc dans le cas particulier d'un input NXML ou TEI
			$grouptag = tag_recodage($tag, $xml_elt, $file_format) ;
		}
		
		# terminaux PCDATA ignorés (n'apportent pas souvent une info supplémentaire)
		if ($grouptag eq "#text" || $grouptag eq "SKIP") {
			return $cur_idx ;
		}
		
		# ajout des attributs type et autres comme différenciateur
		my @attrs = $xml_elt->attributes() ;
		
		# on gardera les valeurs d'attributs @type, @unit et @level
		# et, si switch --moreattrs, les noms de tout autre attribut
		for my $attr (@attrs) {
			if (defined $attr) {
				my $attr_name = $attr->nodeName ;
				if ($attr_name =~ /type|unit|level/) {
					my $mon_type = $attr->value ;
					
					# ajout de l'attribut au tag recodé de groupement des décomptes
					$grouptag = $grouptag.'[@'.$attr_name.'="'.$mon_type.'"]' ;
				}
				elsif ($SHOW_MISC_ATTRS) {
					$grouptag = $grouptag.'[@'.$attr_name.'="???"]' ;
				}
			}
		}
		
		# pointeur (localiser le père dans l'arbre)
		my $subtree = $cur_idx ;
		for my $ancestor (@{$ancestors}) {
			$subtree = $subtree->{$ancestor} ;
		}
		# warn $subtree ;
		
		# incrément local
		if (defined($subtree->{$grouptag})) {
			$subtree->{$grouptag}->{"_freq"} ++ ;
		}
		else {
			$subtree->{$grouptag} = {} ;
			$subtree->{$grouptag}->{"_freq"} = 1 ;
		}
		
		# lancement récursif
		if ($xml_elt->hasChildNodes()) {
			push (@$ancestors, $grouptag) ;
			for my $kid ($xml_elt->childNodes()) {
	# 			warn "$grouptag 's kid no $k, ancestors = ".scalar(@$ancestors)."\n" ;
				$cur_idx = rec_xml_freq_tree (
					{"xml_elt"   => $kid,
					 "add_idx"   => $cur_idx,
					 "ancestors" => $ancestors}) ;
			}
			pop @$ancestors ;
		}
		return $cur_idx ;
	}
}

# Impression d'un index plat
# ---------------------------
sub print_freq_flat {
	my $h = shift ;
	for my $tag (sort { $h->{$b} <=> $h->{$a} } keys(%$h)) {
		print $tag."\t".$h->{$tag}."\n" ;
	}
}


# Impression d'un index hiérarchique
# ------------------------------------
# Parcourt récursivement un hash hiérarchique et imprime le niveau n+1
sub print_freq_tree {
	my $tree = shift ;
	my $prefix = shift || "" ;
	
	# Seul cas d'un print au niveau n
	if ($prefix eq "") {
		print "(xpath '$start_elt')\n" ;
	}
	
	# parmi les keys() on a des branches filles et des 
	# métadonnées (clés commençant par "_")
	# par ex: on traitera toujours "_freq" à part
	my @branch_keys = grep {$_ !~ /^_/} keys(%$tree) ;
	my $n_kids = scalar(@branch_keys) ;
	
	# Remarque : La stratégie de récursion est d'imprimer le niveau n+1
	#            (autrement dit la fonction ne fera rien au niveau des terminaux)
	if ($n_kids > 0) {
		# embranchements précédents (ancestraux)
		# deviennent "inactifs" à la ligne du dessous (chez les fils)
		$prefix =~ s/├/│/g ;     
		
		# idem pour profondeur en amont du père
		# devient invisible
		$prefix =~ s/─/ /g ;
		
		# embranchements "finis" à supprimer
 		$prefix =~ s/└/ /g ;
		
		my @ordered = () ;
		
		# tri alphabétique
		if ($ALPHA) {
			@ordered = sort { $a cmp $b } @branch_keys ;
		}
		# tri décroissant sur les freqs
		else {
			@ordered = sort { $tree->{$b}->{"_freq"} <=> $tree->{$a}->{"_freq"} } @branch_keys ;
		}

		$prefix .= " ├──" ;      # empilement d'une nouvelle fratrie
		
		my $k = 0 ;
		for my $branch (@ordered) {
			$k++ ;
			
			# marqueurs d'embranchement spécial pour le benjamin
			if ($k == $n_kids) {
				$prefix =~ s/├/└/;
			}

			print $prefix." ".$branch." ".$tree->{$branch}->{"_freq"}."\n";
			
			# appel récursif sur n+1 pour qu'il regarde s'il y a des n+2 à faire
			print_freq_tree($tree->{$branch}, $prefix)
		}
	}
}


# Sélectionne une info à loguer à l'intérieur de $@
# --------------------------------------------------
# On cherche l'info la plus pertinente parmi plusieurs
# lignes d'un log hérité en favorisant les lignes longues
# et les lignes vers la fin du log
sub errlog {
	my $at = shift || "=inco=" ;      # lignes d'erreur $@ héritées
	my $path = shift || "" ;          # nom du fichier
	my $off = shift || 8 ;            # offset en nb d'espaces
	
	my $to_replace = quotemeta($path) ;

	$at =~ s/$to_replace/<INFILE>/g ;
	
	return " "x$off."[$at]\n" ;
	
	my @errors = split(/\n/,$at) ;
	my $best_line = "" ;
	my $best_score = 0 ;
	my $i = 0 ;
	for my $line (@errors) {
		warn "orig >> $line\n" ;
	}
		#~ $i++ ;
		#~ my $test = $line ;
		#~ $test =~ s/\s+/ /g ;
		#~ 
		#~ # warn "--> $test\n" ;
		#~ my $score = log(length($test)+1) * sqrt($i) ;
		#~ # warn "$i score = $score\n" ;
		#~ if ($score >= $best_score) {
			#~ $best_score = $score ;
			#~ $best_line = $line ;
		#~ } 
	#~ }
	#~ return " "x$off."[$best_line]\n" ;   # message mis en forme pr warn
}


# recodages optionnels sur les noms d'<éléments>
# -----------------------------------------------
#   => décompte groupé = plusieurs noms d'éléments recodés vers un même nom
#   => décompte omis   = nom d'élément recodé vers SKIP
#  !!! le texte de remplacement ne doit pas commencer par "_"
sub tag_recodage {
	my $str = shift ;
	my $elt = shift ;
	my $format = shift ;
	
	if ($format eq "tei.xml") {
		for my $attr ($elt->attributes()) {
			if (defined $attr) {
				my $attr_name = $attr->nodeName ;
				if ($attr_name =~ /type|level/) {
					my $val = $attr->value ;
					# ajout de l'attribut recodé au tag recodé de groupement des décomptes
					$str .= "_\@$attr_name=".$val ;
				}
			}
		}
		return $str ;
	}
	elsif ($format eq "nxml") {
		
		# !!! >SKIP< veut dire qu'on ne va pas du tout *dans* l'élément
		$str =~ s/^citation$/*citation/ ;
		$str =~ s/^element-citation$/*citation/ ;
		$str =~ s/^mixed-citation$/*citation/ ;
		$str =~ s/^italic$/(text-style)/ ;
		$str =~ s/^bold$/(text-style)/ ;     
		$str =~ s/^sup$/(text-style)/ ;       # superscript
		$str =~ s/^sub$/(text-style)/ ;       # subscript
		$str =~ s/^sc$/(text-style)/ ;        # small caps
		
		# on garde la valeur des attributs finissant par *type
		for my $attr ($elt->attributes()) {
			if (defined $attr) {
				my $attr_name = $attr->nodeName ;
				if ($attr_name =~ /type$/) {
					my $val = $attr->value ;
					# recodage des publication-type plus rares (patent, inbook, report, etc) 
					#          sur les types plus fréquents (journal, book, etc)
					# cf. corpus/eval/PMC_sample/analyse_nxml/arbres/sous_arbres_comparés/citation_divers.tree
					$val =~ s/^patent$/book/ ;
					$val =~ s/^report$/book/ ;
					$val =~ s/^msds$/book/ ;
					$val =~ s/^computer-program$/book/ ;
					$val =~ s/^commun$/book/ ;
					$val =~ s/^thesis$/book/ ;
					$val =~ s/^inbook$/journal/ ;
					$val =~ s/^discussion$/journal/ ;
					$val =~ s/^gov$/journal/ ;
					$val =~ s/^undeclared$/journal/ ;
					$val =~ s/^web$/webpage/ ;
					$val =~ s/^weblink$/webpage/ ;
					$val =~ s/^other-ref$/webpage/ ;
					
					# ajout de l'attribut recodé au tag recodé de groupement des décomptes
					$str .= "_\@*type=".$val ;
					
					# Finalement le reliquat de la citation d'origine parfois
					# présent en plus de l'élément <*citation> normal mais peu
					# utile (chaîne non-structurée) peut être ignoré
					$str = "SKIP" if ($val == "display-unstructured") ;
				}
			}
		}
		return $str ;
	}
	else {
		warn "pas de règles de recodage pour $format";
		return $str ;
	}
}

# renvoie le message d'aide
# -------------------------
sub HELP_MESSAGE {
	print <<EOT;
	
------------------------------------------------------------
|    Lecture fichiers XML et décomptes hierarchiques       |
|                          ---                             |
|   Effectif total (tous fichiers confondus) des <tags>    |
|      avec décompte récursif dans les sous-éléments       |
|----------------------------------------------------------|
| Exemple de sortie:                                       |
| ==================                                       |
|    root                                                  |
|     └── citation 15                                      |
|         ├── person-group 14                              |
|         │   └── name 72                                  |
|         │       ├── given-names 72                       |
|         │       └── surname 72                           |
|         ├── year 14                                      |
|         ├── source 12                                    |
|         ├── volume 12                                    |
|         ├── fpage 12                                     |
|         └── lpage 11                                     |
|                                                          |
| Usage                                                    |
| =====                                                    |
|   xml_tag-stats.pl file.xml                              |
|   xml_tag-stats.pl file.xml -x "//subelt[\@foo='bar']"    |
|   xml_tag-stats.pl -d path/xmldir/                       |
|   xml_tag-stats.pl -d xmldir -x "//subelt[\@foo='bar']"   |
|                                                          |
| Options et arguments                                     |
| ====================                                     |
|   -h --help         afficher cet écran                   |
|                                                          |
|   -d --dir dossier  répertoire à lire    [défault: .]    |
|   -e --ext "nxml"   extensions à lire    [défault: xml]  |
|   -g --glob "iop*"  glob fichiers à lire [défault: ""]   |
|                                                          |
|   -x --xpath "/article/back/ref-list"    [défault: /]    | 
|                     selecteur XPATH d'un ou plusieurs    | 
|                     éléments dans lesquels on va compter |
|                     (avancé: écrire 'ns0:elt' au lieu de |
|                      'elt' s'il y a un namespace par déf)|
|                                                          |
|   -s --strictns     xpath strict sur le defaut namespace |
|                     (ne pas l'enregistrer comme ns0)     |
|                                                          |
|   -n --nsadd        ajouter une declaration namespace    |
|                     eg "tei:http://www.tei-c.org/ns/1.0" |
|                                                          |
|   -k --killents     ignorer toute entité XML             |
|                     (substitées par __ENT__ avant parse) |
|                                                          |
|   -m --moreattrs    afficher ts les attributs (sans val) |
|                                                          |
|   -l --liste        sortie alternative : elt    freq     |
|                     (liste simple au lieu d'un arbre)    |
|----------------------------------------------------------|
|  © 2014 Inist-CNRS (ISTEX)  romain.loth at inist dot fr  |
------------------------------------------------------------
EOT
	exit 0 ;
}


# PI:
# Codes numériques des types de node renvoyés par $xelt->getType()
# source :  libxml2 tree.h xmlElementType
# -----------------------------------------------------------------
#Enum xmlElementType {
#    XML_ELEMENT_NODE = 1
#    XML_ATTRIBUTE_NODE = 2
#    XML_TEXT_NODE = 3
#    XML_CDATA_SECTION_NODE = 4
#    XML_ENTITY_REF_NODE = 5
#    XML_ENTITY_NODE = 6
#    XML_PI_NODE = 7
#    XML_COMMENT_NODE = 8
#    XML_DOCUMENT_NODE = 9
#    XML_DOCUMENT_TYPE_NODE = 10
#    XML_DOCUMENT_FRAG_NODE = 11
#    XML_NOTATION_NODE = 12
#    XML_HTML_DOCUMENT_NODE = 13
#    XML_DTD_NODE = 14
#    XML_ELEMENT_DECL = 15
#    XML_ATTRIBUTE_DECL = 16
#    XML_ENTITY_DECL = 17
#    XML_NAMESPACE_DECL = 18
#    XML_XINCLUDE_START = 19
#    XML_XINCLUDE_END = 20
#    XML_DOCB_DOCUMENT_NODE = 21
#}
