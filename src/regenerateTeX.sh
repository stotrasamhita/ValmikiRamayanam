for x in *.txt; do echo $x; ./process_chapter_tex.py $x > ../TeX/${x/txt/tex}; done
