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
		
		$sco_cat = $sco_cat."-".scopus_code_to_title($sco_cat) ;
		
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
#~ my @sorted = sort {$idf->{$a} <=> $idf->{$b}} keys(%$idf) ;
#~ 
#~ for my $sco (@sorted) {
	#~ print $sco."\t".$idf->{$sco}."\n" ;
#~ }
#~ 
#~ exit ;

for my $wos_cat (sort(keys(%$matr))) {
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

####################

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





sub scopus_code_to_title {
	my $code = shift ;
	#~ warn "CODE: $code\n" ;
	
	my %corresp = (
		"1000"  =>  "General",
		"1100"  =>  "Agricultural and Biological Sciences(all)",
		"1101"  =>  "Agricultural and Biological Sciences (miscellaneous)",
		"1102"  =>  "Agronomy and Crop Science",
		"1103"  =>  "Animal Science and Zoology",
		"1104"  =>  "Aquatic Science",
		"1105"  =>  "Ecology, Evolution, Behavior and Systematics",
		"1106"  =>  "Food Science",
		"1107"  =>  "Forestry",
		"1108"  =>  "Horticulture",
		"1109"  =>  "Insect Science",
		"1110"  =>  "Plant Science",
		"1111"  =>  "Soil Science",
		"1200"  =>  "Arts and Humanities(all)",
		"1201"  =>  "Arts and Humanities (miscellaneous)",
		"1202"  =>  "History",
		"1203"  =>  "Language and Linguistics",
		"1204"  =>  "Archaeology",
		"1205"  =>  "Classics",
		"1206"  =>  "Conservation",
		"1207"  =>  "History and Philosophy of Science",
		"1208"  =>  "Literature and Literary Theory",
		"1209"  =>  "Museology",
		"1210"  =>  "Music",
		"1211"  =>  "Philosophy",
		"1212"  =>  "Religious studies",
		"1213"  =>  "Visual Arts and Performing Arts",
		"1300"  =>  "Biochemistry, Genetics and Molecular Biology(all)",
		"1301"  =>  "Biochemistry, Genetics and Molecular Biology (miscellaneous)",
		"1302"  =>  "Ageing",
		"1303"  =>  "Biochemistry",
		"1304"  =>  "Biophysics",
		"1305"  =>  "Biotechnology",
		"1306"  =>  "Cancer Research",
		"1307"  =>  "Cell Biology",
		"1308"  =>  "Clinical Biochemistry",
		"1309"  =>  "Developmental Biology",
		"1310"  =>  "Endocrinology",
		"1311"  =>  "Genetics",
		"1312"  =>  "Molecular Biology",
		"1313"  =>  "Molecular Medicine",
		"1314"  =>  "Physiology",
		"1315"  =>  "Structural Biology",
		"1400"  =>  "Business, Management and Accounting(all)",
		"1401"  =>  "Business, Management and Accounting (miscellaneous)",
		"1402"  =>  "Accounting",
		"1403"  =>  "Business and International Management",
		"1404"  =>  "Management Information Systems",
		"1405"  =>  "Management of Technology and Innovation",
		"1406"  =>  "Marketing",
		"1407"  =>  "Organizational Behavior and Human Resource Management",
		"1408"  =>  "Strategy and Management",
		"1409"  =>  "Tourism, Leisure and Hospitality Management",
		"1410"  =>  "Industrial relations",
		"1500"  =>  "Chemical Engineering(all)",
		"1501"  =>  "Chemical Engineering (miscellaneous)",
		"1502"  =>  "Bioengineering",
		"1503"  =>  "Catalysis",
		"1504"  =>  "Chemical Health and Safety",
		"1505"  =>  "Colloid and Surface Chemistry",
		"1506"  =>  "Filtration and Separation",
		"1507"  =>  "Fluid Flow and Transfer Processes",
		"1508"  =>  "Process Chemistry and Technology",
		"1600"  =>  "Chemistry(all)",
		"1601"  =>  "Chemistry (miscellaneous)",
		"1602"  =>  "Analytical Chemistry",
		"1603"  =>  "Electrochemistry",
		"1604"  =>  "Inorganic Chemistry",
		"1605"  =>  "Organic Chemistry",
		"1606"  =>  "Physical and Theoretical Chemistry",
		"1607"  =>  "Spectroscopy",
		"1700"  =>  "Computer Science(all)",
		"1701"  =>  "Computer Science (miscellaneous)",
		"1702"  =>  "Artificial Intelligence",
		"1703"  =>  "Computational Theory and Mathematics",
		"1704"  =>  "Computer Graphics and Computer-Aided Design",
		"1705"  =>  "Computer Networks and Communications",
		"1706"  =>  "Computer Science Applications",
		"1707"  =>  "Computer Vision and Pattern Recognition",
		"1708"  =>  "Hardware and Architecture",
		"1709"  =>  "Human-Computer Interaction",
		"1710"  =>  "Information Systems",
		"1711"  =>  "Signal Processing",
		"1712"  =>  "Software",
		"1800"  =>  "Decision Sciences(all)",
		"1801"  =>  "Decision Sciences (miscellaneous)",
		"1802"  =>  "Information Systems and Management",
		"1803"  =>  "Management Science and Operations Research",
		"1804"  =>  "Statistics, Probability and Uncertainty",
		"1900"  =>  "Earth and Planetary Sciences(all)",
		"1901"  =>  "Earth and Planetary Sciences (miscellaneous)",
		"1902"  =>  "Atmospheric Science",
		"1903"  =>  "Computers in Earth Sciences",
		"1904"  =>  "Earth-Surface Processes",
		"1905"  =>  "Economic Geology",
		"1906"  =>  "Geochemistry and Petrology",
		"1907"  =>  "Geology",
		"1908"  =>  "Geophysics",
		"1909"  =>  "Geotechnical Engineering and Engineering Geology",
		"1910"  =>  "Oceanography",
		"1911"  =>  "Palaeontology",
		"1912"  =>  "Space and Planetary Science",
		"1913"  =>  "Stratigraphy",
		"2000"  =>  "Economics, Econometrics and Finance(all)",
		"2001"  =>  "Economics, Econometrics and Finance (miscellaneous)",
		"2002"  =>  "Economics and Econometrics",
		"2003"  =>  "Finance",
		"2100"  =>  "Energy(all)",
		"2101"  =>  "Energy (miscellaneous)",
		"2102"  =>  "Energy Engineering and Power Technology",
		"2103"  =>  "Fuel Technology",
		"2104"  =>  "Nuclear Energy and Engineering",
		"2105"  =>  "Renewable Energy, Sustainability and the Environment",
		"2200"  =>  "Engineering(all)",
		"2201"  =>  "Engineering (miscellaneous)",
		"2202"  =>  "Aerospace Engineering",
		"2203"  =>  "Automotive Engineering",
		"2204"  =>  "Biomedical Engineering",
		"2205"  =>  "Civil and Structural Engineering",
		"2206"  =>  "Computational Mechanics",
		"2207"  =>  "Control and Systems Engineering",
		"2208"  =>  "Electrical and Electronic Engineering",
		"2209"  =>  "Industrial and Manufacturing Engineering",
		"2210"  =>  "Mechanical Engineering",
		"2211"  =>  "Mechanics of Materials",
		"2212"  =>  "Ocean Engineering",
		"2213"  =>  "Safety, Risk, Reliability and Quality",
		"2214"  =>  "Media Technology",
		"2215"  =>  "Building and Construction",
		"2216"  =>  "Architecture ",
		"2300"  =>  "Environmental Science(all)",
		"2301"  =>  "Environmental Science (miscellaneous)",
		"2302"  =>  "Ecological Modelling",
		"2303"  =>  "Ecology",
		"2304"  =>  "Environmental Chemistry",
		"2305"  =>  "Environmental Engineering",
		"2306"  =>  "Global and Planetary Change",
		"2307"  =>  "Health, Toxicology and Mutagenesis",
		"2308"  =>  "Management, Monitoring, Policy and Law",
		"2309"  =>  "Nature and Landscape Conservation",
		"2310"  =>  "Pollution",
		"2311"  =>  "Waste Management and Disposal",
		"2312"  =>  "Water Science and Technology",
		"2400"  =>  "Immunology and Microbiology(all)",
		"2401"  =>  "Immunology and Microbiology (miscellaneous) ",
		"2402"  =>  "Applied Microbiology and Biotechnology",
		"2403"  =>  "Immunology",
		"2404"  =>  "Microbiology",
		"2405"  =>  "Parasitology",
		"2406"  =>  "Virology",
		"2500"  =>  "Materials Science(all)",
		"2501"  =>  "Materials Science (miscellaneous)",
		"2502"  =>  "Biomaterials",
		"2503"  =>  "Ceramics and Composites",
		"2504"  =>  "Electronic, Optical and Magnetic Materials",
		"2505"  =>  "Materials Chemistry",
		"2506"  =>  "Metals and Alloys",
		"2507"  =>  "Polymers and Plastics",
		"2508"  =>  "Surfaces, Coatings and Films",
		"2600"  =>  "Mathematics(all)",
		"2601"  =>  "Mathematics (miscellaneous)",
		"2602"  =>  "Algebra and Number Theory",
		"2603"  =>  "Analysis",
		"2604"  =>  "Applied Mathematics",
		"2605"  =>  "Computational Mathematics",
		"2606"  =>  "Control and Optimization",
		"2607"  =>  "Discrete Mathematics and Combinatorics",
		"2608"  =>  "Geometry and Topology",
		"2609"  =>  "Logic",
		"2610"  =>  "Mathematical Physics",
		"2611"  =>  "Modelling and Simulation",
		"2612"  =>  "Numerical Analysis",
		"2613"  =>  "Statistics and Probability",
		"2614"  =>  "Theoretical Computer Science",
		"2700"  =>  "Medicine(all)",
		"2701"  =>  "Medicine (miscellaneous)",
		"2702"  =>  "Anatomy",
		"2703"  =>  "Anesthesiology and Pain Medicine",
		"2704"  =>  "Biochemistry, medical",
		"2705"  =>  "Cardiology and Cardiovascular Medicine",
		"2706"  =>  "Critical Care and Intensive Care Medicine",
		"2707"  =>  "Complementary and alternative medicine",
		"2708"  =>  "Dermatology",
		"2709"  =>  "Drug guides",
		"2710"  =>  "Embryology",
		"2711"  =>  "Emergency Medicine",
		"2712"  =>  "Endocrinology, Diabetes and Metabolism",
		"2713"  =>  "Epidemiology",
		"2714"  =>  "Family Practice",
		"2715"  =>  "Gastroenterology",
		"2716"  =>  "Genetics(clinical)",
		"2717"  =>  "Geriatrics and Gerontology",
		"2718"  =>  "Health Informatics",
		"2719"  =>  "Health Policy",
		"2720"  =>  "Hematology",
		"2721"  =>  "Hepatology",
		"2722"  =>  "Histology",
		"2723"  =>  "Immunology and Allergy",
		"2724"  =>  "Internal Medicine",
		"2725"  =>  "Infectious Diseases",
		"2726"  =>  "Microbiology (medical)",
		"2727"  =>  "Nephrology",
		"2728"  =>  "Clinical Neurology",
		"2729"  =>  "Obstetrics and Gynaecology",
		"2730"  =>  "Oncology",
		"2731"  =>  "Ophthalmology",
		"2732"  =>  "Orthopedics and Sports Medicine",
		"2733"  =>  "Otorhinolaryngology",
		"2734"  =>  "Pathology and Forensic Medicine",
		"2735"  =>  "Pediatrics, Perinatology, and Child Health",
		"2736"  =>  "Pharmacology (medical)",
		"2737"  =>  "Physiology (medical)",
		"2738"  =>  "Psychiatry and Mental health",
		"2739"  =>  "Public Health, Environmental and Occupational Health",
		"2740"  =>  "Pulmonary and Respiratory Medicine",
		"2741"  =>  "Radiology Nuclear Medicine and imaging",
		"2742"  =>  "Rehabilitation",
		"2743"  =>  "Reproductive Medicine",
		"2744"  =>  "Reviews and References, Medical",
		"2745"  =>  "Rheumatology",
		"2746"  =>  "Surgery",
		"2747"  =>  "Transplantation",
		"2748"  =>  "Urology",
		"2800"  =>  "Neuroscience(all)",
		"2801"  =>  "Neuroscience (miscellaneous)",
		"2802"  =>  "Behavioral Neuroscience",
		"2803"  =>  "Biological Psychiatry",
		"2804"  =>  "Cellular and Molecular Neuroscience",
		"2805"  =>  "Cognitive Neuroscience",
		"2806"  =>  "Developmental Neuroscience",
		"2807"  =>  "Endocrine and Autonomic Systems",
		"2808"  =>  "Neurology",
		"2809"  =>  "Sensory Systems",
		"2900"  =>  "Nursing(all)",
		"2901"  =>  "Nursing (miscellaneous)",
		"2902"  =>  "Advanced and Specialised Nursing",
		"2903"  =>  "Assessment and Diagnosis",
		"2904"  =>  "Care Planning",
		"2905"  =>  "Community and Home Care",
		"2906"  =>  "Critical Care",
		"2907"  =>  "Emergency",
		"2908"  =>  "Fundamentals and skills",
		"2909"  =>  "Gerontology",
		"2910"  =>  "Issues, ethics and legal aspects",
		"2911"  =>  "Leadership and Management",
		"2912"  =>  "LPN and LVN",
		"2913"  =>  "Maternity and Midwifery",
		"2914"  =>  "MedicalﾖSurgical",
		"2915"  =>  "Nurse Assisting",
		"2916"  =>  "Nutrition and Dietetics",
		"2917"  =>  "Oncology(nursing)",
		"2918"  =>  "Pathophysiology",
		"2919"  =>  "Pediatrics",
		"2920"  =>  "Pharmacology (nursing)",
		"2921"  =>  "Phychiatric Mental Health",
		"2922"  =>  "Research and Theory",
		"2923"  =>  "Review and Exam Preparation",
		"3000"  =>  "Pharmacology, Toxicology and Pharmaceutics(all)",
		"3001"  =>  "Pharmacology, Toxicology and Pharmaceutics (miscellaneous)",
		"3002"  =>  "Drug Discovery",
		"3003"  =>  "Pharmaceutical Science",
		"3004"  =>  "Pharmacology",
		"3005"  =>  "Toxicology",
		"3100"  =>  "Physics and Astronomy(all)",
		"3101"  =>  "Physics and Astronomy (miscellaneous)",
		"3102"  =>  "Acoustics and Ultrasonics",
		"3103"  =>  "Astronomy and Astrophysics",
		"3104"  =>  "Condensed Matter Physics",
		"3105"  =>  "Instrumentation",
		"3106"  =>  "Nuclear and High Energy Physics",
		"3107"  =>  "Atomic and Molecular Physics, and Optics",
		"3108"  =>  "Radiation",
		"3109"  =>  "Statistical and Nonlinear Physics",
		"3110"  =>  "Surfaces and Interfaces",
		"3200"  =>  "Psychology(all)",
		"3201"  =>  "Psychology (miscellaneous)",
		"3202"  =>  "Applied Psychology",
		"3203"  =>  "Clinical Psychology",
		"3204"  =>  "Developmental and Educational Psychology",
		"3205"  =>  "Experimental and Cognitive Psychology",
		"3206"  =>  "Neuropsychology and Physiological Psychology",
		"3207"  =>  "Social Psychology",
		"3300"  =>  "Social Sciences(all)",
		"3301"  =>  "Social Sciences (miscellaneous)",
		"3302"  =>  "Archaeology",
		"3303"  =>  "Development",
		"3304"  =>  "Education",
		"3305"  =>  "Geography, Planning and Development",
		"3306"  =>  "Health(social science)",
		"3307"  =>  "Human Factors and Ergonomics",
		"3308"  =>  "Law",
		"3309"  =>  "Library and Information Sciences",
		"3310"  =>  "Linguistics and Language",
		"3311"  =>  "Safety Research",
		"3312"  =>  "Sociology and Political Science",
		"3313"  =>  "Transportation",
		"3314"  =>  "Anthropology",
		"3315"  =>  "Communication",
		"3316"  =>  "Cultural Studies",
		"3317"  =>  "Demography",
		"3318"  =>  "Gender Studies",
		"3319"  =>  "Life-span and Life-course Studies",
		"3320"  =>  "Political Science and International Relations",
		"3321"  =>  "Public Administration",
		"3322"  =>  "Urban Studies",
		"3400"  =>  "veterinary(all)",
		"3401"  =>  "veterinary (miscalleneous)",
		"3402"  =>  "Equine",
		"3403"  =>  "Food Animals",
		"3404"  =>  "Small Animals",
		"3500"  =>  "Dentistry(all)",
		"3501"  =>  "Dentistry (miscellaneous)",
		"3502"  =>  "Dental Assisting",
		"3503"  =>  "Dental Hygiene",
		"3504"  =>  "Oral Surgery",
		"3505"  =>  "Orthodontics",
		"3506"  =>  "Periodontics",
		"3600"  =>  "Health Professions(all)",
		"3601"  =>  "Health Professions (miscellaneous)",
		"3602"  =>  "Chiropractics",
		"3603"  =>  "Complementary and Manual Therapy",
		"3604"  =>  "Emergency Medical Services",
		"3605"  =>  "Health Information Management",
		"3606"  =>  "Medical Assisting and Transcription",
		"3607"  =>  "Medical Laboratory Technology",
		"3608"  =>  "Medical Terminology",
		"3609"  =>  "Occupational Therapy",
		"3610"  =>  "Optometry",
		"3611"  =>  "Pharmacy",
		"3612"  =>  "Physical Therapy, Sports Therapy and Rehabilitation",
		"3613"  =>  "Podiatry",
		"3614"  =>  "Radiological and Ultrasound Technology",
		"3615"  =>  "Respiratory Care",
		"3616"  =>  "Speech and Hearing"
	) ;
	
	return $corresp{$code} ;
}

