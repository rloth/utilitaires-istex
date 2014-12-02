#! /usr/bin/perl
# --------------------------
# remplace_champ.pl -f 2 -e erratas.tsv < big_table
#   [istex-enrich:stats] 
# --------------------------
# (c) CNRS-INIST   2014-11
# romain.loth @ inist . fr
# --------------------------
# Usage :
# remplace_champ.pl --field 4 --errata "corrections.tsv" < TABLE_A_CORRIGER.tsv

# Remarque :
# on part du principe que l'identifiant est le champ 1
# (il permet le report de la correction)

use warnings ;
use strict ;
use Getopt::Long ;
use Data::Dumper ;

# -------- OPTIONS ---------

# champ (int) qui contient les valeurs à remplacer
# -f  --field 3
my $the_field = undef ;

# table à 2 colonnes ID champ_corrigé
# -e --errata corrections.tsv    
my $errata_file = undef ;

GetOptions( "help"    => \&HELP_MESSAGE,
			"field:i" => \$the_field,         # obligé
			"errata:s" => \$errata_file,      # obligé
			) ;

die "j'ai besoin d'un int >=1 indiquant le champ à corriger, via option -f 3 pour champ 3\n" unless (defined($the_field) && ($the_field >=1)) ;
die "j'ai besoin d'un chemin vers table des corrections à 2 colonnes : ID champ_corrigé via option --errata table_des_corrections.tsv\n" unless (defined($errata_file)) ;

$the_field = $the_field - 1 ;

# --------- MAIN -----------

# annuaire à part de {(chemins => champ_corrigé)} pour report dans la table à corriger
my %corrections = () ;

open (ERRATA, "< $errata_file") || die "Je ne trouve pas le document des corrections '$errata_file'\n" ;

while (<ERRATA>) {
	chomp ;
	my ($id,$replacement) = split(/\t/, $_) ;
	$corrections{$id} = $replacement ;
}
close ERRATA ;

while(<>) {
	chomp ;
	# INPUT TSV
	my @fields = split(/\t/, $_) ;
	my $n = scalar(@fields) ;
	
	die "il n'y a que $n colonnes dans cette table donc je ne peux pas prendre le champ ".($the_field+1)."\n" if ($the_field > $n-1) ;
	
	# on part du principe que l'identifiant est le champ 1
	my $id = $fields[0] ;
	
	# ssi ID fait partie des lignes à corriger
	# -----------------------------------------
	if (exists $corrections{$id}) {
		my $replacement = $corrections{$id} ;
		
		# l'indice [1..n] à déjà été ramené sur [0..n-1]
		my $original = $fields[$the_field] ;
		
		warn "s/$original/$replacement/\n" ;
		
		# cas premier champ est à remplacer
		if ($the_field == 0) {
			# on préserve les champs situés après celui qui change
			# et on reconstitue la ligne
			print $replacement."\t".join("\t",@fields[1..$n-1])."\n" ;
		}
		# cas dernier champ
		elsif ($the_field == $n-1) {
			# on préserve les champs situés avant celui qui change
			# et on reconstitue la ligne
			print join("\t",@fields[0..$n-2])."\t".$replacement."\n" ;
		}
		# cas normal : champ quelquepart au milieu
		else {
			# on préserve les champs situés avant et après celui qui change
			my @before = @fields[0..$the_field-1] ;
			my @after = @fields[$the_field+1..$n-1] ;
		
			# et on reconstitue la ligne avec le remplacement
			print join("\t",@before)."\t".$replacement."\t".join("\t",@after)."\n" ;
		}
	}
	# sinon rien à faire on renvoie la ligne inchangée
	else {
		print $_."\n"
	}
}

# renvoie le message d'aide
sub HELP_MESSAGE {
	print <<EOT;
--------------------------------------------------------------
|         Remplacement d'un champ dans base tabulée          |
|           d'après une liste "errata" avec IDs              |
|------------------------------------------------------------|
| Usage                                                      |
| =====                                                      |
|  remplace_champ.pl -f 2 -e qqs_corrections.tsv < base.tsv  |
|                                                            |
| Options et arguments                                       |
| ====================                                       |
|  -f --field 3                 indice du champ à remplacer  |
|  -e --errata corrections.tsv  table 2 col: ID champcorrigé |
|  -h --help                    ce message d'aide            |
|                                                            |
|                                                            |
| Entrée "base" : sur STDIN grande table avec ID en col 1    |
|                 (séparateur attendu = tab)                 |
|                                                            |
| Entrée "errata" : table à 2 colonnes ID et champ_corrigé   |
|                   (séparateur attendu = tab)               |
|                                                            |
| Sortie: copie de la base avec juste le champ voulu modifié |
|         selon les lignes signalées dans errata             |
|                                                            |
|------------------------------------- ----------------------|
|  © 2014 Inist-CNRS (ISTEX)    romain.loth at inist dot fr  |
--------------------------------------------------------------
EOT
	exit 0 ;
}
