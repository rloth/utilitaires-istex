#! /usr/bin/perl
use warnings ;
use strict ;
use Data::Dumper ;

# ----------------------------------------------------------------------
# LECTURE TABLE DE PASSAGE pour avoir les cats sous la main

my $homedir = "/home/loth/istex/domaines" ;

# table => "annuaire" de report des thèmes
open (PASSAGE, "< $homedir/4_RESULTATS_GROUPES/passage-issn_catswos-pour_xml.tsv")
 || die ("je ne trouve pas l'extrait de cumul-revues passage-issn_catswos.tsv") ;

my %mes_reports = () ;

while (<PASSAGE>) {
	chomp ;
	my ($issn, $cats) = split(/\t/, $_) ;
	my @cats = split(/\//, $cats) ;
	
	# arrayref
	$mes_reports{$issn} = \@cats ;
}

close PASSAGE ;

#~ warn Dumper \%mes_reports ;

# ----------------------------------------------------------------------
# ENTETE GLOBALE
print<<FINHEADER ;
<?xml version="1.0"?>
<teiCorpus xmlns="http://www.tei-c.org/ns/1.0" xmlns:xml="http://www.w3.org/XML/1998/namespace" xml:id="enrich_domaines_2014-11">
 <teiHeader>
  <fileDesc>
   <titleStmt>
    <title>Liste de domaines thématiques des documents ISTEX</title>
    <respStmt xml:id="ISTEX-RD">
     <resp>Documents catégorisés en disciplines WOS (via leur ISSN)</resp>
     <name>E. Morale, G. Guibon et R. Loth</name>
    </respStmt>
    <extent>6308071 docs XML (lots Elsevier et Nature)</extent>
   </titleStmt>
  </fileDesc>
  <revisionDesc>
   <change who="#ISTEX-RD" when="2014-11">version unique</change>
  </revisionDesc>
 </teiHeader>
FINHEADER



# ----------------------------------------------------------------------
# LECTURE D'UNE LISTE D'ISSN SUR STDIN
# et sortie dans le même ordre d'une liste avec les cats de ch. ISSN
while (<>) {
	chomp ;
	my ($path, $id, $lotissna) = split(/\t/, $_) ;
	
	$lotissna =~ m!^...:/([^/]*)/$! ;
	my $issna = $1 ;
	#~ warn $issna ;
	# /^([0-9]{4}-[0-9X]{4})$/
	if (length($issna)) {
		# pointeur sur liste de cats
		my $cats = $mes_reports{$issna} || undef ;
		
		if (defined($cats)) {
			my $xml_str = id_n_cats_to_xml_tei_entry($id, $cats) ;
			# SORTIE NORMALE
			print $xml_str ;
		}
		else {
			warn "ligne $. '$issna' issnannoncé2wos n'a pas de correspondance" ;
			next ;
		}
	}
	# pour elsevier on sait retrouver l'issn
	elsif ($path =~ m!^/data/elsevier/raw/[ISTY0-9]+/([0-9]{4})([0-9X]{4})/!) {
		$issna = $1."-".$2 ;
		# pointeur sur liste de cats
		my $cats = $mes_reports{$issna} || undef ;
		
		if (defined($cats)) {
			my $xml_str = id_n_cats_to_xml_tei_entry($id, $cats) ;
			# SORTIE NORMALE
			print $xml_str ;
		}
		else {
			warn "ligne $. '$issna' issntrouvé2wos n'a pas de correspondance" ;
			next ;
		}
	# sinon on n'a vraiment pas l'issn
	}
	else {
		# SORTIE ERREURS
		warn "ligne $. '$_' issn vide" ;
		next ;
	}
}

warn "lignes lues $. ok \n" ;



# ----------------------------------------------------------------------
# FOOTER GLOBAL
print<<FINFOOTER ;
</teiCorpus>
FINFOOTER


# ----------------------- fonctions ------------------------------------

sub id_n_cats_to_xml_tei_entry {
	my $id = shift ;
	my $cats_array = shift ;
	
	my $out_str ="<TEI xml:id=\"istex-${id}\"><teiHeader><profileDesc><textClass>" ;

	for my $cat (@$cats_array) {
		# <classCode scheme="WOS">EDUCATION, SCIENTIFIC DISCIPLINES</classCode>
		$out_str .= "<classCode scheme=\"WOS\">$cat</classCode>" ;
	}
	
	$out_str .="</textClass></profileDesc></teiHeader></TEI>\n" ;


	return $out_str ;
}

