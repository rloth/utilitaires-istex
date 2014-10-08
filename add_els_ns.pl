#! /usr/bin/perl

# add_els_ns.pl : diagnostic et ajout de namespaces 
#                 pour les fichiers XML elsevier
# --------------------------------------------------------------------------
#  message /help/ en fin de ce fichier       version: 0.1 (03/10/2014)
#  copyright 2014 INIST-CNRS      contact: romain dot loth at inist dot fr
# --------------------------------------------------------------------------

use warnings ;
use strict ;
use Data::Dumper ;

# flag interne
my $debug = 0 ;

# namespaces "ajoutables" : liste de référence
# ---------------------------------------------
my %ADDABLE_NS = (
	'ja'    => 'http://www.elsevier.com/xml/ja/dtd' ,
	'ce'    => 'http://www.elsevier.com/xml/common/dtd' ,
	'sb'    => 'http://www.elsevier.com/xml/common/struct-bib/dtd' ,
	'xlink' => 'http://www.w3.org/1999/xlink' ,
	'sa'    => 'http://www.elsevier.com/xml/common/struct-aff/dtd' ,
	'mml'   => 'http://www.w3.org/1998/Math/MathML' ,
	'tb'    => 'http://www.elsevier.com/xml/common/table/dtd' ,
	'cals'  => 'http://www.elsevier.com/xml/common/cals/dtd' ,
	'xocs'  => 'http://www.elsevier.com/xml/xocs/dtd' ,
	'xs'    => 'http://www.w3.org/2001/XMLSchema' ,
	'xsi'   => 'http://www.w3.org/2001/XMLSchema-instance',
	) ;

# lecture XML en entrée
# ----------------------
# unique argument : chemin fichier en entrée
my $filepath = $ARGV[0] || die "ERR: veuillez fournir un nom de fichier en entrée\n" ;

# slurp FILE => $content
my $content = "" ;
open (FILE, "< $filepath") || die "ERR: impossible d'ouvrir '$filepath'\n" ;
while (<FILE>) { $content .= $_ ; }
close (FILE) ;

# namespaces réellement utilisés
# -------------------------------
# hash "checkliste" des ns utilisés
my %needed_ns = () ;

# match de tous les ns en présence dans le doc
# sur forme /<tartampion:/
my @match_ns = ($content =~ m/<([^\/:> ]+):/g) ;

# report dans le hash => unicité
for my $ns (@match_ns) {
	$needed_ns{$ns} = "present" ;
}

# namespaces actuellement déclarés
# ---------------------------------
# liste des ns déclarés
my @declared_ns = () ;

# capture de la déclaration root
$content =~ m/(<(?:converted-)?article[^>]+>)/ ;

my $root_tag = $1 || die "ERR: je ne trouve pas de balise root du type <article...> ou <converted-article...> dans le document '$filepath'\n" ;

# Exemple de match :
# <article xmlns="http://www.elsevier.com/xml/ja/dtd" version="5.1" xmlns:ce="http://www.elsevier.com/xml/common/dtd" xmlns:sb="http://www.elsevier.com/xml/common/struct-bib/dtd" xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="en" docsubtype="fla">

@declared_ns = ($root_tag =~ /xmlns:([^=]+)/g) ;

# différence : (utilisés) privé de (déclarés)
# --------------------------------------------
for my $ns (@declared_ns) {
	delete $needed_ns{$ns} || next ;
}

my @remaining_ns = keys(%needed_ns) ;

if ($debug) {
	warn "à ajouter pour doc '$filepath':\n" ;
	warn Dumper \@remaining_ns ;
}

# est-ce qu'il reste quelquechose ?
# ---------------------------------
if (scalar(@remaining_ns)) {
	# construction nouvelle balise
	# -----------------------------
	
	# chaîne avec déclarations à ajouter
	my $insert_str = "" ;
	for my $ns (@remaining_ns) {
		my $uri = $ADDABLE_NS{$ns} ;
		my $declaration_str = 'xmlns:'.$ns.'="'.$uri.'"' ;
		$insert_str .= ' '.$declaration_str ;
	}
	
	# création de la nouvelle balise root
	my $new_root_tag = $root_tag ;
	
	# les déclarations sont ajoutées à la toute fin par substitution du chevron fermant
	$new_root_tag =~ s/>$/${insert_str}>/ ;
	
	warn $new_root_tag if ($debug) ;
	
	# remplacement balise root par la nouvelle balise
	# ------------------------------------------------
	
	# regexp-isation de la chaine à remplacer
	my $regexp_old_root_tag = quotemeta($root_tag) ;
	
	# remplacement dans le contenu du fichier
	$content =~ s/$regexp_old_root_tag/$new_root_tag/ ;
}

# SORTIE : 
#  - le doc est resté tel quel si la différence de ns était vide
#  - sinon on lui a substitué sont tag 'root' par un semblable avec
#    insertion des déclarations ns manquantes
print $content ;
