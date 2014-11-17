#! /usr/bin/perl

# Ce script est un filtre simple sur des lignes de champs tabulées
# il garde uniquement les lignes dont un des champs contenant des int
# correspond à un intervalle spécifié [min,max].

use warnings ;
use strict ;
use Getopt::Long ;

# -------- OPTIONS ---------

# -f  --field 6       colonne du champ (int) qui contient l'int à filtrer
my $the_field = undef ;

# -min n et -max N  : bornes inf et sup de l'intervalle
my $min = 0 ;
my $max = 1000000000 ;

GetOptions( "field:i" => \$the_field,      # obligé
			"min:i"   => \$min,            # optionnel
			"max:i"   => \$max             # optionnel
			) ;

unless (defined ($the_field)) {
	die "Exemple d'usage:\ngettsv_int_range.pl -f 6 -min 62 -max 1000000 < big.tsv\n\nFiltre le tableau tsv sur la valeur d'un champ int (dans la colonne f) en précisant des bornes [min,max]\n" ;
}


while (<>) {
	my @fields = split (/\t/, $_) ;
	my $nbc = $fields[5] ;
	if (($min <= $nbc) && ($nbc <= $max)) {
		print $_ ;
	}
}
