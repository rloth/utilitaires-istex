#! /usr/bin/perl -w

# cf. aussi commandes : echo 'char' | od -ctx1      (octet par octet, en hex)
#                  et : echo 'char' | tlu.pl -o uf  (caractère utf8 par caractère utf8)

use warnings ;
use strict ;

use Getopt::Std ; $Getopt::Std::STANDARD_HELP_VERSION = 1 ;

use utf8 ;
binmode(STDOUT, ":utf8");
use Encode ;
use Unicode::Normalize ;

use HTML::HTML5::Entities;

my $opts = {} ;
getopts('hadexw', $opts) ;

# -h ou --help
HELP_MESSAGE() if ($opts->{h}) ;

my $joinAcct     = $opts->{a} || 0 ;
my $removeAcct   = $opts->{d} || 0 ;
my $convertEntis = $opts->{e} || 0 ;
my $convertEntisKeepXML = $opts->{x} || 0 ;
#~ my $convertMoreEntisMathML = $opts->{m} || 0 ; #TODO
my $replaceWeird  = $opts->{w} || 0 ;

if ($convertEntisKeepXML && $convertEntis) {
	die "les options -e et -x s'excluent mutuellement : il faut choisir !\n";
}

while (<>) {

	# !!! important !!!
	$_ = decode('UTF-8', $_);

	# avant la suite pour que les entités décodées puissent aussi être translittérées
	if ($convertEntisKeepXML) {
		
		# pour préserver '&' sous sa forme &amp;
		s/&amp;/___amp___/goi ;
		s/&#0*38;/___amp___/goi ;
		s/&#x0*26;/___amp___/goi ;
		
		# pour préserver '<' sous sa forme &lt;
		s/&lt;/___lt___/goi ;
		s/&#0*60;/___lt___/goi ;
		s/&#x0*3C;/___lt___/goi ;
		
		# pour préserver '>' sous sa forme &gt;
		s/&gt;/___gt___/goi ;
		s/&#0*62;/___gt___/goi ;
		s/&#x0*3E;/___gt___/goi ;
		
		# use HTML::HTML5::Entities;
		decode_entities($_);
		
		s/___amp___/&amp;/go ;
		s/___lt___/&lt;/go ;
		s/___gt___/&gt;/go ;
	}
	
	if ($convertEntis) {
		# use HTML::HTML5::Entities;
		decode_entities($_);
	}

	if ($joinAcct) {
		
		my $before = $_ ;
		s/([A-Za-z])([\x{0300}-\x{036F}`¨¯´¸˙˚\x{02db}˜˝^\x{ff3e}\x{ff40}\x{ffe3}])/combine_accent($1,$2)/eg ;
		warn "joinAcct" if (m/[\x{0300}-\x{036F}`¨¯´¸˙˚\x{02db}˜˝^\x{ff3e}\x{ff40}\x{ffe3}]/) ;
	}

 # suppression des accents
	if ($removeAcct) {

	# àáâãäåąāăçćĉċčďđèéêëęēĕėěĝğġģĥħìíîïĩīĭįıĵķłĺļľŀñńņňòóôõöøōŏőŕŗřśŝşšţťŧùúûüũūŭůűųŵÿýŷźżž

		# toutes les accentuées courantes sur leur équivalent ASCII
		# NB : on utilise s/// car tr/// est plus difficile à utiliser avec l'utf8
		s/[ÀÁÂÃÄÅĄĀĂ]/A/go ;
		s/[àáâãäåąāă]/a/go ;
		s/[ÇĆĈĊČ]/C/go ;
		s/[çćĉċč]/c/go ;
		s/[ĎĐ]/D/go ;
		s/[ďđ]/d/go ;
		s/[ÈÉÊËĘĒĔĖĚ]/E/go ;
		s/[èéêëęēĕėě]/e/go ;
		s/[ĜĞĠĢ]/G/go ;
		s/[ĝğġģ]/g/go ;
		s/[ĤĦ]/H/go ;
		s/[ĥħ]/h/go ;
		s/[ÌÍÎÏĨĪĬĮİ]/I/go ;
		s/[ìíîïĩīĭįı]/i/go ;
		s/[Ĵ]/J/go ;
		s/[ĵ]/j/go ;
		s/[Ķ]/K/go ;
		s/[ķ]/k/go ;
		s/[ŁĹĻĽĿ]/L/go ;
		s/[łĺļľŀ]/l/go ;
		s/[ÑŃŅŇ]/N/go ;
		s/[ñńņň]/n/go ;
		s/[ÒÓÔÕÖØŌŎŐ]/O/go ;
		s/[òóôõöøōŏő]/o/go ;
		s/[ŔŖŘ]/R/go ;
		s/[ŕŗř]/r/go ;
		s/[ŚŜŞŠ]/S/go ;
		s/[śŝşš]/s/go ;
		s/[ŢŤŦ]/T/go ;
		s/[ţťŧ]/t/go ;
		s/[ÙÚÛÜŨŪŬŮŰŲ]/U/go ;
		s/[ùúûüũūŭůűų]/u/go ;
		s/[Ŵ]/W/go ;
		s/[ŵ]/w/go ;
		s/[ŸÝŶ]/Y/go ;
		s/[ÿýŷ]/y/go ;
		s/[ŹŻŽ]/Z/go ;
		s/[źżž]/z/go ;
		
		# alternative en 2 lignes qui marche pour tous sauf pour [ŁłĐđŦŧĦħ]
		# (méthode en utilisant la décomposition des combos unicodes cara + accent)
		## $_ = Unicode::Normalize::NFKD($_);
		## s/\p{NonspacingMark}//g;
		
	}
 
	# remplacement  des caractères  inhabituels par des 
	# tokens conventionnels plus simples et plus transcodables
	if ($replaceWeird) {
		
		# Caractères de contrôle
		# ----------------------
		
		# tabulation
		## tr/\x{0009}/ / ;
		
		# LF line feed \n
		## tr/\x{000A}/ / ;
		
		# CR carriage return \r
		## tr/\x{000D}/ / ;
		
		# tous les caractères de contrôle (sauf \t, \n et \r) --> espace
		tr/\x{0000}\x{0001}\x{0002}\x{0003}\x{0004}\x{0005}\x{0006}\x{0007}\x{0008}\x{000B}\x{000C}\x{000E}\x{000F}\x{0010}\x{0011}\x{0012}\x{0013}\x{0014}\x{0015}\x{0016}\x{0017}\x{0018}\x{0019}\x{001A}\x{001B}\x{001C}\x{001D}\x{001E}\x{001F}\x{007F}/ / ;
		
		# Line separator
		tr/\x{2028}/ / ;
		
		# parfois quote parfois caractère de contrôle
		tr/\x{0092}/ / ;
		## tr/\x{0092}/'/ ;
		
		
		# Espaces et tirets
		# -----------------
		
		# tous les espaces alternatifs --> espace
		tr/\x{00A0}\x{1680}\x{180E}\x{2000}\x{2001}\x{2002}\x{2003}\x{2004}\x{2005}\x{2006}\x{2007}\x{2008}\x{2009}\x{200A}\x{200B}\x{202F}\x{205F}\x{3000}\x{FEFF}/ / ;
		
		# la plupart des tirets alternatifs --> tiret normal (dit "du 6")
		# (dans l'ordre U+002D U+2010 U+2011 U+2012 U+2013 U+2014 U+2015 U+2212 U+FE63)
		s/[‐‑‒–—―−﹣]/-/go ;
		
		# Guillemets
		# ----------
		# la plupart des quotes doubles --> "
		tr/“”„‟/"/ ;   # U+201C U+201D U+201E U+201F
		s/« ?/"/go ;    # U+20AB plus espace éventuel après
		s/ ?»/"/go ;    # U+20AB plus espace éventuel avant
		
		# la plupart des quotes simples --> '
		tr/‘’‚‛/'/ ;   # U+2018 U+2019 U+201a U+201b
		s/‹ ?/"/go ;    # U+2039 plus espace éventuel après
		s/ ?›/"/go ;    # U+203A plus espace éventuel avant
		# tr/\x{02BC}/'/ ; # parfois quote parfois modifieur accent aigü
		# tr/\x{0092}/'/ ; # parfois quote parfois caractère de contrôle
		
		
		# Ligatures
		# ---------
		s/Ꜳ/AA/go ;
		s/ꜳ/aa/go ;
		s/Æ/AE/go ;
		s/æ/ae/go ;
		s/Ǳ/DZ/go ;
		s/ǲ/Dz/go ;
		s/ǳ/dz/go ;
		s/ﬃ/ffi/go ;
		s/ﬀ/ff/go ;
		s/ﬁ/fi/go ;
		s/ﬄ/ffl/go ;
		s/ﬂ/fl/go ;
		s/ﬅ/ft/go ;
		s/Ĳ/IJ/go ;
		s/ĳ/ij/go ;
		s/Ǉ/LJ/go ;
		s/ǉ/lj/go ;
		s/Ǌ/NJ/go ;
		s/ǌ/nj/go ;
		#~ s/Œ/OE/go ;
		#~ s/œ/oe/go ;
		s//oe/go ;   # U+009C (cara contrôle vu comme oe)
		s/ﬆ/st/go ;
		s/Ꜩ/Tz/go ;
		s/ꜩ/tz/go ;

		# INACTIFS : stockés si besoin est
		# diachro islande
	#	s/Ꜵ/AO/go ;
	#	s/ꜵ/ao/go ;
	#	s/Ꜷ/AU/go ;
	#	s/ꜷ/au/go ;
	#	s/Ꜹ/AV/go ;
	#	s/ꜹ/av/go ;
	#	s/Ꜽ/AY/go ;
	#	s/ꜽ/ay/go ;
	#	s/Ꝏ/OO/go ;
	#	s/ꝏ/oo/go ;
		
		
		# Divers
		# -------
		
	#	s/…/.../go ;
	#	s//.../go ;
	#	s/€/EUR/go ;

		# puces (bullets) cf aussi egrep -o "^ +[^ ] +"
	#	s/▪/*/go ;
	#	s/►/*/go ;
	#	s/●/*/go ;
	#	s/◘/*/go ;
	#	s/→/*/go ;
	#	s/•/*/go ;
	#	s/·/*/go ;
	#	s/☽/*/go ;
	}

 print ;
}

## fonctions


# letter + combining accent ==> accented letter
# par exemple : n (U+006E) +  ́(U+0301) ==> ń (U+0144)
# NB on suppose que l'entrée a été decode et la sortie devra être encode(UTF-8)
sub combine_accent {
	my $letter = shift ;
	my $accent = shift ;
	
	# valeur à retourner
	my $combined_result = "" ;
	
	# lettre et caractère d'accentuation directement combinable dit 'combining accent'
	# --------------------------------------------------------------------------------
	if ($accent =~ /^[\x{0300}-\x{036F}]$/) {
		# lettre + combining accent
		warn "hello" ;
		$combined_result = NFC($letter.$accent) ;
	}
	# lettre et caractère d'accentuation séparé dit 'spacing accent'
	# ----------------------------------------------------------
	else {
		my $combining_equivalent = spacing_to_combining_accent($accent) ;
		
		if ($combining_equivalent eq 'UNKNOWN_ACCENT') {
			$combined_result = $letter ;
		}
		else {
			$combined_result = NFC($letter.$combining_equivalent) ;
		}
	}
	return $combined_result ;
}


# on cherche le 'combining accent' équivalent au 'spacing accent'
#
# par exemple
# \x{00B4} (class [Sk]) => \x{0301} (class [Mn])
# "ACUTE ACCENT"        => "COMBINING ACUTE ACCENT"
# 
# NB on suppose que l'entrée a été decode et la sortie devra être encode(UTF-8)
sub spacing_to_combining_accent {
	# spacing accent = (any element from Unicode [Sk] category 
	#                   that has an equivalent combining accent char)
	# --- avec 'compatibility decomposition' ---
	# 0060   GRAVE ACCENT
	# 00A8   DIAERESIS
	# 00AF   MACRON
	# 00B4   ACUTE ACCENT
	# 00B8   CEDILLA
	# 02D9   DOT ABOVE
	# 02DA   RING ABOVE
	# 02DB   OGONEK
	# 02DC   SMALL TILDE
	# 02DD   DOUBLE ACUTE ACCENT
	# --- sans 'compatibility decomposition' ---
	# 005E   CIRCUMFLEX ACCENT
	# FF3E   FULLWIDTH CIRCUMFLEX ACCENT
	# FF40   FULLWIDTH GRAVE ACCENT
	# FFE3   FULLWIDTH MACRON
	my $accent_char = shift ;
	
	# caractère cherché
	my $combining_accent = "" ;

	# pour plusieurs spacing accents, Unicode::Normalize::NFKD donne la
	# "compatibility decomposition" en un espace et l'accent combining
	my $decomp = NFKD($accent_char) ;
	my @one_two = split(//, $decomp) ;
	
	# si c'est le cas :
	if ((scalar(@one_two) == 2) && ($one_two[0] eq ' ')) {
		$combining_accent = $one_two[1] ;
	}
	# sinon on le fait nous-mêmes sur liste empirique
	else {
		# 005E CIRCUMFLEX ACCENT  --------------------> 0302 COMBINING CIRCUMFLEX ACCENT
		# FF3E FULLWIDTH CIRCUMFLEX ACCENT  ----------> 0302 COMBINING CIRCUMFLEX ACCENT
		# FF40 FULLWIDTH GRAVE ACCENT  ---------------> 0300 COMBINING GRAVE ACCENT
		# FFE3 FULLWIDTH MACRON  ---------------------> 0304 COMBINING MACRON
		$combining_accent = $accent_char ;
		$combining_accent =~ tr/\x{005e}\x{ff3e}\x{ff40}\x{ffe3}/\x{0302}\x{0302}\x{0300}\x{0304}/ ;
	}
	
	# vérification du combining accent
	# il devrait être dans range [768-879] = hex range [300-36F]
	my $decimal_cp = unpack('U*', $combining_accent) ;
	if ($decimal_cp < 768 || $decimal_cp > 879) {
		warn "found no equivalent in hex [0300-036F] for second char, codepoint decimal'"
			.sprintf("%x",$decimal_cp)."'\n" ;
		return "UNKNOWN_ACCENT" ;
	}
	else {
		# a single *non-spacing* char
		return $combining_accent ;
	}
}




sub HELP_MESSAGE {
	print <<EOT;
---------------------------------------------------------------------
    Suppression des accents et/ou des caractères utf8 atypiques
---------------------------------------------------------------------
 Usage:
      nettoie_accents_cara.pl [SWITCHES] < input.txt > output.txt

 Options:
   -e     convertir les entités html           ex: &eacute; => é
   -x     convertir les entités html sauf   /  ex: &eacute; => é
          les 3 &lt; &gt; et &amp; ou      {       &lt;     => &lt;
          leurs variantes &#0060; etc.      \\      &#0060;  => &lt;
   -a     joindre les accents séparés          ex:  e + ´ => é
   -d     tout désaccentuer                    ex: [ÀÁÂÄÅĄ] => A
   -w     remplacer les caras bizarres         ex: (ﬁ ▪ » € etc)

 Par exemple pour convertir les entités html sauf '<' '>' et '&' :

      nettoie_accents_cara.pl -x < input.txt > output.txt
---------------------------------------------------------------------
 © 2009-12 Modyco-CNRS (Nanterre)        romain.loth at inist dot fr 
---------------------------------------------------------------------
EOT
	exit 0 ;
}

