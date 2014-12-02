#! /usr/bin/perl
# Sépare les catégories groupées et fait une table de cooccurrences
use warnings ;
use strict ;

use Data::Dumper ;

my $matr = {} ;

# pour idf
my $idxinv = {} ;

my $sep = quotemeta("/") ;

while(<>) {
	chomp ;
	my ($scopus,$wos) = split(/\t/, $_) ;
	
	next unless (defined($scopus) && defined($wos) ) ;
	
	my @sco_champs = split(/$sep/, $scopus) ;
	my @wos_champs = split(/$sep/, $wos) ;
	
	my $paires = paires(nettoie_liste(\@sco_champs), nettoie_liste(\@wos_champs)) ;
	
	for my $paire (@$paires) {
		my $wos_cat = $paire->[0] ;
		my $sco_cat = $paire->[1] ;
		$matr->{$wos_cat}->{$sco_cat}++ ;
		
		# le nombre de fois que cette catégories WOS apparaît
		$idxinv->{$sco_cat} ++ ;
	}
}

my $idf = {} ;

for my $scow (keys(%$idxinv)) {
	$idf->{$scow} = 1/log(1+$idxinv->{$scow}) ;
}

# imprime les IDFs
#~ my @sorted = sort {$idf->{$b} <=> $idf->{$a}} keys(%$idf) ;
#~ 
#~ for my $sco (@sorted) {
	#~ print $sco." ===> ".$idf->{$sco}."\n" ;
#~ }
#~ 
#~ exit ;

for my $wos_cat (keys(%$matr)) {
	my $sco_freqs = $matr->{$wos_cat} ;
	
	my $tfidf = {} ;
	
	for my $sco_cat (keys(%$sco_freqs)) {
		$tfidf->{$sco_cat} = $sco_freqs->{$sco_cat} * $idf->{$sco_cat} ;
	}
	
	my @rn = sort {$tfidf->{$b} <=> $tfidf->{$a}} keys(%$tfidf) ;
	
	my $best_sco = shift @rn ;
	
	my @strs = () ;
	for my $restants_sco (@rn) {
		push(@strs, $restants_sco."(".$sco_freqs->{$restants_sco}.")")
	}
	# chaîne en sortie
	# calibrée ici pour tenir sur une ligne
	my $outstr = "$wos_cat\t$best_sco\t".join("/",@strs) ;
	print $outstr."\n" ;
}


sub nettoie_liste {
	my $list = shift ;
	
	my $newlist = [] ;
	for my $elt (@$list) {
		$elt =~ s/^ +//g ;
		$elt =~ s/ +$//g ;
		next unless (length($elt)) ;
		push (@$newlist, $elt) ;
	}
	return $newlist ;
}


# donne toutes les combinaisons de 2 pour une liste de longueur >= 2
sub paires {
	my $list1 = shift ;
	my $list2 = shift ;
	my $len1 = scalar(@$list1) ;
	my $len2 = scalar(@$list2) ;
	
	my @pairs = () ;
	
	for (my $j = 0 ; $j < $len1 ; $j++) {
		for (my $k = 0 ; $k < $len2 ; $k++) {
			push (@pairs, [$list1->[$j],$list2->[$k]]) ;
		}
	}
	return \@pairs ;
}
