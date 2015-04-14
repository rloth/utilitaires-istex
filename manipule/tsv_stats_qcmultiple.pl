#! /usr/bin/perl
# --------------------------
# multiple -f 2 -x "3,4" < abcd.tsv
#   [istex-enrich:stats] 
# --------------------------
# (c) CNRS-INIST   2014-10  
# romain.loth @ inist . fr 
# --------------------------
# objectif:
#   sortir des stats sur
#   attributs multiples
#   d'une colonne selon
#   attributs classants
#   d'autres colonnes
# --------------------------
# détails:
#   les attributs recouvrants
#   à compter sont typiquement
#   des catégories thématiques
#   les attributs à croiser
#   peuvent être des classes 
#   sur un ou plusieurs plans
#   de catégories (type de doc,
#   époque de publi, etc)
# --------------------------

# usage
# shuf slim_et_themes.tsv | head -n 150 | multiple.pl -f 7 -x 5

use strict ;
use warnings ;
use Getopt::Long ;
use Data::Dumper ;

# --------- INPUT ---------- (TABULÉ, sur STDIN)

# Restoration     \t  "Chemistry/Art"            \t  "av.1960"  \t  en
# Aérobidule      \t  "Aero. Eng."               \t  "1990-99"  \t  fr
# Alchemy_Reviews \t  "Mining/Chemistry/Truc"    \t  "1960-89"  \t  en
# Jetlab_News     \t  "Spatial Eng./Aero. Eng."  \t  "1990-99"  \t  en

# ^^^^^^^^^^^^^^^     ^^^^^^^^^^^^^^^^^^^^^^^      ^^^^^^^^^^^      ^^
#   colonne 1             colonne -f 2                 cols -x 3,4 
#  id ou label        -> ATTRS MULTIPLES <-         données à croiser
#


# -------- OPTIONS ---------

# -f  --field 3       champ (int) qui contient les attributs multiples
my $the_field = undef ;

# -x  --xtabs 4,2,1   liste de champs (int[]) catégories de croisement
my $xtabs = undef ;

GetOptions( "help"    => \&HELP_MESSAGE,
			"field:i" => \$the_field,         # obligé
			"xtabs:s" => \$xtabs,             # optionnel
			) ;

# option à changer à la main
my $quote = '"' ;

die "veuillez fournir la colonne contenant les thématiques" unless (defined ($the_field)) ;

#~ die "$the_field" ;
# -------- OUTPUT: ---------

#                   [av.1960]   [1960-89]   [1990-99]
#       Mining          0           1          0
#   Aero. Eng.          0           0          2
# Spatial Eng.          0           0          1
#    Chemistry          1           1          0
#         Truc          0           1          0
#          Art          1           0          0

#                      en          fr
#       Mining          1           0
#   Aero. Eng.          1           1
# Spatial Eng.          1           0
#    Chemistry          2           0
#         Truc          1           0
#          Art          1           0

#                      TOT
#       Mining          1
#   Aero. Eng.          2
# Spatial Eng.          1
#    Chemistry          2
#         Truc          1
#          Art          1

# --------------------------
# ---------- MAIN ----------
# --------------------------

# initialisation des stats pour chaque table à sortir
my %aggs = () ;

# il y a au moins toujours les totaux à sortir
$aggs{'TOTAUX'} = {} ;

# initialisations complémentaires s'il y a des tables croisées à faire
my @xtabs = () ;
if (defined $xtabs) {
	my @nos = split(',',$xtabs) ;
	for my $no (@nos) {
		if ($no =~ /^\d+$/) {
			# => table pour les boucles de travail
			push(@xtabs, $no) ;
			# => stats pour les décomptes à sortir
			$aggs{"Table par facette n° ".$no} = {} ;
		}
		else {
			die "l'argument -x ou --xtabs prend une liste d'entiers séparés par des virgules (indice des colonnes de croisement)\n" ;
		}
	}
}

# pour logging des stats sur STDERR
my $nb_answers = 0 ;
my $nb_lignes = 0 ;

while (<>) {
	chomp ; 
	my @input_table_line_vals = split(/\t/,$_) ;
	
	my $ncol = scalar(@input_table_line_vals) ;
	
	die "il n'y a que $ncol colonnes dans cette table donc je ne peux pas prendre le champ ".($the_field)."\n" if ($the_field-1 > $ncol) ;
	
	my $str = $input_table_line_vals[$the_field-1] ;
	
	$str =~ s/^${quote}// ;
	$str =~ s/${quote}$// ;
	
	# next if ($str =~ /___NA___/) ;
	
	#~ warn Dumper $str ;
	
	my @cats_list = split(/\//,$str) ;
	
	#~ die Dumper \@cats_list ;
	
	$nb_answers += scalar(@cats_list) ;
	
	
	for my $the_cat (@cats_list) {
		#~ warn $the_cat ;
		
		# incrément décomptes pour table des TOTAUX
		$aggs{'TOTAUX'}->{$the_cat} ++ ;
		
		# et si nécessaire, incréments décomptes pour tables croisées
		if (defined $xtabs) {
			for my $xcol (@xtabs) {
				# valeur de la facette croisée
				my $xval = $input_table_line_vals[$xcol-1] ;
				$xval =~ s/^${quote}// ;
				$xval =~ s/${quote}$// ;
				$aggs{"Table par facette n° ".$xcol}->{$xval}->{$the_cat} ++ ;
			}
		}
	}
}

# récap sur le champ à réponse multiples :
# ------------------------------------------
# (pour logging: le nb de réponses moyen du champ QCM)
$nb_lignes = $. ;
warn "=================================\n" ;
warn "nombre de lignes :            $nb_lignes \n" ;
warn "nombre de catégories :        $nb_answers \n" ;
warn "=================================\n\n" ;

# liste triée des cats => lignes des tables stats en sortie
my @klignes = sort(keys($aggs{'TOTAUX'})) ;


# impression headers de colonnes et si nécessaire préparation
# récap sur les clés obtenues pour chaque tableau croisé complémentaire

print "CATEGORIE WOS\tTOTAL OCCURRENCES" ;

# hash de listes canoniques de colonnes
my %facetcols = () ;

if (defined $xtabs) {
	for my $facetno (@xtabs) {
		my $xstats = $aggs{"Table par facette n° ".$facetno} ;
		
		
		my @cols = sort(keys(%$xstats)) ;
		
		# stockage canonique
		$facetcols{$facetno} = \@cols ;
		
		# impression headers supplémentaires
		for my $col (@cols) {
			print "\t".$col ;
		}
	}
}

# fin ligne HEADER
print "\n" ;

# SORTIE DES TABLES
for my $cat (@klignes) {
	
	# ligne à finir (pas de "\n")
	print $cat."\t".$aggs{'TOTAUX'}->{$cat} ;
	
	
	if (defined $xtabs) {
		for my $facetno (@xtabs) {
			my @cols = @{$facetcols{$facetno}} ;
			
			# impression stats supplémentaires
			for my $col (@cols) {
				my $count = $aggs{"Table par facette n° ".$facetno}->{$col}->{$cat} 
				     || 0 ;
				print "\t${count}" ;
			}
		}
	}

	# fin de ligne
	print "\n" ;
}


# renvoie le message d'aide
sub HELP_MESSAGE {
	print <<EOT;
----------------------------------------------------------------
|         Stats croisées sur question à choix multiples        |
|--------------------------------------------------------------|
| Usage                                                        |
| =====                                                        |
|  multiple -f 2 -x "3" < abcd.tsv                             |
|                                                              |
| Options et arguments                                         |
| ====================                                         |
|  -f --field 2           indice du champ contenant les        |
|                         réponses multi                       |
|  -x --xtabs "3,4"       indices du ou des champ(s) à croiser |
|                         (optionnels)                         |
|  -h --help              message d'aide                       |
|                                                              |
|                                                              |
| Entrée "base" : sur STDIN grande tables TSV                  |
|                                                              |
|> revue1 \\t  "Aero. Eng."              \\t "[1990-99]" \\t fr  <|
|> revue2 \\t  "Mining/Truc"             \\t "[1960-89]" \\t en  <|
|> revue3 \\t  "Spatial Eng./Aero. Eng." \\t "[1990-99]" \\t en  <|
|                                                              |
|              ^^^^^^^^^^^^^^^^^^^^^^^^    ^^^^^^^^^           |
|                champ étudié -f 2         champ -x 3          |
|               (sép. interne: '/')         à croiser          |
|                                                              |
| Sortie : stats tabulées                                      |
|          (en ligne les modalités du champ -f)                |
|          (en colonne celle du ou des champ(s) -x)            |
|                                                              |
|>                     [av.1960]   [1960-89]   [1990-99]      <|
|>         Mining          0           1          0           <|
|>     Aero. Eng.          0           0          2           <|
|>   Spatial Eng.          0           0          1           <|
|>           Truc          0           1          0           <|
|                                                              |
|------------------------------------- ------------------------|
|  © 2014 Inist-CNRS (ISTEX)      romain.loth at inist dot fr  |
----------------------------------------------------------------
EOT
	exit 0 ;
}


