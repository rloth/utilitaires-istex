#! /usr/bin/python3
"""
Renvoie le doctype le plus long parmi tous les XML d'un dossier
"""

from re import search, sub, MULTILINE

from os import listdir,path

from sys import argv

# ---------------------------------

my_dir = argv[1]

mes_files = [path.join(my_dir,fi) for fi in listdir(my_dir)]

# lecture pour chaque doc

longest = 0
longest_str = ""
longest_fi = ""

for (i, fi) in enumerate(mes_files):
  try:
    fh = open(fi, 'r')
  except FileNotFoundError as fnfe:
    print("WARN: Unreadable object: %s" % fi)
    continue
  try:
    long_str = fh.read()
  except UnicodeDecodeError as ue:
    print("WARN: UTF-8 decode error in input file %s" % fi)
    continue
  fh.close()
  m = search(r'(?:<\?xml[^>]*\?>)?\s*<!DOCTYPE[^\[>]+(?:\[[^\]]*\])?>',long_str, MULTILINE)
  
  # si on veut la declaration de chaque doc (str multiligne) décommenter la ligne suivante
  # print(m.group())
  
  
  if m and len(m.group()) > longest:
    longest_str = m.group()
    longest = len(longest_str)
    longest_fi = fi
  
  # compteur
  if i % 100 == 0:
    print("%i docs lus" % i)


print("La déclaration la plus longue trouvée dans le dossier est la suivante:\n %s \n" % longest_str)
print("Elle fait %i caractères" % longest)
print("Elle est dans le doc %s" % fi)