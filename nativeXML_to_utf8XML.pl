#! /usr/bin/perl

# nativeXML_to_utf8XML.pl : conversion depuis l'encodage déclaré XML 
#                           vers UTF-8 (avec remplacement déclaration)
# --------------------------------------------------------------------------
#  message /help/ en fin de ce fichier       version: 0.1 (27/11/2014)
#  copyright 2014 INIST-CNRS      contact: romain dot loth at inist dot fr
# --------------------------------------------------------------------------

use warnings ;
use strict ;

# check if we got iconv
# ----------------------
unless (qx/which iconv/) {
	die "ERR: nativeXML_to_utf8XML demande que vous installiez 'iconv'\n"
}

my $arg = shift ;

if ($arg =~ /^--?h(?:elp)?$/) {
	HELP_MESSAGE() ;
	exit ;
}

# slurp XML file
# ---------------
my $file_path = $arg 
                 || die "Veuillez indiquer le nom du fichier d'entrée\n" ;


open(XFILE, "< $file_path")
 || die "Le chemin '$file_path' ne pointe sur rien de lisible\n" ;

my @lines = <XFILE> ;

close(XFILE) ;

# extract XML encoding declaration
# ---------------------------------
my $declared_encoding = undef ;
my $i = 0 ;

my $declaration_lineidx = 0 ;

while (not defined $declared_encoding) {
	my $line = $lines[$i] ;
	
	# on cherche seulement un bout de l'entête
	if ($line =~ m/<?xml[^>]+encoding="([-A-Za-z0-9]+)"/) {
		$declared_encoding = $1 ;
		$declaration_lineidx = $i ;
		# on a fini
		last ;
	}
	
	# inutile de parcourir tout le fichier
	last if ((not defined $line) or ($. > 20));
	
	$i++ ;
}

warn "Trouvé $declared_encoding à la ligne $declaration_lineidx\n" ;


# convert & replace declaration if needed, then print to STDOUT
# -------------------------------------------------------------
# si c'est déjà utf-8 il n'y a rien à faire
if ($declared_encoding =~ m/UTF-8/i){
	# OUTPUT
	for my $l (@lines) { print $l } ;
}
elsif ($declared_encoding =~ m/^(?:^[A-Z]{2}-)?ASCII$/i) {
	warn "ASCII for $file_path ;)" ;
	# ASCII est un sous-ensemble d'UTF-8
	$lines[$declaration_lineidx] =~ s/$declared_encoding/UTF-8/ ;
	# OUTPUT
	for my $l (@lines) { print $l } ;
}
else {
	# on ne va plus utiliser le @lines précédent (enco incertain)
	@lines = () ;
	# appel à iconv
	@lines = qx/iconv -f $declared_encoding -t utf-8 $file_path/ ;
	
	# replacement of declaration & OUTPUT
	for my $l (@lines) {
		if ($l =~ m/<?xml[^>]+encoding="$declared_encoding"/) {
			$l =~ s/encoding="$declared_encoding"/encoding="UTF-8"/ ;
		}
		print $l ;
	}
}

# voilà !


sub HELP_MESSAGE {
	print <<EOT;
--------------------------------------------------
         Conversion d'un XML vers UTF-8 
           + remplacement déclaration
--------------------------------------------------
 Usage:
  nativeXML_to_utf8XML.pl fichier.xml 
                            > fichier.utf-8.xml

 Options:
  -h     affiche cet écran d'aide

 Remarques: 
  1) Ce script utilise iconv en interne.
  2) La déclaration <?xml..encoding="bidule"..?>  
        deviendra : <?xml..encoding="UTF-8"..?>
--------------------------------------------------
 © 2014 INIST-CNRS    romain.loth at inist dot fr 
--------------------------------------------------
EOT
	exit 0 ;
}


