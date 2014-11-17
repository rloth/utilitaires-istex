#! /usr/bin/perl
# ---------------------------------------------------------------
#  corrige_revues_oup.pl  2014-09  rloth  [istex-enrich::idxcsv] 
# ---------------------------------------------------------------
# objectif:
# ce script remplace le point virgule qui empêche les cuts -d';' 
# par la chaîne de caractère "__PVIRG__"
# ---------------------------------------------------------------
# détails:
# il les matche en position chemin /data en début de ligne
# ex: ^/data/oup/<<MATCH>>/...
# ---------------------------------------------------------------
# antidote:
# ==> on a tout intérêt à stocker la suite en tabulé (aka tsv)
# ==>           et à re-remplacer comme cela :
# ==>                  s/__PVIRG__/;/
# ---------------------------------------------------------------

use warnings ;
use strict ; 

##########################  MAIN  #################################

# les 24 revues OUP ayant un point-virgule
# (on ignorera les 155 autres inoffensives)
my @revuescoup = (
   "African Affairs, 1901-2010 (v1-v109; vVI-vXXXVIII)" ,
   "British Journal for the Philosophy of Science, The, 1950-2010 (v1-v61; vI-vXVI)" ,
   "Cambridge Quarterly, The, 1965-2010 (v30-v39; vI-vXXVII)" ,
   "Early Music , 1973-2010 (v1-v38; vXIX-vXXXI)" ,
   "ELT Journal , 1946-2010 (v1-v64; vII-vXXXV)" ,
   "Essays in Criticism , 1951-2010 (v50-v60; vI-vXXXX)" ,
   "Forum for Modern Language Studies , 1965-2010 (v37-v46; vI-vXXXVI)" ,
   "French Studies , 1947-2010 (v1-v64; vII-vXXXVIII)" ,
   "ICES Journal of Marine Science, 1903-2010 (v1-v67; vs1-vs91)" ,
   "Journal of Semitic Studies , 1956-2010 (v1-v55; vXI-XXXVIII)" ,
   "Journal of the History of Medicine and Allied Sciences , 1946-2010 (v38-v65; vII-vXXXVII)" ,
   "Journal of the London Mathematical Society, 1926-2010 (v49-v82; vs1-1-s2-48)" ,
   "Journal of Theological Studies , 1899-2010 (v34-61; vos-I-os-XXXVIII; vI-vXXXIII)" ,
   "Library, The, 1889-2010 (v1-v11; s1-s6; TBS-1-TBS-16)" ,
   "Mind , 1876-2010 (v101-v119; os-1-os-XVI; II-XXXVIII)" ,
   "Music and Letters , 1920-2010 (v41-91; vI-vXXXVIII)" ,
   "Oxford Economic Papers , 1938-2010 (v1-v62; os-1-os-8)" ,
   "Parliamentary Affairs , 1947-2010 (v19-v63; vI-vXXXV)" ,
   "Philosophia Mathematica , 1964-2010 (v1-v18; vs1-1-s2-6)" ,
   "Proceedings of the London Mathematical Society, 1865-2010 (v74-v101; s1-s3)" ,
   "QJM An International Journal of Medicine, 1907-2010 (v1-v103; os-1-os24)" ,
   "Quarterly Journal of Mathematics , 1930-2010 (v1-v61; vos-1-vos-20)" ,
   "Review of English Studies, 1925-2010 (v49-v61; os-I-os-XXIV; I-XXXVIII)" ,
   "Rheumatology , 1952-2010 (v1-v49; vIII-vXXXIV)" ,
   "Year's Work in English Studies, The , 1919-2010 (v48-v89; vII-vXXXVIII)"
) ;

my $regexp = join('|', map {quotemeta($_)} @revuescoup) ;

warn "regexp: $regexp \n";

# STDIN
while (<>) {
	# ici à corriger
	if (m!^/data/oup/($regexp)!) {
		# alors on enlève le 1er cara ';'
		$_ =~ s/;/__PVIRG__/ ;
		
		# corrigés > STDOUT
		print $_ ;
	}
	else { 
		# inoffensifs > STDOUT
		print $_ ; 
	}
}
