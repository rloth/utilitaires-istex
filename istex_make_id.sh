#! /bin/bash
#  Transforms a path to an ISTEX-ID using sha1sum
#  (c) 2015 ISTEX (rloth)

case $1 in
 -h|--help)
  echo 'Usage : cat paths_to_xmlfiles.list | istex_make_id.sh'
  ;;
 *)
  while read a_data_xml_path
  do
   echo -n $a_data_xml_path | sha1sum | cut -c1-40 | tr 'a-f' 'A-F'
  done
  ;;
esac