#!/bin/bash
awk 'BEGIN{kandas = 0}
$0~/Ramayana/{sub(/kanda/, "Kanda", $3); sub(/ski/, "shki", $3); kandas +=1; fname = kandas "-" $3 ".txt"}
{print > fname}' ValmikiRamayanam.txt
